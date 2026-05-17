from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import numpy as np
from .core import Inst, Plan
from .config import Config
from .heuristics import _route_cost_list, _route_load, _route_avg_slack, _check_route, _insert_customer

try:
    from scipy.optimize import Bounds, LinearConstraint, milp as _scipy_milp
    milp = _scipy_milp
    MILP_OK = True
except Exception:
    Bounds = LinearConstraint = milp = None
    MILP_OK = False

@dataclass(frozen=True)
class RouteRecord:
    nodes: Tuple[int, ...]
    cost:  float
    load:  float
    slack: float


class RoutePool:
    def __init__(self, inst: Inst, cfg: Config):
        self.inst = inst
        self.cfg  = cfg
        self._routes: Dict[Tuple[int, ...], RouteRecord] = {}

    def _priority(self, rec: RouteRecord) -> Tuple[float, ...]:
        lr  = rec.load / max(self.inst.capacity, 1)
        cps = rec.cost / max(len(rec.nodes), 1)
        return (-len(rec.nodes), cps, -lr, -rec.slack)

    def _trim(self) -> None:
        limit = self.cfg.route_pool_limit
        if len(self._routes) <= limit:
            return
        usage: Dict[int, int] = {}
        kept:  Dict[Tuple[int, ...], RouteRecord] = {}
        ranked = sorted(self._routes.values(), key=self._priority)
        for rec in ranked:
            if len(kept) >= limit:
                break
            under = all(usage.get(n, 0) < self.cfg.route_pool_max_per_customer for n in rec.nodes)
            if under or len(kept) < limit // 3:
                kept[rec.nodes] = rec
                for n in rec.nodes:
                    usage[n] = usage.get(n, 0) + 1
        if len(kept) < limit:
            for rec in ranked:
                if rec.nodes not in kept:
                    kept[rec.nodes] = rec
                if len(kept) >= limit:
                    break
        self._routes = kept

    def add_route(self, route: List[int]) -> None:
        if not route or not _check_route(route, self.inst):
            return
        key = tuple(route)
        if key in self._routes:
            return
        self._routes[key] = RouteRecord(
            nodes=key,
            cost =_route_cost_list(route, self.inst),
            load =_route_load(route, self.inst),
            slack=_route_avg_slack(route, self.inst),
        )
        self._trim()

    def add_plan(self, plan: Plan) -> None:
        for r in plan.routes:
            self.add_route(r)

    def records(self, incumbent: Optional[Plan] = None) -> List[RouteRecord]:
        recs = dict(self._routes)
        if incumbent is not None:
            for r in incumbent.routes:
                key = tuple(r)
                recs[key] = RouteRecord(
                    nodes=key,
                    cost =_route_cost_list(r, incumbent.inst),
                    load =_route_load(r, incumbent.inst),
                    slack=_route_avg_slack(r, incumbent.inst),
                )
        return sorted(recs.values(), key=self._priority)


def _sp_vehicle_penalty(inst: Inst, cfg: Config) -> float:
    return cfg.sp_vehicle_penalty_scale * max(inst.max_dist, 1.0) * max(inst.n, 1)


def _milp_recombine(route_records: List[RouteRecord], inst: Inst, cfg: Config,
                    nv_ceiling: Optional[int] = None) -> Optional[Plan]:
    if not MILP_OK or not route_records:
        return None
    n_routes = len(route_records)
    cover    = np.zeros((inst.n, n_routes), dtype=float)
    for ridx, rec in enumerate(route_records):
        for node in rec.nodes:
            cover[node - 1, ridx] = 1.0
    if np.any(cover.sum(axis=1) == 0):
        return None
    constraints = [LinearConstraint(cover, lb=np.ones(inst.n), ub=np.ones(inst.n))]
    if nv_ceiling is not None:
        constraints.append(LinearConstraint(
            np.ones((1, n_routes)), lb=np.array([0.0]), ub=np.array([float(nv_ceiling)])
        ))
    costs  = np.array([_sp_vehicle_penalty(inst, cfg) + rec.cost for rec in route_records])
    result = milp(
        c=costs, constraints=constraints,
        integrality=np.ones(n_routes, dtype=int),
        bounds=Bounds(np.zeros(n_routes), np.ones(n_routes)),
        options={"time_limit": float(cfg.sp_time_limit), "disp": False},
    )
    if result is None or not getattr(result, "success", False) or result.x is None:
        return None
    chosen = [list(route_records[i].nodes) for i, v in enumerate(result.x) if v >= 0.5]
    plan   = Plan(chosen, inst, "SP-RECOMBINE")
    return plan if plan.feasible else None


def _greedy_recombine(route_records: List[RouteRecord], incumbent: Plan,
                      nv_ceiling: Optional[int] = None) -> Plan:
    uncovered = set(range(1, incumbent.inst.n + 1))
    selected: List[List[int]] = []
    used: set = set()
    while uncovered:
        best_rec, best_score = None, -float("inf")
        for rec in route_records:
            if rec.nodes in used:
                continue
            gain = len(set(rec.nodes) & uncovered)
            if gain == 0:
                continue
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
    return plan if plan.feasible else incumbent.copy()


def recombine_with_route_pool(incumbent: Plan, pool: RoutePool, cfg: Config,
                              nv_ceiling: Optional[int] = None) -> Plan:
    pool.add_plan(incumbent)
    recs = pool.records(incumbent)
    if not recs:
        return incumbent.copy()
    candidate = _milp_recombine(recs, incumbent.inst, cfg, nv_ceiling=nv_ceiling)
    if candidate is None:
        candidate = _greedy_recombine(recs, incumbent, nv_ceiling=nv_ceiling)
    if nv_ceiling is not None and candidate.nv > nv_ceiling:
        return incumbent.copy()
    return candidate if candidate.dominates(incumbent) else incumbent.copy()

