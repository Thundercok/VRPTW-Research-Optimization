from __future__ import annotations

import math
import random

import numpy as np
from numba import njit

from .config import MODES, Config
from .core import Inst, Plan, _invalidate, _route_duration_no_return
from .heuristics import _best_insert_position, _insert_customer


def op_random(plan: Plan, size: int) -> tuple[Plan, list[int]]:
    nodes = [n for r in plan.routes for n in r]
    removed = random.sample(nodes, min(size, len(nodes)))
    rs = set(removed)
    plan.routes = [[n for n in r if n not in rs] for r in plan.routes]
    plan.routes = [r for r in plan.routes if r]
    return _invalidate(plan), removed


def op_worst(plan: Plan, size: int) -> tuple[Plan, list[int]]:
    inst = plan.inst
    gains: list[tuple[float, int]] = []
    for route in plan.routes:
        for idx, node in enumerate(route):
            prev = route[idx - 1] if idx > 0 else 0
            nxt = route[idx + 1] if idx < len(route) - 1 else 0
            gains.append((inst.dist[prev, node] + inst.dist[node, nxt] - inst.dist[prev, nxt], node))
    gains.sort(reverse=True)
    p = 3.0
    removed: list[int] = []
    rs = set()
    while len(removed) < size and gains:
        idx = int((random.random() ** p) * len(gains))
        _, node = gains.pop(idx)
        removed.append(node)
        rs.add(node)
    plan.routes = [[n for n in r if n not in rs] for r in plan.routes]
    plan.routes = [r for r in plan.routes if r]
    return _invalidate(plan), removed


def op_shaw(plan: Plan, size: int) -> tuple[Plan, list[int]]:
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
        ref_node = random.choice(removed)
        neighbors = inst.neighbors_k[ref_node]
        candidates = [
            (
                n,
                0.5 * inst.dist[ref_node, n] / max_dist
                + 0.4 * abs(inst.ready_times[ref_node] - inst.ready_times[n]) / max_tw
                + 0.1 * abs(inst.demands[ref_node] - inst.demands[n]) / inst.capacity,
            )
            for n in neighbors
            if n not in rs
        ]
        if not candidates:
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
        p = 3.0
        idx = int((random.random() ** p) * len(candidates))
        chosen = candidates[idx][0]
        removed.append(chosen)
        rs.add(chosen)
    plan.routes = [[n for n in r if n not in rs] for r in plan.routes]
    plan.routes = [r for r in plan.routes if r]
    return _invalidate(plan), removed


def op_route_portion_removal(plan: Plan, size: int) -> tuple[Plan, list[int]]:
    if len(plan.routes) <= 1:
        return op_shaw(plan, size)
    inst = plan.inst
    target = min(max(3, size), sum(len(r) for r in plan.routes))
    removed: list[int] = []
    routes = [r[:] for r in plan.routes]
    while len(removed) < target:
        nonempty = [r for r in routes if r]
        if not nonempty:
            break
        durations = [_route_duration_no_return(r, inst) for r in nonempty]
        avg_dur = max(float(np.mean(durations)), 1e-9)
        max_len = max(len(r) for r in nonempty)
        max_dist = max(inst.max_dist, 1.0)
        scored: list[tuple[float, int]] = []
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
        strain: list[tuple[float, int]] = []
        for pos, node in enumerate(route):
            prev = route[pos - 1] if pos > 0 else 0
            nxt = route[pos + 1] if pos < len(route) - 1 else 0
            arc = inst.dist[prev, node] + inst.dist[node, nxt] - inst.dist[prev, nxt]
            tw_width = inst.due_times[node] - inst.ready_times[node]
            urgency = 1.0 - min(tw_width / max(inst.max_tw_width, 1.0), 1.0)
            strain.append((arc / max_dist + 0.35 * urgency, pos))
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


