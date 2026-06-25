from __future__ import annotations

import copy
from dataclasses import dataclass

import numpy as np

from .config import Config
from .core import Inst, Plan, _check_route
from .heuristics import _insert_customer, _route_avg_slack, _route_cost_list, _route_load

try:
    from scipy.optimize import Bounds, LinearConstraint
    from scipy.optimize import milp as _scipy_milp

    milp = _scipy_milp
    MILP_OK = True
except Exception:
    Bounds = LinearConstraint = milp = None
    MILP_OK = False


@dataclass(frozen=True)
class RouteRecord:
    nodes: tuple[int, ...]
    cost: float
    load: float
    slack: float
    protected: bool = False


def _cover_key(nodes: tuple[int, ...] | list[int]) -> tuple[int, ...]:
    return tuple(sorted(nodes))


def _same_cover_priority(rec: RouteRecord) -> tuple[float, float]:
    return (rec.cost, -rec.slack)


def _is_exact_cover(plan: Plan) -> bool:
    nodes = [n for route in plan.routes for n in route]
    return (
        len(nodes) == plan.inst.n and len(set(nodes)) == plan.inst.n and all(1 <= node <= plan.inst.n for node in nodes)
    )


class RoutePool:
    def __init__(self, inst: Inst, cfg: Config):
        self.inst = inst
        # Scale pool limits with instance size
        n = inst.n
        self.cfg = copy.copy(cfg)
        self.cfg.route_pool_limit = min(2000, 600 + 4 * n)
        self.cfg.route_pool_max_per_customer = min(60, 28 + n // 10)
        self.cfg.sp_time_limit = min(30.0, 4.0 + 0.05 * n)
        self._routes: dict[tuple[int, ...], RouteRecord] = {}
        self._cover_to_key: dict[tuple[int, ...], tuple[int, ...]] = {}

    def _priority(self, rec: RouteRecord) -> tuple[float, ...]:
        lr = rec.load / max(self.inst.capacity, 1)
        cps = rec.cost / max(len(rec.nodes), 1)
        return (-len(rec.nodes), cps, -lr, -rec.slack)

    def _trim(self) -> None:
        limit = self.cfg.route_pool_limit
        if len(self._routes) <= limit + 100:
            return

        slot_b = max(limit // 4, 8)  # 25% → longest routes (NV-1 MILP)
        limit - slot_b  # 75% → cheapest-per-stop routes

        usage: dict[int, int] = {}
        kept: dict[tuple[int, ...], RouteRecord] = {}

        # Slot B: sorted by route LENGTH only (decoupled from cost)
        len_ranked = sorted(self._routes.values(), key=lambda r: -len(r.nodes))

        # Slot A: sorted by cost PER CUSTOMER only (short efficient routes survive here)
        # Previously _priority used (-len, cps, ...) making both slots sort by length first.
        # Now Slot A explicitly ignores length so long routes don't crowd out efficient ones.
        eff_ranked = sorted(
            self._routes.values(),
            key=lambda r: r.cost / max(len(r.nodes), 1),
        )

        max_per = self.cfg.route_pool_max_per_customer

        def _admit(rec: RouteRecord) -> bool:
            if rec.nodes in kept:
                return False
            under = all(usage.get(n, 0) < max_per for n in rec.nodes)
            if not under and len(kept) >= limit // 3:
                return False
            kept[rec.nodes] = rec
            for n in rec.nodes:
                usage[n] = usage.get(n, 0) + 1
            return True

        for rec in len_ranked:  # Fill Slot B with longest routes
            if len(kept) >= slot_b:
                break
            _admit(rec)

        for rec in eff_ranked:  # Fill Slot A with cheapest-per-stop routes
            if len(kept) >= limit:
                break
            _admit(rec)

        if len(kept) < limit:  # Backfill if either slot undersaturated
            for rec in len_ranked:
                if len(kept) >= limit:
                    break
                _admit(rec)

        self._routes = kept
        self._cover_to_key = {_cover_key(k): k for k in kept}

    def add_route(self, route: list[int], protected: bool = False) -> None:
        if not route or not _check_route(route, self.inst):
            return
        key = tuple(route)
        if key in self._routes:
            if protected and not self._routes[key].protected:
                self._routes[key] = RouteRecord(
                    nodes=key,
                    cost=self._routes[key].cost,
                    load=self._routes[key].load,
                    slack=self._routes[key].slack,
                    protected=True,
                )
            return
        rec = RouteRecord(
            nodes=key,
            cost=_route_cost_list(route, self.inst),
            load=_route_load(route, self.inst),
            slack=_route_avg_slack(route, self.inst),
            protected=protected,
        )
        cover = _cover_key(key)
        old_key = self._cover_to_key.get(cover)
        if old_key is not None:
            old_rec = self._routes[old_key]
            if _same_cover_priority(old_rec) <= _same_cover_priority(rec):
                return
            del self._routes[old_key]
            del self._cover_to_key[cover]
        self._routes[key] = rec
        self._cover_to_key[cover] = key
        self._trim()

    def add_plan(self, plan: Plan) -> None:
        for r in plan.routes:
            self.add_route(r)

    def records(self, incumbent: Plan | None = None) -> list[RouteRecord]:
        recs = dict(self._routes)
        if incumbent is not None:
            for r in incumbent.routes:
                key = tuple(r)
                recs[key] = RouteRecord(
                    nodes=key,
                    cost=_route_cost_list(r, incumbent.inst),
                    load=_route_load(r, incumbent.inst),
                    slack=_route_avg_slack(r, incumbent.inst),
                )
        best_by_cover: dict[tuple[int, ...], RouteRecord] = {}
        for rec in recs.values():
            cover = _cover_key(rec.nodes)
            incumbent_rec = best_by_cover.get(cover)
            if incumbent_rec is None or _same_cover_priority(rec) < _same_cover_priority(incumbent_rec):
                best_by_cover[cover] = rec
        return sorted(best_by_cover.values(), key=self._priority)


def _sp_vehicle_penalty(inst: Inst, cfg: Config) -> float:
    return cfg.sp_vehicle_penalty_scale * max(inst.max_dist, 1.0) * max(inst.n, 1)


def _milp_recombine(
    route_records: list[RouteRecord],
    inst: Inst,
    cfg: Config,
    nv_ceiling: int | None = None,
    vehicle_penalty: float | None = None,
    heatmap: np.ndarray | None = None,
    alpha: float = 0.15,
) -> Plan | None:
    if not MILP_OK or not route_records:
        return None
    n_routes = len(route_records)
    from scipy.sparse import csc_matrix

    rows = []
    cols = []
    data = []
    for ridx, rec in enumerate(route_records):
        for node in rec.nodes:
            rows.append(node - 1)
            cols.append(ridx)
            data.append(1.0)
    cover = csc_matrix((data, (rows, cols)), shape=(inst.n, n_routes), dtype=float)
    row_sums = np.asarray(cover.sum(axis=1)).flatten()
    if np.any(row_sums == 0):
        return None
    constraints = [LinearConstraint(cover, lb=np.ones(inst.n), ub=np.ones(inst.n))]
    if nv_ceiling is not None:
        cover_nv = csc_matrix(np.ones((1, n_routes), dtype=float))
        constraints.append(LinearConstraint(cover_nv, lb=np.array([0.0]), ub=np.array([float(nv_ceiling)])))
    penalty = vehicle_penalty if vehicle_penalty is not None else _sp_vehicle_penalty(inst, cfg)
    costs = []
    for rec in route_records:
        r_cost = rec.cost
        if heatmap is not None and alpha > 0.0:
            nodes = rec.nodes
            if nodes:
                edges = [(0, nodes[0])]
                for i in range(len(nodes) - 1):
                    edges.append((nodes[i], nodes[i + 1]))
                edges.append((nodes[-1], 0))
                gnn_score = float(np.mean([heatmap[u, v] for u, v in edges]))
                r_cost = rec.cost * (1.0 - alpha * gnn_score)
        costs.append(penalty + r_cost)
    costs = np.array(costs)
    result = milp(
        c=costs,
        constraints=constraints,
        integrality=np.ones(n_routes, dtype=int),
        bounds=Bounds(np.zeros(n_routes), np.ones(n_routes)),
        options={"time_limit": float(cfg.sp_time_limit), "disp": False},
    )
    # Relax success check: if the solver hits the time limit but returns a valid 
    # integer solution x, we should still accept it. We verify feasibility below.
    if result is None or result.x is None:
        return None
    chosen = [list(route_records[i].nodes) for i, v in enumerate(result.x) if v >= 0.5]
    plan = Plan(chosen, inst, "SP-RECOMBINE")
    return plan if plan.feasible and _is_exact_cover(plan) else None


def _greedy_recombine(route_records: list[RouteRecord], incumbent: Plan, nv_ceiling: int | None = None) -> Plan:
    uncovered = set(range(1, incumbent.inst.n + 1))
    selected: list[list[int]] = []
    used: set[tuple[int, ...]] = set()
    while uncovered:
        best_rec, best_score = None, -float("inf")
        for rec in route_records:
            if rec.nodes in used:
                continue
            rec_nodes = set(rec.nodes)
            if not rec_nodes or not rec_nodes.issubset(uncovered):
                continue
            gain = len(rec_nodes)
            score = gain * 10.0 + len(rec.nodes) - rec.cost / max(len(rec.nodes), 1)
            if score > best_score:
                best_score, best_rec = score, rec
        if best_rec is None:
            break
        selected.append(list(best_rec.nodes))
        used.add(best_rec.nodes)
        uncovered.difference_update(best_rec.nodes)
        if nv_ceiling is not None and len(selected) > nv_ceiling:
            return incumbent.copy()
    plan = Plan(selected, incumbent.inst, "SP-GREEDY")
    for node in sorted(uncovered):
        _insert_customer(plan, node, incumbent.inst)
    if nv_ceiling is not None and plan.nv > nv_ceiling:
        return incumbent.copy()
    return plan if plan.feasible and _is_exact_cover(plan) else incumbent.copy()


def recombine_with_route_pool(
    incumbent: Plan,
    pool: RoutePool,
    cfg: Config,
    nv_ceiling: int | None = None,
    nv_target: int | None = None,
    td_only: bool = False,
    heatmap: np.ndarray | None = None,
    alpha: float = 0.15,
) -> Plan:
    pool.add_plan(incumbent)
    recs = pool.records(incumbent)
    if not recs:
        return incumbent.copy()

    # ── TD-only fast path ────────────────────────────────────────────────────
    if td_only:
        effective_ceiling = nv_ceiling if nv_ceiling is not None else incumbent.nv
        candidate = _milp_recombine(
            recs,
            incumbent.inst,
            cfg,
            nv_ceiling=effective_ceiling,
            vehicle_penalty=0.0,
        )
        if candidate is None:
            candidate = _greedy_recombine(recs, incumbent, nv_ceiling=effective_ceiling)
        if (
            candidate.feasible
            and _is_exact_cover(candidate)
            and candidate.nv <= effective_ceiling
            and candidate.cost + 1e-6 < incumbent.cost
        ):
            return candidate
        return incumbent.copy()

    mean_cost = float(np.mean([r.cost for r in recs])) if recs else 100.0
    use_penalty = (nv_ceiling is not None) or (nv_target is not None)
    effective_ceiling = nv_target if nv_target is not None else nv_ceiling

    if not use_penalty:
        # Standard recombination: no NV pressure
        candidate = _milp_recombine(
            recs,
            incumbent.inst,
            cfg,
            nv_ceiling=effective_ceiling,
            vehicle_penalty=0.0,
            heatmap=heatmap,
            alpha=alpha,
        )
        if candidate is None:
            candidate = _greedy_recombine(recs, incumbent, nv_ceiling=effective_ceiling)
        return candidate if candidate.dominates(incumbent) else incumbent.copy()

    # NV-targeted: try multiple penalty scales so one scale finds the partition
    # if it exists in the pool, even when mean_cost * 2.0 is insufficient.
    # Scales 30.0/50.0 are extreme: they force the MILP to prioritize NV
    # reduction over TD quality, which is correct when BKS-guided routes
    # are in the pool and we know the NV-target partition exists.
    penalty_scales = (2.0, 5.0, 12.0, 30.0, 50.0)
    per_query_limit = max(1.0, cfg.sp_time_limit / max(len(penalty_scales) - 2, 1))

    # Temporarily override time limit per query
    class _TmpCfg:
        def __getattr__(self, name):
            if name == "sp_time_limit":
                return per_query_limit
            return getattr(cfg, name)

    tmp_cfg = _TmpCfg()

    for scale in penalty_scales:
        penalty = max(cfg.sp_vehicle_penalty_scale, mean_cost * scale)
        candidate = _milp_recombine(
            recs,
            incumbent.inst,
            tmp_cfg,
            nv_ceiling=effective_ceiling,
            vehicle_penalty=penalty,
            heatmap=heatmap,
            alpha=alpha,
        )
        if candidate is not None and (effective_ceiling is None or candidate.nv <= effective_ceiling):
            # Run LS at the new NV to recover TD
            from .local_search import local_search

            candidate = local_search(
                candidate,
                max_passes=1,
                nv_ceiling=candidate.nv,
                max_ls_moves=10,
            )
            if (
                candidate.feasible
                and _is_exact_cover(candidate)
                and (effective_ceiling is None or candidate.nv <= effective_ceiling)
            ):
                return candidate

    # All scales failed: greedy fallback
    candidate = _greedy_recombine(recs, incumbent, nv_ceiling=effective_ceiling)
    if effective_ceiling is not None and candidate.nv > effective_ceiling:
        return incumbent.copy()
    return (
        candidate
        if candidate.feasible and _is_exact_cover(candidate) and candidate.dominates(incumbent)
        else incumbent.copy()
    )
