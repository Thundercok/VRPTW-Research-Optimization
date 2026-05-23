from __future__ import annotations

import math
import random
from typing import List, Optional, Tuple

import numpy as np

from .config import MODES, Config
from .core import Inst, Plan, _check_route, _invalidate, _route_duration_no_return, _route_ok
from .heuristics import _best_insert_position, _insert_customer


def op_random(plan: Plan, size: int) -> Tuple[Plan, List[int]]:
    nodes = [n for r in plan.routes for n in r]
    removed = random.sample(nodes, min(size, len(nodes)))
    rs = set(removed)
    plan.routes = [[n for n in r if n not in rs] for r in plan.routes]
    plan.routes = [r for r in plan.routes if r]
    return _invalidate(plan), removed


def op_worst(plan: Plan, size: int) -> Tuple[Plan, List[int]]:
    inst = plan.inst
    gains: List[Tuple[float, int]] = []
    for route in plan.routes:
        for idx, node in enumerate(route):
            prev = route[idx - 1] if idx > 0 else 0
            nxt = route[idx + 1] if idx < len(route) - 1 else 0
            gains.append((inst.dist[prev, node] + inst.dist[node, nxt] - inst.dist[prev, nxt], node))
    gains.sort(reverse=True)
    # ALNS power-law randomized selection to introduce search diversity
    p = 3.0
    removed: List[int] = []
    rs = set()
    while len(removed) < size and gains:
        idx = int((random.random() ** p) * len(gains))
        _, node = gains.pop(idx)
        removed.append(node)
        rs.add(node)
    plan.routes = [[n for n in r if n not in rs] for r in plan.routes]
    plan.routes = [r for r in plan.routes if r]
    return _invalidate(plan), removed


def op_shaw(plan: Plan, size: int) -> Tuple[Plan, List[int]]:
    inst = plan.inst
    nodes = [n for r in plan.routes for n in r]
    if not nodes:
        return plan, []
    seed_node = random.choice(nodes)
    removed = [seed_node]
    rs = {seed_node}
    max_dist = inst.max_dist + 1e-9
    max_tw = max(inst.due_times - inst.ready_times) + 1e-9
    while len(removed) < size:
        # Dynamically select a reference node from the already removed set
        ref_node = random.choice(removed)
        candidates = [
            (
                n,
                0.5 * inst.dist[ref_node, n] / max_dist
                + 0.4 * abs(inst.ready_times[ref_node] - inst.ready_times[n]) / max_tw
                + 0.1 * abs(inst.demands[ref_node] - inst.demands[n]) / inst.capacity,
            )
            for n in nodes
            if n not in rs
        ]
        if not candidates:
            break
        candidates.sort(key=lambda x: x[1])
        # Use power law selection (p = 3.0) to select similar nodes with high probability
        p = 3.0
        idx = int((random.random() ** p) * len(candidates))
        chosen = candidates[idx][0]
        removed.append(chosen)
        rs.add(chosen)
    plan.routes = [[n for n in r if n not in rs] for r in plan.routes]
    plan.routes = [r for r in plan.routes if r]
    return _invalidate(plan), removed