def op_tw_urgent(plan: Plan, size: int) -> tuple[Plan, list[int]]:
    inst = plan.inst
    nodes = [n for r in plan.routes for n in r]
    if not nodes:
        return plan, []
    candidates = sorted(nodes, key=lambda n: (inst.due_times[n] - inst.ready_times[n]) * (1.0 + random.random() * 0.3))
    removed = candidates[:size]
    rs = set(removed)
    plan.routes = [[n for n in r if n not in rs] for r in plan.routes]
    plan.routes = [r for r in plan.routes if r]
    return _invalidate(plan), removed


def op_route_eliminate(plan: Plan, size: int) -> tuple[Plan, list[int]]:
    if len(plan.routes) <= 1:
        return op_random(plan, size)
    inst = plan.inst
    ranked = sorted(
        enumerate(plan.routes),
        key=lambda x: (
            len(x[1]) + random.random() * 0.8,
            sum(inst.demands[n] for n in x[1]) / max(inst.capacity, 1) + random.random() * 0.1,
        ),
    )
    removed: list[int] = []
    drop_ids: set = set()
    for idx, route in ranked:
        if len(removed) >= size:
            break
        removed.extend(route)
        drop_ids.add(idx)
    plan.routes = [r for i, r in enumerate(plan.routes) if i not in drop_ids]
    return _invalidate(plan), removed


def op_route_dispersion_eliminate(plan: Plan, size: int) -> tuple[Plan, list[int]]:
    if len(plan.routes) <= 1:
        return op_random(plan, size)
    inst = plan.inst
    durations = [_route_duration_no_return(r, inst) for r in plan.routes if r]
    avg_dur = max(float(np.mean(durations)), 1e-9)
    max_dist = max(inst.max_dist, 1.0)
    scored: list[tuple[float, int]] = []
    for idx, route in enumerate(plan.routes):
        if not route:
            continue
        coords = inst.coords[np.array(route, dtype=np.int64)]
        centroid = coords.mean(axis=0)
        spatial = float(np.sqrt(((coords - centroid) ** 2).sum(axis=1)).mean()) / max_dist
        temporal = _route_duration_no_return(route, inst) / avg_dur
        noise = random.random() * 0.25
        scored.append((1.5 * spatial + 0.5 * temporal + noise, idx))
    removed: list[int] = []
    drop_ids: set = set()
    for _, idx in sorted(scored, reverse=True):
        if len(removed) >= size:
            break
        removed.extend(plan.routes[idx])
        drop_ids.add(idx)
    plan.routes = [r for i, r in enumerate(plan.routes) if i not in drop_ids]
    return _invalidate(plan), removed


def op_cross_route_shaw(plan: Plan, size: int) -> tuple[Plan, list[int]]:
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
        ref_node = random.choice(removed)
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


def _remove_neighborhood_additional(plan: Plan, removed: list[int], size: int) -> list[int]:
    inst = plan.inst
    nodes = [n for r in plan.routes for n in r]
    rs = set(removed)
    candidates = [n for n in nodes if n not in rs]
    if not candidates or len(removed) >= size:
        return removed

    max_dist = inst.max_dist + 1e-9
    max_tw = max(inst.due_times - inst.ready_times) + 1e-9

    scores = []
    for n in candidates:
        min_score = float("inf")
        for ref in removed:
            score = (
                0.5 * inst.dist[ref, n] / max_dist
                + 0.4 * abs(inst.ready_times[ref] - inst.ready_times[n]) / max_tw
                + 0.1 * abs(inst.demands[ref] - inst.demands[n]) / inst.capacity
            )
            if score < min_score:
                min_score = score
        scores.append((n, min_score))

    scores.sort(key=lambda x: x[1])

    p = 3.0
    while len(removed) < size and scores:
        idx = int((random.random() ** p) * len(scores))
        chosen, _ = scores.pop(idx)
        removed.append(chosen)
        rs.add(chosen)

    return removed


def op_route_costly_eliminate(plan: Plan, size: int) -> tuple[Plan, list[int]]:
    if len(plan.routes) <= 1:
        return op_random(plan, size)
    inst = plan.inst
    scored = []
    from .heuristics import _route_cost_list

    for idx, route in enumerate(plan.routes):
        if not route:
            continue
        cost = _route_cost_list(route, inst)
        noise = random.random() * 0.1 * cost
        scored.append((cost + noise, idx))

    best_idx = max(scored, key=lambda x: x[0])[1]
    removed = list(plan.routes[best_idx])
    drop_ids = {best_idx}

    plan.routes = [r for i, r in enumerate(plan.routes) if i not in drop_ids]

    if len(removed) < size:
        removed = _remove_neighborhood_additional(plan, removed, size)
        rs = set(removed)
        plan.routes = [[n for n in r if n not in rs] for r in plan.routes]
        plan.routes = [r for r in plan.routes if r]

    return _invalidate(plan), removed


def op_route_merge_sample(plan: Plan, size: int) -> tuple[Plan, list[int]]:
    if len(plan.routes) <= 1:
        return op_random(plan, size)
    inst = plan.inst

    candidates = []
    for i, r1 in enumerate(plan.routes):
        load1 = sum(inst.demands[n] for n in r1)
        for j, r2 in enumerate(plan.routes):
            if j <= i:
                continue
            load2 = sum(inst.demands[n] for n in r2)
            if load1 + load2 > inst.capacity:
                continue
            combined_len = len(r1) + len(r2)
            load_fill = (load1 + load2) / max(inst.capacity, 1)
            score = combined_len - load_fill * 4.0 + random.random() * 1.5
            candidates.append((score, i, j))

    if not candidates:
        return op_route_eliminate(plan, size)

    candidates.sort()
    p = 3.0
    idx = int((random.random() ** p) * len(candidates))
    _, i, j = candidates[idx]

    small_idx = i if len(plan.routes[i]) <= len(plan.routes[j]) else j
    removed = list(plan.routes[small_idx])
    plan.routes = [r for k, r in enumerate(plan.routes) if k != small_idx]
    return _invalidate(plan), removed


def op_route_absorb_disrupt(plan: Plan, size: int) -> tuple[Plan, list[int]]:
    """Absorb the smallest route and disrupt border zones of neighboring routes.

    1. Select the route with fewest customers.
    2. Remove all customers from that route.
    3. For each absorbed customer, identify the nearest customers still in
       other routes and remove those 'border zone' neighbors.
    4. Cap total removals at ``size``.
    """
    if len(plan.routes) <= 1:
        return op_random(plan, size)
    inst = plan.inst
    # Find smallest route
    ranked = sorted(
        enumerate(plan.routes),
        key=lambda x: (len(x[1]) + random.random() * 0.5,),
    )
    target_idx, target_route = ranked[0]
    removed: list[int] = list(target_route)
    drop_ids: set = {target_idx}

    # Build remaining node list for border-zone disruption
    remaining_nodes = [n for i, r in enumerate(plan.routes) if i != target_idx for n in r]

    # For each absorbed customer, find nearest border-zone neighbors
    if remaining_nodes and len(removed) < size:
        absorbed_set = set(removed)
        border_candidates: list[tuple[float, int]] = []
        for node in removed:
            for rn in remaining_nodes:
                if rn not in absorbed_set:
                    dist_score = float(inst.dist[node, rn]) + random.random() * 0.1
                    border_candidates.append((dist_score, rn))

        # Sort by proximity and select unique border nodes
        border_candidates.sort(key=lambda x: x[0])
        seen = set(removed)
        for _, rn in border_candidates:
            if len(removed) >= size:
                break
            if rn not in seen:
                removed.append(rn)
                seen.add(rn)

    rs = set(removed)
    plan.routes = [[n for n in r if n not in rs] for r in plan.routes]
    plan.routes = [r for r in plan.routes if r]
    return _invalidate(plan), removed