def op_route_portion_removal(plan: Plan, size: int) -> Tuple[Plan, List[int]]:
    if len(plan.routes) <= 1:
        return op_shaw(plan, size)
    inst = plan.inst
    target = min(max(3, size), sum(len(r) for r in plan.routes))
    removed: List[int] = []
    routes = [r[:] for r in plan.routes]
    while len(removed) < target:
        nonempty = [r for r in routes if r]
        if not nonempty:
            break
        durations = [_route_duration_no_return(r, inst) for r in nonempty]
        avg_dur = max(float(np.mean(durations)), 1e-9)
        max_len = max(len(r) for r in nonempty)
        max_dist = max(inst.max_dist, 1.0)
        scored: List[Tuple[float, int]] = []
        for ridx, route in enumerate(routes):
            if len(route) < 2:
                continue
            coords = inst.coords[np.array(route, dtype=np.int64)]
            centroid = coords.mean(axis=0)
            spatial = float(np.sqrt(((coords - centroid) ** 2).sum(axis=1)).mean()) / max_dist
            duration = _route_duration_no_return(route, inst) / avg_dur
            length_pressure = len(route) / max(max_len, 1)
            score = 0.45 * length_pressure + 0.35 * duration + 0.20 * spatial
            score += random.random() * 0.03
            scored.append((score, ridx))
        if not scored:
            break
        _, ridx = max(scored, key=lambda x: x[0])
        route = routes[ridx]
        remaining = target - len(removed)
        lower = max(1, int(math.floor(0.05 * len(route))))
        upper = min(max(lower, int(math.ceil(0.30 * len(route)))), len(route) - 1, remaining)
        if upper < 1:
            break
        seg_len = random.randint(min(lower, upper), upper)
        strain: List[Tuple[float, int]] = []
        for pos, node in enumerate(route):
            prev = route[pos - 1] if pos > 0 else 0
            nxt = route[pos + 1] if pos < len(route) - 1 else 0
            arc = inst.dist[prev, node] + inst.dist[node, nxt] - inst.dist[prev, nxt]
            tw_width = inst.due_times[node] - inst.ready_times[node]
            urgency = 1.0 - min(tw_width / max(inst.max_tw_width, 1.0), 1.0)
            strain.append((arc / max_dist + 0.35 * urgency, pos))
        # Use randomized selection for the pivot to prevent determinism
        strain.sort(reverse=True, key=lambda x: x[0])
        p = 2.0
        idx = int((random.random() ** p) * len(strain))
        pivot = strain[idx][1]
        start = int(np.clip(pivot - seg_len // 2, 0, len(route) - seg_len))
        segment = route[start : start + seg_len]
        removed.extend(segment)
        routes[ridx] = route[:start] + route[start + seg_len :]
    if not removed:
        return op_shaw(plan, size)
    plan.routes = [r for r in routes if r]
    return _invalidate(plan), removed


def op_tw_urgent(plan: Plan, size: int) -> Tuple[Plan, List[int]]:
    inst = plan.inst
    nodes = [n for r in plan.routes for n in r]
    if not nodes:
        return plan, []
    # Add random noise to the time window width to vary the selection of tight windows
    candidates = sorted(nodes, key=lambda n: (inst.due_times[n] - inst.ready_times[n]) * (1.0 + random.random() * 0.3))
    removed = candidates[:size]
    rs = set(removed)
    plan.routes = [[n for n in r if n not in rs] for r in plan.routes]
    plan.routes = [r for r in plan.routes if r]
    return _invalidate(plan), removed


def op_route_eliminate(plan: Plan, size: int) -> Tuple[Plan, List[int]]:
    if len(plan.routes) <= 1:
        return op_random(plan, size)
    inst = plan.inst
    # Add small random noise to route length and load fraction to vary route choices
    ranked = sorted(
        enumerate(plan.routes),
        key=lambda x: (
            len(x[1]) + random.random() * 0.8,
            sum(inst.demands[n] for n in x[1]) / max(inst.capacity, 1) + random.random() * 0.1,
        ),
    )
    removed: List[int] = []
    drop_ids: set = set()
    for idx, route in ranked:
        if len(removed) >= size:
            break
        removed.extend(route)
        drop_ids.add(idx)
    plan.routes = [r for i, r in enumerate(plan.routes) if i not in drop_ids]
    return _invalidate(plan), removed


def op_route_dispersion_eliminate(plan: Plan, size: int) -> Tuple[Plan, List[int]]:
    if len(plan.routes) <= 1:
        return op_random(plan, size)
    inst = plan.inst
    durations = [_route_duration_no_return(r, inst) for r in plan.routes if r]
    avg_dur = max(float(np.mean(durations)), 1e-9)
    max_dist = max(inst.max_dist, 1.0)
    scored: List[Tuple[float, int]] = []
    for idx, route in enumerate(plan.routes):
        if not route:
            continue
        coords = inst.coords[np.array(route, dtype=np.int64)]
        centroid = coords.mean(axis=0)
        spatial = float(np.sqrt(((coords - centroid) ** 2).sum(axis=1)).mean()) / max_dist
        temporal = _route_duration_no_return(route, inst) / avg_dur
        # Add random noise to increase variety
        noise = random.random() * 0.25
        scored.append((1.5 * spatial + 0.5 * temporal + noise, idx))
    removed: List[int] = []
    drop_ids: set = set()
    for _, idx in sorted(scored, reverse=True):
        removed.extend(plan.routes[idx])
        drop_ids.add(idx)
        if len(removed) >= size:
            break
    plan.routes = [r for i, r in enumerate(plan.routes) if i not in drop_ids]
    return _invalidate(plan), removed


def op_cross_route_shaw(plan: Plan, size: int) -> Tuple[Plan, List[int]]:
    inst = plan.inst
    nodes = [n for r in plan.routes for n in r]
    if not nodes:
        return plan, []
    node_to_route = {n: ri for ri, route in enumerate(plan.routes) for n in route}
    seed_node = random.choice(nodes)
    removed = [seed_node]
    rs = {seed_node}
    max_dist = inst.max_dist + 1e-9
    max_tw = max(inst.due_times - inst.ready_times) + 1e-9
    while len(removed) < size:
        ref_node = random.choice(removed)  # ← once per outer iteration
        ref_route = node_to_route.get(ref_node, -1)
        candidates = []
        for n in nodes:
            if n in rs:
                continue
            cross_route_bonus = -0.2 if node_to_route.get(n, -2) != ref_route else 0.2
            rel = (
                0.5 * inst.dist[ref_node, n] / max_dist
                + 0.4 * abs(inst.ready_times[ref_node] - inst.ready_times[n]) / max_tw
                + 0.1 * abs(inst.demands[ref_node] - inst.demands[n]) / inst.capacity
                + cross_route_bonus
            )
            candidates.append((n, rel))
        if not candidates:
            break
        candidates.sort(key=lambda x: x[1])
        p = 3.0
        idx = int((random.random() ** p) * len(candidates))
        nxt = candidates[idx][0]
        removed.append(nxt)
        rs.add(nxt)
    plan.routes = [[n for n in r if n not in rs] for r in plan.routes]
    plan.routes = [r for r in plan.routes if r]
    return _invalidate(plan), removed


DESTROY = [
    op_random,
    op_worst,
    op_shaw,
    op_route_portion_removal,
    op_tw_urgent,
    op_route_eliminate,
    op_route_dispersion_eliminate,
    op_cross_route_shaw,
]


def op_greedy(plan: Plan, removed: List[int]) -> Plan:
    inst = plan.inst
    for node in sorted(removed, key=lambda n: inst.due_times[n]):
        _insert_customer(plan, node, inst)
    return Plan(plan.routes, inst, plan.algo)


def _regret(plan: Plan, removed: List[int], k: int) -> Plan:
    inst = plan.inst
    remaining: set = set(removed)
    while remaining:
        best_regret, chosen, choice = -float("inf"), None, None
        for node in remaining:
            options = sorted(
                (delta, ri, pos)
                for ri, route in enumerate(plan.routes)
                for delta, pos in [_best_insert_position(node, route, inst)]
                if pos is not None
            )
            if not options:
                continue
            # sum-of-gaps variant of regret-k: penalises nodes with multiple
            # poor alternatives more aggressively than classical Δ_{k-1} - Δ_0
            regret = (
                sum(options[i][0] - options[0][0] for i in range(1, k))
                if len(options) >= k
                else (options[1][0] - options[0][0] if len(options) >= 2 else float("inf"))
            )
            if regret > best_regret:
                best_regret, chosen, choice = regret, node, options[0]
        if chosen is not None and choice is not None:
            _, ri, pos = choice
            if pos is not None:
                plan.routes[ri].insert(pos, chosen)
            plan.invalidate()
            remaining.discard(chosen)  # ← O(1)
        else:
            for node in remaining:
                plan.routes.append([node])
            break
    return Plan(plan.routes, inst, plan.algo)


def op_regret_2(plan: Plan, removed: List[int]) -> Plan:
    return _regret(plan, removed, 2)


def op_regret_3(plan: Plan, removed: List[int]) -> Plan:
    return _regret(plan, removed, 3)


def op_tw_greedy(plan: Plan, removed: List[int]) -> Plan:
    inst = plan.inst
    for node in sorted(removed, key=lambda n: inst.due_times[n] - inst.ready_times[n]):
        _insert_customer(plan, node, inst)
    return Plan(plan.routes, inst, plan.algo)


def _route_arrivals_wait(route: List[int], inst: Inst) -> Tuple[List[float], float]:
    arrivals: List[float] = []
    total_wait = 0.0
    t, prev = 0.0, 0
    for node in route:
        raw = t + inst.dist[prev, node]
        wait = max(0.0, inst.ready_times[node] - raw)
        t = raw + wait
        arrivals.append(float(t))
        total_wait += wait
        t += inst.service_times[node]
        prev = node
    return arrivals, float(total_wait)


def _route_forward_time_slacks(route: List[int], inst: Inst) -> List[float]:
    if not route:
        return []
    arrivals, _ = _route_arrivals_wait(route, inst)
    latest = [0.0] * len(route)
    latest[-1] = float(inst.due_times[route[-1]])
    for idx in range(len(route) - 2, -1, -1):
        node = route[idx]
        nxt = route[idx + 1]
        latest[idx] = min(
            float(inst.due_times[node]),
            latest[idx + 1] - float(inst.service_times[node]) - float(inst.dist[node, nxt]),
        )
    return [max(0.0, latest[idx] - arrivals[idx]) for idx in range(len(route))]


def _fts_best_insert_position(node: int, route: List[int], inst: Inst) -> Tuple[float, Optional[int]]:
    best_cost, best_pos = float("inf"), None
    horizon = max(inst.horizon, 1.0)
    max_dist = max(inst.max_dist, 1.0)
    wait_weight = 0.10 + 0.35 * inst.tw_tight_frac
    long_route_pressure = min((len(route) + 1) / 30.0, 1.0)
    fts_weight = 0.15 + 0.45 * inst.tw_tight_frac + 0.25 * long_route_pressure

    # precompute once — O(route_len)
    base_arrivals, base_wait = _route_arrivals_wait(route, inst)

    for pos in range(len(route) + 1):
        prev = route[pos - 1] if pos > 0 else 0
        nxt = route[pos] if pos < len(route) else 0

        # incremental feasibility: check node insertion only
        t_prev = base_arrivals[pos - 1] if pos > 0 else 0.0
        t_arrive = t_prev + inst.dist[prev, node]
        if t_arrive > inst.due_times[node]:
            continue
        t_depart = max(t_arrive, inst.ready_times[node]) + inst.service_times[node]
        # check downstream propagation: time push at nxt
        if nxt != 0:
            t_nxt_new = t_depart + inst.dist[node, nxt]
            t_nxt_old = base_arrivals[pos] if pos < len(base_arrivals) else None
            if t_nxt_old is not None and t_nxt_new > inst.due_times[nxt]:
                continue

        dist_added = inst.dist[prev, node] + inst.dist[node, nxt] - inst.dist[prev, nxt]

        # approximate wait_added from time push at insertion point
        wait_node = max(0.0, inst.ready_times[node] - (t_prev + inst.dist[prev, node]))
        wait_added = wait_node  # dominant contribution; downstream wait unchanged to first order

        # downstream FTS: min slack from pos onward in base route
        if pos < len(base_arrivals):
            downstream_fts = min(max(0.0, inst.due_times[route[i]] - base_arrivals[i]) for i in range(pos, len(route)))
        else:
            downstream_fts = horizon
        fts_norm = min(downstream_fts / horizon, 1.0)

        composite = float(dist_added + wait_weight * wait_added - fts_weight * fts_norm * max_dist)
        if composite < best_cost:
            best_cost, best_pos = composite, pos

    return best_cost, best_pos


def op_fts_greedy(plan: Plan, removed: List[int]) -> Plan:
    inst = plan.inst
    urgent_first = sorted(
        removed,
        key=lambda n: (inst.due_times[n] - inst.ready_times[n], inst.due_times[n], -inst.demands[n]),
    )
    for node in urgent_first:
        best_cost, best_route, best_pos = float("inf"), None, None
        for ri, route in enumerate(plan.routes):
            cost, pos = _fts_best_insert_position(node, route, inst)
            if pos is not None and cost < best_cost:
                best_cost, best_route, best_pos = cost, ri, pos
        if best_route is not None and best_pos is not None:
            plan.routes[best_route].insert(best_pos, node)
        else:
            plan.routes.append([node])
        plan.invalidate()
    return Plan(plan.routes, inst, plan.algo)


REPAIR = [op_greedy, op_regret_2, op_regret_3, op_tw_greedy, op_fts_greedy]
N_D, N_R = len(DESTROY), len(REPAIR)
N_ACTIONS = N_D * N_R

assert N_D == 8
assert N_R == 5
for _m in MODES:
    assert len(_m.destroy_bias) == N_D
    assert len(_m.repair_bias) == N_R


def accept(cur: Plan, cand: Plan, temp: float, allow_nv_increase: bool = False) -> bool:
    if not cand.feasible:
        return False
    if cand.nv < cur.nv:
        return True
    if cand.nv == cur.nv:
        if cand.cost < cur.cost:
            return True
        return random.random() < math.exp(-(cand.cost - cur.cost) / max(temp, 1e-6))
    if allow_nv_increase and cand.nv == cur.nv + 1:
        return random.random() < math.exp(-2.0)
    return False


def accept_with_nv_ceiling(
    cur: Plan, cand: Plan, temp: float, nv_ceiling: int, allow_nv_increase: bool = False
) -> bool:
    allowed_nv = max(nv_ceiling, cur.nv + 1) if allow_nv_increase else nv_ceiling
    if not cand.feasible or cand.nv > allowed_nv:
        return False
    return accept(cur, cand, temp, allow_nv_increase=allow_nv_increase)


def destroy_size(it: int, n_iters: int, cfg: Config, n_customers: int, scale: float = 1.0) -> int:
    ratio = cfg.destroy_ratio_max - ((cfg.destroy_ratio_max - cfg.destroy_ratio_min) * (it / max(n_iters, 1)))
    ratio = min(cfg.destroy_ratio_max, max(cfg.destroy_ratio_min, ratio * scale))
    return max(3, int(ratio * n_customers))