def op_neural_worst(plan: Plan, size: int, heatmap: np.ndarray | None = None) -> tuple[Plan, list[int]]:
    """Remove customers whose current edges have low GNN-predicted probability.

    For each customer *node* currently placed between *prev* and *nxt* in its
    route, compute a removal score:
        score = (1 - heatmap[prev, node]) + (1 - heatmap[node, nxt])
    High score ⇒ the GNN thinks these edges are unlikely in a good solution
    ⇒ the customer is misplaced ⇒ prioritise it for removal.

    Falls back to ``op_worst`` when no heatmap is available.
    """
    if heatmap is None:
        return op_worst(plan, size)

    inst = plan.inst
    scores: list[tuple[float, int]] = []
    for route in plan.routes:
        for idx, node in enumerate(route):
            prev = route[idx - 1] if idx > 0 else 0
            nxt = route[idx + 1] if idx < len(route) - 1 else 0
            # Low heatmap probability → high removal score
            neural_score = (1.0 - heatmap[prev, node]) + (1.0 - heatmap[node, nxt])
            # Blend with detour cost for stability (30% distance, 70% neural)
            detour = inst.dist[prev, node] + inst.dist[node, nxt] - inst.dist[prev, nxt]
            detour_norm = detour / max(inst.max_dist, 1e-9)
            score = 0.7 * neural_score + 0.3 * detour_norm
            scores.append((score, node))
    scores.sort(reverse=True)

    p = 3.0
    removed: list[int] = []
    rs: set = set()
    while len(removed) < size and scores:
        idx = int((random.random() ** p) * len(scores))
        _, node = scores.pop(idx)
        if node not in rs:
            removed.append(node)
            rs.add(node)
    plan.routes = [[n for n in r if n not in rs] for r in plan.routes]
    plan.routes = [r for r in plan.routes if r]
    return _invalidate(plan), removed


def op_neural_shaw(plan: Plan, size: int, heatmap: np.ndarray | None = None) -> tuple[Plan, list[int]]:
    """Remove a coherent cluster of poorly-connected customers using Shaw relatedness and GNN edge probability.

    Falls back to ``op_shaw`` when no heatmap is available.
    """
    if heatmap is None:
        return op_shaw(plan, size)

    inst = plan.inst
    nodes = [n for r in plan.routes for n in r]
    if not nodes:
        return plan, []

    # 1. Seed: pick customer with lowest avg GNN edge probability to neighbors in current route
    seed_node = None
    min_avg_prob = 2.0
    for route in plan.routes:
        for idx, node in enumerate(route):
            prev = route[idx - 1] if idx > 0 else 0
            nxt = route[idx + 1] if idx < len(route) - 1 else 0
            avg_prob = 0.5 * (heatmap[prev, node] + heatmap[node, nxt])
            if avg_prob < min_avg_prob:
                min_avg_prob = avg_prob
                seed_node = node

    if seed_node is None:
        seed_node = random.choice(nodes)

    removed = [seed_node]
    rs = {seed_node}
    max_dist = inst.max_dist + 1e-9
    max_tw = max(inst.due_times - inst.ready_times) + 1e-9

    while len(removed) < size:
        ref_node = random.choice(removed)
        neighbors = inst.neighbors_k[ref_node]
        candidates = []
        for n in neighbors:
            if n not in rs:
                spatial_rel = inst.dist[ref_node, n] / max_dist
                temporal_rel = abs(inst.ready_times[ref_node] - inst.ready_times[n]) / max_tw
                demand_rel = abs(inst.demands[ref_node] - inst.demands[n]) / inst.capacity
                avg_heatmap_prob = sum(0.5 * (heatmap[r, n] + heatmap[n, r]) for r in removed) / len(removed)
                score = (
                    0.35 * spatial_rel
                    + 0.25 * temporal_rel
                    + 0.30 * (1.0 - avg_heatmap_prob)
                    + 0.10 * demand_rel
                )
                candidates.append((n, score))

        if not candidates:
            for n in nodes:
                if n not in rs:
                    spatial_rel = inst.dist[ref_node, n] / max_dist
                    temporal_rel = abs(inst.ready_times[ref_node] - inst.ready_times[n]) / max_tw
                    demand_rel = abs(inst.demands[ref_node] - inst.demands[n]) / inst.capacity
                    avg_heatmap_prob = sum(0.5 * (heatmap[r, n] + heatmap[n, r]) for r in removed) / len(removed)
                    score = (
                        0.35 * spatial_rel
                        + 0.25 * temporal_rel
                        + 0.30 * (1.0 - avg_heatmap_prob)
                        + 0.10 * demand_rel
                    )
                    candidates.append((n, score))

        if not candidates:
            break

        candidates.sort(key=lambda x: x[1])
        p = 3.0
        idx = int((random.random() ** p) * len(candidates))
        chosen = candidates[idx][0]
        removed.append(chosen)
        rs.add(chosen)

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
    op_route_costly_eliminate,
    op_cross_route_shaw,
    op_route_merge_sample,
    op_route_absorb_disrupt,
    op_neural_worst,
    op_neural_shaw,
]


def op_greedy(plan: Plan, removed: list[int], heatmap: np.ndarray | None = None, gamma: float = 0.0) -> Plan:
    inst = plan.inst
    if heatmap is not None and gamma > 0.0:
        from .heuristics import _insert_customer_biased
        for node in sorted(removed, key=lambda n: inst.due_times[n]):
            _insert_customer_biased(plan, node, inst, heatmap, gamma)
    else:
        for node in sorted(removed, key=lambda n: inst.due_times[n]):
            _insert_customer(plan, node, inst)
    return Plan(plan.routes, inst, plan.algo)


def _regret(plan: Plan, removed: list[int], k: int, heatmap: np.ndarray | None = None, gamma: float = 0.0) -> Plan:
    inst = plan.inst
    remaining: set = set(removed)
    while remaining:
        best_regret, chosen, choice = -float("inf"), None, None
        for node in remaining:
            if heatmap is not None and gamma > 0.0:
                from .heuristics import _best_insert_position_biased
                options = []
                for ri, route in enumerate(plan.routes):
                    biased, actual, pos = _best_insert_position_biased(node, route, inst, heatmap, gamma)
                    if pos is not None:
                        options.append((biased, actual, ri, pos))
                options.sort(key=lambda x: x[0])
            else:
                options = []
                for ri, route in enumerate(plan.routes):
                    delta, pos = _best_insert_position(node, route, inst)
                    if pos is not None:
                        options.append((delta, delta, ri, pos))
                options.sort(key=lambda x: x[0])
                
            if not options:
                continue
                
            regret = (
                sum(options[i][0] - options[0][0] for i in range(1, k))
                if len(options) >= k
                else (options[1][0] - options[0][0] if len(options) >= 2 else float("inf"))
            )
            if regret > best_regret:
                # We store best choice, but keep track of actual cost to make insertion correctly
                best_regret, chosen, choice = regret, node, (options[0][2], options[0][3])
                
        if chosen is not None and choice is not None:
            ri, pos = choice
            plan.routes[ri].insert(pos, chosen)
            plan.invalidate()
            remaining.discard(chosen)
        else:
            for node in remaining:
                plan.routes.append([node])
            break
    return Plan(plan.routes, inst, plan.algo)


def op_regret_2(plan: Plan, removed: list[int], heatmap: np.ndarray | None = None, gamma: float = 0.0) -> Plan:
    return _regret(plan, removed, 2, heatmap, gamma)


def op_regret_3(plan: Plan, removed: list[int], heatmap: np.ndarray | None = None, gamma: float = 0.0) -> Plan:
    return _regret(plan, removed, 3, heatmap, gamma)


def op_tw_greedy(plan: Plan, removed: list[int], heatmap: np.ndarray | None = None, gamma: float = 0.0) -> Plan:
    inst = plan.inst
    if heatmap is not None and gamma > 0.0:
        from .heuristics import _insert_customer_biased
        for node in sorted(removed, key=lambda n: inst.due_times[n] - inst.ready_times[n]):
            _insert_customer_biased(plan, node, inst, heatmap, gamma)
    else:
        for node in sorted(removed, key=lambda n: inst.due_times[n] - inst.ready_times[n]):
            _insert_customer(plan, node, inst)
    return Plan(plan.routes, inst, plan.algo)



def _route_arrivals_wait(route: list[int], inst: Inst) -> tuple[list[float], float]:
    arrivals: list[float] = []
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


@njit(cache=True)
def _route_arrivals_wait_numba(
    route: np.ndarray,
    dist: np.ndarray,
    ready: np.ndarray,
    service: np.ndarray,
    arrivals: np.ndarray,
) -> float:
    total_wait = 0.0
    t, prev = 0.0, 0
    for idx in range(len(route)):
        node = route[idx]
        raw = t + dist[prev, node]
        wait = max(0.0, ready[node] - raw)
        t = raw + wait
        arrivals[idx] = t
        total_wait += wait
        t += service[node]
        prev = node
    return total_wait


def _route_forward_time_slacks(route: list[int], inst: Inst) -> list[float]:
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


@njit(cache=True)
def _fts_best_insert_position_numba(
    node: int,
    route: np.ndarray,
    dist: np.ndarray,
    demands: np.ndarray,
    capacity: float,
    ready: np.ndarray,
    due: np.ndarray,
    service: np.ndarray,
    horizon: float,
    max_dist: float,
    tw_tight_frac: float,
) -> tuple[float, int]:
    best_cost = 1e18
    best_pos = -1
    
    n_nodes = len(route)
    current_load = 0.0
    for idx in range(n_nodes):
        current_load += demands[route[idx]]
    if current_load + demands[node] > capacity:
        return 1e18, -1

    wait_weight = 0.10 + 0.35 * tw_tight_frac
    long_route_pressure = min((n_nodes + 1) / 30.0, 1.0)
    fts_weight = 0.15 + 0.45 * tw_tight_frac + 0.25 * long_route_pressure

    base_arrivals = np.zeros(n_nodes, dtype=np.float64)
    _route_arrivals_wait_numba(route, dist, ready, service, base_arrivals)

    for pos in range(n_nodes + 1):
        prev = route[pos - 1] if pos > 0 else 0
        nxt = route[pos] if pos < n_nodes else 0

        t_prev = base_arrivals[pos - 1] if pos > 0 else 0.0
        t_arrive = t_prev + dist[prev, node]
        if t_arrive > due[node]:
            continue
        t_depart = max(t_arrive, ready[node]) + service[node]
        if nxt != 0:
            t_nxt_new = t_depart + dist[node, nxt]
            if t_nxt_new > due[nxt]:
                continue

        dist_added = dist[prev, node] + dist[node, nxt] - dist[prev, nxt]
        wait_node = max(0.0, ready[node] - (t_prev + dist[prev, node]))
        wait_added = wait_node

        if pos < n_nodes:
            min_slack = horizon
            for i in range(pos, n_nodes):
                s = max(0.0, due[route[i]] - base_arrivals[i])
                if s < min_slack:
                    min_slack = s
            downstream_fts = min_slack
        else:
            downstream_fts = horizon
        fts_norm = min(downstream_fts / horizon, 1.0)

        composite = dist_added + wait_weight * wait_added - fts_weight * fts_norm * max_dist
        if composite < best_cost:
            best_cost = composite
            best_pos = pos

    return best_cost, best_pos


def _fts_best_insert_position(node: int, route: list[int], inst: Inst) -> tuple[float, int | None]:
    route_arr = np.array(route, dtype=np.int64)
    best_cost, best_pos = _fts_best_insert_position_numba(
        node,
        route_arr,
        inst.dist,
        inst.demands,
        inst.capacity,
        inst.ready_times,
        inst.due_times,
        inst.service_times,
        max(inst.horizon, 1.0),
        max(inst.max_dist, 1.0),
        inst.tw_tight_frac,
    )
    if best_pos == -1:
        return float("inf"), None
    return float(best_cost), int(best_pos)


def op_fts_greedy(plan: Plan, removed: list[int], heatmap: np.ndarray | None = None, gamma: float = 0.0) -> Plan:
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

assert N_D == 13
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
