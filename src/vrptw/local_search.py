from __future__ import annotations

import numpy as np

from .core import Inst, Plan, _check_route, _route_cost
from .heuristics import (
    _best_insert_position,
    _best_insert_position_numba,
    _best_insert_position_pruned_numba,
    _route_cost_list,
    _route_load,
)
from .numba_kernels import (
    _best_segment_insert_numba,
    _best_segment_insert_pruned_numba,
    _cross_exchange_pair_numba,
    _cross_exchange_pair_pruned_numba,
    _intra_route_optimize_numba,
    _or_opt_intra_numba,
    _swap_evaluate_numba,
    _swap_evaluate_pruned_numba,
    _two_opt_best_numba,
)


def _two_opt_best(route: list[int], inst: Inst) -> list[int]:
    if len(route) < 4:
        return route[:]
    route_arr = np.array(route, dtype=np.int64)
    result, _ = _two_opt_best_numba(
        route_arr,
        inst.dist,
        inst.demands,
        inst.capacity,
        inst.ready_times,
        inst.due_times,
        inst.service_times,
    )
    return list(result)


def _best_relocate(
    plan: Plan,
    nv_ceiling: int | None = None,
    heatmap: np.ndarray | None = None,
    pruning_threshold: float = 0.0,
):
    inst = plan.inst
    best_delta, best_move = -1e-9, None
    max_dist = max(inst.max_dist, 1.0)
    # Use cached route arrays
    route_arrays = plan.route_arrays
    # Pre-calculate route centroids
    centroids = [inst.coords[arr].mean(axis=0) if len(arr) > 0 else inst.coords[0] for arr in route_arrays]

    # Build node-to-route index for kNN filtering
    node_to_route = {}
    for ri, route in enumerate(plan.routes):
        for node in route:
            node_to_route[node] = ri

    for si in range(len(plan.routes)):
        source_route = plan.routes[si]
        for sp in range(len(source_route)):
            node = source_route[sp]
            sn_empty = len(source_route) == 1
            # Compute removal delta in O(1) — removing a node from a feasible
            # route always yields a feasible route (earlier arrivals, lower load)
            prev_s = source_route[sp - 1] if sp > 0 else 0
            next_s = source_route[sp + 1] if sp < len(source_route) - 1 else 0
            remove_delta = inst.dist[prev_s, next_s] - inst.dist[prev_s, node] - inst.dist[node, next_s]
            node_coord = inst.coords[node]

            # kNN-filtered destination routes
            candidate_routes = set()
            if node < len(inst.neighbors_k):
                for neighbor in inst.neighbors_k[node]:
                    if neighbor in node_to_route:
                        candidate_routes.add(node_to_route[neighbor])
            candidate_routes.discard(si)
            # Fallback: if kNN yields too few candidates, use centroid filter
            if len(candidate_routes) < 3:
                for di in range(len(plan.routes)):
                    if di != si and float(np.linalg.norm(centroids[di] - node_coord)) <= 0.55 * max_dist:
                        candidate_routes.add(di)

            for di in candidate_routes:
                # Check if pruning is enabled and heatmap is provided
                if heatmap is not None and pruning_threshold > 0.0:
                    insert_delta, best_pos = _best_insert_position_pruned_numba(
                        node,
                        route_arrays[di],
                        inst.dist,
                        inst.demands,
                        inst.capacity,
                        inst.ready_times,
                        inst.due_times,
                        inst.service_times,
                        heatmap,
                        pruning_threshold,
                    )
                else:
                    insert_delta, best_pos = _best_insert_position_numba(
                        node,
                        route_arrays[di],
                        inst.dist,
                        inst.demands,
                        inst.capacity,
                        inst.ready_times,
                        inst.due_times,
                        inst.service_times,
                    )
                if best_pos == -1:
                    continue
                new_nv = plan.nv - (1 if sn_empty else 0)
                if nv_ceiling is not None and new_nv > nv_ceiling:
                    continue
                delta = remove_delta + insert_delta
                if new_nv < plan.nv:
                    delta -= 1000.0
                if delta < best_delta:
                    best_delta = delta
                    best_move = (si, sp, di, int(best_pos))
                    best_cost_delta = remove_delta + insert_delta
    if best_move is None:
        return None
    return best_move, best_cost_delta


def _apply_relocate(plan: Plan, move: tuple[int, int, int, int]) -> Plan:
    si, sp, di, ip = move
    routes = [r[:] for r in plan.routes]
    node = routes[si].pop(sp)
    if si < di and len(routes[si]) == 0:
        di -= 1
    routes = [r for r in routes if r]
    routes[di].insert(ip, node)
    return Plan(routes, plan.inst, plan.algo)


def _best_swap(
    plan: Plan,
    heatmap: np.ndarray | None = None,
    pruning_threshold: float = 0.0,
):
    inst = plan.inst
    best_delta, best_move = -1e-9, None
    route_arrays = plan.route_arrays
    max_dist = max(inst.max_dist, 1.0)
    centroids = [inst.coords[arr].mean(axis=0) if len(arr) > 0 else inst.coords[0] for arr in route_arrays]

    for si in range(len(plan.routes)):
        for di in range(si + 1, len(plan.routes)):
            # Spatial filter: skip route pairs whose centroids are too far apart
            if float(np.linalg.norm(centroids[si] - centroids[di])) > 0.65 * max_dist:
                continue
            if heatmap is not None and pruning_threshold > 0.0:
                delta, sp, dp = _swap_evaluate_pruned_numba(
                    route_arrays[si],
                    route_arrays[di],
                    inst.dist,
                    inst.demands,
                    inst.capacity,
                    inst.ready_times,
                    inst.due_times,
                    inst.service_times,
                    heatmap,
                    pruning_threshold,
                )
            else:
                delta, sp, dp = _swap_evaluate_numba(
                    route_arrays[si],
                    route_arrays[di],
                    inst.dist,
                    inst.demands,
                    inst.capacity,
                    inst.ready_times,
                    inst.due_times,
                    inst.service_times,
                )
            if sp >= 0 and delta < best_delta:
                best_delta = delta
                best_move = (si, int(sp), di, int(dp))
    if best_move is None:
        return None
    return best_move, best_delta


def _apply_swap(plan: Plan, move: tuple[int, int, int, int]) -> Plan:
    si, sp, di, dp = move
    routes = [r[:] for r in plan.routes]
    routes[si][sp], routes[di][dp] = routes[di][dp], routes[si][sp]
    return Plan(routes, plan.inst, plan.algo)


def _cross_exchange(
    plan: Plan,
    nv_ceiling: int | None = None,
    heatmap: np.ndarray | None = None,
    pruning_threshold: float = 0.0,
) -> Plan | None:
    inst = plan.inst
    if nv_ceiling is not None and plan.nv > nv_ceiling:
        return None
    max_dist = max(inst.max_dist, 1.0)
    best_delta = -1e-9
    best_routes: list[list[int]] | None = None

    # Use cached route arrays
    route_arrays = plan.route_arrays

    # Pre-calculate route metrics for filtering
    route_coords_mean = [inst.coords[arr].mean(axis=0) if len(arr) > 0 else np.zeros(2) for arr in route_arrays]
    route_readys = [float(np.min(inst.ready_times[arr])) if len(arr) > 0 else 0.0 for arr in route_arrays]
    route_dues = [float(np.max(inst.due_times[arr])) if len(arr) > 0 else 0.0 for arr in route_arrays]

    for i in range(len(plan.routes)):
        for j in range(i + 1, len(plan.routes)):
            r1, r2 = plan.routes[i], plan.routes[j]
            if not r1 or not r2:
                continue
            r1_arr, r2_arr = route_arrays[i], route_arrays[j]
            # Route-level spatial/temporal filter
            c1, c2 = route_coords_mean[i], route_coords_mean[j]
            r1_ready, r1_due = route_readys[i], route_dues[i]
            r2_ready, r2_due = route_readys[j], route_dues[j]
            if float(np.linalg.norm(c1 - c2)) > 0.55 * max_dist and not (
                min(r1_due, r2_due) >= max(r1_ready, r2_ready)
            ):
                continue
            old_pair = float(_route_cost(r1_arr, inst.dist)) + float(_route_cost(r2_arr, inst.dist))
            max_len1 = 3 if len(r1) >= 12 else 2
            max_len2 = 3 if len(r2) >= 12 else 2
            # Delegate entire (p1, p2, len1, len2) search to JIT
            if heatmap is not None and pruning_threshold > 0.0:
                delta, p1, len1, p2, len2 = _cross_exchange_pair_pruned_numba(
                    r1_arr,
                    r2_arr,
                    max_len1,
                    max_len2,
                    inst.dist,
                    inst.demands,
                    inst.capacity,
                    inst.ready_times,
                    inst.due_times,
                    inst.service_times,
                    old_pair,
                    heatmap,
                    pruning_threshold,
                )
            else:
                delta, p1, len1, p2, len2 = _cross_exchange_pair_numba(
                    r1_arr,
                    r2_arr,
                    max_len1,
                    max_len2,
                    inst.dist,
                    inst.demands,
                    inst.capacity,
                    inst.ready_times,
                    inst.due_times,
                    inst.service_times,
                    old_pair,
                )
            if p1 >= 0 and delta < best_delta:
                seg2 = list(r2[p2 : p2 + len2])
                seg1 = list(r1[p1 : p1 + len1])
                nr1 = r1[:p1] + seg2 + r1[p1 + len1 :]
                nr2 = r2[:p2] + seg1 + r2[p2 + len2 :]
                routes = [r[:] for r in plan.routes]
                routes[i], routes[j] = nr1, nr2
                best_routes = routes
                best_delta = delta
    if best_routes is not None:
        cand = Plan(best_routes, inst, plan.algo)
        cand._cost = plan.cost + best_delta
        cand._ok = True
        return cand
    return None


def _try_route_compact(plan: Plan, nv_ceiling: int | None = None) -> Plan | None:
    if len(plan.routes) <= 1:
        return None
    inst = plan.inst
    ranked = sorted(
        range(len(plan.routes)),
        key=lambda i: (len(plan.routes[i]), _route_load(plan.routes[i], inst), _route_cost_list(plan.routes[i], inst)),
    )
    for ridx in ranked:
        source = plan.routes[ridx]
        others = [r[:] for i, r in enumerate(plan.routes) if i != ridx]
        ok = True
        for node in sorted(source, key=lambda n: (inst.due_times[n] - inst.ready_times[n], -inst.demands[n])):
            best_c, best_r, best_p = float("inf"), None, None
            for oi, route in enumerate(others):
                delta, pos = _best_insert_position(node, route, inst)
                if pos is not None and delta < best_c:
                    best_c, best_r, best_p = delta, oi, pos
            if best_r is None:
                ok = False
                break
            others[best_r].insert(best_p, node)
        if not ok:
            continue
        cand = Plan([r for r in others if r], inst, plan.algo)
        if not cand.feasible:
            continue
        if nv_ceiling is not None and cand.nv > nv_ceiling:
            continue
        if cand.dominates(plan) or (cand.nv == plan.nv and cand.cost + 1e-9 < plan.cost):
            return cand
    return None


def _best_or_opt(
    plan: Plan,
    nv_ceiling: int | None = None,
    heatmap: np.ndarray | None = None,
    pruning_threshold: float = 0.0,
):
    inst = plan.inst
    best_delta, best_move = -1e-9, None
    route_arrays = plan.route_arrays
    max_dist = max(inst.max_dist, 1.0)
    centroids = [inst.coords[arr].mean(axis=0) if len(arr) > 0 else inst.coords[0] for arr in route_arrays]

    # Build node-to-route index for kNN filtering
    node_to_route = {}
    for ri, route in enumerate(plan.routes):
        for node in route:
            node_to_route[node] = ri

    for si in range(len(plan.routes)):
        source_route = plan.routes[si]
        for L in (2, 3):
            for sp in range(len(source_route) - L + 1):
                seg_arr = np.array(source_route[sp : sp + L], dtype=np.int64)
                sn_empty = len(source_route) == L
                # Compute removal delta in O(1) — removing a segment from a
                # feasible route always yields a feasible route
                prev_s = source_route[sp - 1] if sp > 0 else 0
                next_s = source_route[sp + L] if sp + L < len(source_route) else 0
                # Distance of removed arc chain: prev→seg[0]→...→seg[-1]→next
                remove_dist = inst.dist[prev_s, source_route[sp]]
                for k in range(L - 1):
                    remove_dist += inst.dist[source_route[sp + k], source_route[sp + k + 1]]
                remove_dist += inst.dist[source_route[sp + L - 1], next_s]
                remove_delta = inst.dist[prev_s, next_s] - remove_dist

                # kNN-filtered destination routes (using first node of segment)
                seg_node = source_route[sp]
                candidate_routes = set()
                if seg_node < len(inst.neighbors_k):
                    for neighbor in inst.neighbors_k[seg_node]:
                        if neighbor in node_to_route:
                            candidate_routes.add(node_to_route[neighbor])
                candidate_routes.discard(si)
                # Fallback: if kNN yields too few candidates, add centroid-close routes
                if len(candidate_routes) < 3:
                    seg_center = inst.coords[seg_arr].mean(axis=0)
                    for di in range(len(plan.routes)):
                        if di != si and float(np.linalg.norm(centroids[di] - seg_center)) <= 0.55 * max_dist:
                            candidate_routes.add(di)

                for di in candidate_routes:
                    # JIT-compiled segment insertion evaluation
                    if heatmap is not None and pruning_threshold > 0.0:
                        insert_delta, best_pos, rev_int = _best_segment_insert_pruned_numba(
                            seg_arr,
                            route_arrays[di],
                            inst.dist,
                            inst.demands,
                            inst.capacity,
                            inst.ready_times,
                            inst.due_times,
                            inst.service_times,
                            heatmap,
                            pruning_threshold,
                        )
                    else:
                        insert_delta, best_pos, rev_int = _best_segment_insert_numba(
                            seg_arr,
                            route_arrays[di],
                            inst.dist,
                            inst.demands,
                            inst.capacity,
                            inst.ready_times,
                            inst.due_times,
                            inst.service_times,
                        )
                    if best_pos == -1:
                        continue
                    new_nv = plan.nv - (1 if sn_empty else 0)
                    if nv_ceiling is not None and new_nv > nv_ceiling:
                        continue
                    delta = remove_delta + insert_delta
                    if new_nv < plan.nv:
                        delta -= 1000.0
                    if delta < best_delta:
                        best_delta = delta
                        best_move = (si, sp, L, di, int(best_pos), bool(rev_int))
                        best_cost_delta = remove_delta + insert_delta
    if best_move is None:
        return None
    return best_move, best_cost_delta


def _apply_or_opt(plan: Plan, move: tuple[int, int, int, int, int, bool]) -> Plan:
    si, sp, L, di, ip, is_reversed = move
    routes = [r[:] for r in plan.routes]
    seg = routes[si][sp : sp + L]
    del routes[si][sp : sp + L]
    if si < di and len(routes[si]) == 0:
        di -= 1
    routes = [r for r in routes if r]
    if is_reversed:
        seg = list(reversed(seg))
    routes[di] = routes[di][:ip] + seg + routes[di][ip:]
    return Plan(routes, plan.inst, plan.algo)


def _merge_orderings(r1: list[int], r2: list[int], inst: Inst) -> list[list[int]]:
    combined = list(r1) + list(r2)
    depot = 0
    center = inst.coords[np.array(combined, dtype=np.int64)].mean(axis=0)
    polar = sorted(
        combined,
        key=lambda n: np.arctan2(inst.coords[n][1] - center[1], inst.coords[n][0] - center[0]),
    )
    nearest_seed = min(combined, key=lambda n: inst.dist[depot, n])
    farthest_seed = max(combined, key=lambda n: inst.dist[depot, n])

    orderings = [
        sorted(combined, key=lambda n: (inst.due_times[n], inst.ready_times[n], inst.dist[depot, n])),
        sorted(combined, key=lambda n: (inst.ready_times[n], inst.due_times[n], inst.dist[depot, n])),
        sorted(combined, key=lambda n: inst.dist[depot, n]),
        sorted(combined, key=lambda n: inst.dist[depot, n], reverse=True),
        polar,
        list(reversed(polar)),
        sorted(combined, key=lambda n: (inst.dist[nearest_seed, n], inst.due_times[n])),
        sorted(combined, key=lambda n: (inst.dist[farthest_seed, n], inst.due_times[n])),
    ]

    deduped: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()
    for ordering in orderings:
        key = tuple(ordering)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ordering)
    return deduped


def _build_merged_route(ordering: list[int], inst: Inst) -> list[int] | None:
    route: list[int] = []
    for node in ordering:
        _, pos = _best_insert_position(node, route, inst)
        if pos is None:
            return None
        route.insert(pos, node)
    return route if _check_route(route, inst) else None


def _ranked_merge_pairs(plan: Plan, max_pairs: int) -> list[tuple[int, int]]:
    inst = plan.inst
    route_stats = []
    for i, route in enumerate(plan.routes):
        route_stats.append((i, _route_load(route, inst), _route_cost_list(route, inst), len(route)))

    candidates: list[tuple[float, int, int]] = []
    for pos_i, (i, load_i, cost_i, len_i) in enumerate(route_stats):
        for j, load_j, cost_j, len_j in route_stats[pos_i + 1 :]:
            if load_i + load_j > inst.capacity:
                continue
            depot_saving = inst.dist[0, plan.routes[i][0]] + inst.dist[plan.routes[i][-1], 0]
            depot_saving += inst.dist[0, plan.routes[j][0]] + inst.dist[plan.routes[j][-1], 0]
            size_bias = len_i + len_j
            pair_score = cost_i + cost_j - 0.15 * depot_saving - 2.0 * size_bias
            candidates.append((float(pair_score), i, j))
    candidates.sort(key=lambda x: x[0])
    return [(i, j) for _, i, j in candidates[:max_pairs]]


def merged_route_candidates(plan: Plan, max_pairs: int = 24, max_routes: int = 32) -> list[list[int]]:
    if len(plan.routes) <= 1:
        return []

    inst = plan.inst
    candidates: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()
    for i, j in _ranked_merge_pairs(plan, max_pairs=max_pairs):
        for ordering in _merge_orderings(plan.routes[i], plan.routes[j], inst):
            merged_route = _build_merged_route(ordering, inst)
            if merged_route is None:
                continue
            key = tuple(merged_route)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(merged_route)
            if len(candidates) >= max_routes:
                return candidates
    return candidates


def _try_route_merge(plan: Plan, max_pairs: int = 24) -> Plan | None:
    inst = plan.inst
    if len(plan.routes) <= 1:
        return None

    best_merged: Plan | None = None

    for i, j in _ranked_merge_pairs(plan, max_pairs=max_pairs):
        r1 = plan.routes[i]
        r2 = plan.routes[j]
        for ordering in _merge_orderings(r1, r2, inst):
            merged_route = _build_merged_route(ordering, inst)
            if merged_route is None:
                continue

            surviving = [r[:] for k, r in enumerate(plan.routes) if k != i and k != j]
            surviving.append(merged_route)
            cand = Plan(surviving, inst, plan.algo)
            if not cand.feasible:
                continue
            if best_merged is None or cand.dominates(best_merged) or cand.nv < best_merged.nv:
                best_merged = cand

    return best_merged


def _covers_all_customers(routes: list[list[int]], inst: Inst) -> bool:
    nodes = [n for route in routes for n in route]
    return len(nodes) == inst.n and len(set(nodes)) == inst.n and all(1 <= n <= inst.n for n in nodes)


def _insertion_options(
    node: int,
    routes: list[list[int]],
    inst: Inst,
    max_options: int = 3,
) -> list[tuple[float, int, int]]:
    options: list[tuple[float, int, int]] = []
    for ri, route in enumerate(routes):
        delta, pos = _best_insert_position(node, route, inst)
        if pos is not None:
            options.append((float(delta), ri, pos))
    options.sort(key=lambda x: x[0])
    return options[:max_options]


def _select_buffered_pending_node(pending: list[int], routes: list[list[int]], inst: Inst) -> int:
    best_idx = 0
    best_key: tuple[float, ...] | None = None
    for idx, node in enumerate(pending):
        options = 0
        best_delta = float("inf")
        for route in routes:
            delta, pos = _best_insert_position(node, route, inst)
            if pos is not None:
                options += 1
                best_delta = min(best_delta, float(delta))
        width = float(inst.due_times[node] - inst.ready_times[node])
        key = (float(options), width, float(inst.due_times[node]), -float(inst.demands[node]), best_delta)
        if best_key is None or key < best_key:
            best_key = key
            best_idx = idx
    return best_idx


def _buffered_ejection_options(
    node: int,
    routes: list[list[int]],
    inst: Inst,
    max_options: int = 3,
) -> list[tuple[float, int, list[int], int]]:
    options: list[tuple[float, int, list[int], int]] = []
    max_dist = max(inst.max_dist, 1.0)
    horizon = max(inst.horizon, 1.0)

    for ri, route in enumerate(routes):
        old_cost = _route_cost_list(route, inst)
        for eject_pos, ejected in enumerate(route):
            stripped = route[:eject_pos] + route[eject_pos + 1 :]
            _, pos_node = _best_insert_position(node, stripped, inst)
            if pos_node is None:
                continue

            new_route = stripped[:pos_node] + [node] + stripped[pos_node:]
            if not _check_route(new_route, inst):
                continue

            trial_routes = [r[:] for r in routes]
            trial_routes[ri] = new_route
            landing = _insertion_options(ejected, trial_routes, inst, max_options=1)
            if landing:
                landing_score = landing[0][0]
                orphan_penalty = 0.0
            else:
                landing_score = max_dist
                orphan_penalty = max_dist

            width_penalty = (inst.due_times[ejected] - inst.ready_times[ejected]) / horizon
            route_delta = _route_cost_list(new_route, inst) - old_cost
            score = float(route_delta + 0.35 * landing_score + orphan_penalty + 0.05 * width_penalty * max_dist)
            options.append((score, ri, new_route, ejected))

    options.sort(key=lambda x: x[0])
    return options[:max_options]


def _try_buffered_route_elimination(
    plan: Plan,
    target_idx: int,
    max_ejections: int = 4,
    beam_width: int = 8,
) -> Plan | None:
    if len(plan.routes) <= 1:
        return None

    inst = plan.inst
    target = sorted(
        plan.routes[target_idx],
        key=lambda n: (inst.due_times[n] - inst.ready_times[n], inst.due_times[n], -inst.demands[n]),
    )
    routes = [r[:] for i, r in enumerate(plan.routes) if i != target_idx]
    states: list[tuple[list[list[int]], list[int], int, float]] = [(routes, target, 0, 0.0)]
    max_steps = len(target) + max_ejections

    def finish_if_complete(routes_: list[list[int]], pending_: list[int]) -> Plan | None:
        if pending_:
            return None
        cand = Plan([r for r in routes_ if r], inst, plan.algo)
        if cand.nv == plan.nv - 1 and cand.feasible and _covers_all_customers(cand.routes, inst):
            return cand
        return None

    for _ in range(max_steps):
        next_states: list[tuple[list[list[int]], list[int], int, float]] = []
        for routes_cur, pending, ejections, score in states:
            completed = finish_if_complete(routes_cur, pending)
            if completed is not None:
                return completed
            if not pending:
                continue

            node_idx = _select_buffered_pending_node(pending, routes_cur, inst)
            node = pending[node_idx]
            rest = pending[:node_idx] + pending[node_idx + 1 :]

            for delta, ri, pos in _insertion_options(node, routes_cur, inst):
                new_routes = [r[:] for r in routes_cur]
                new_routes[ri] = new_routes[ri][:pos] + [node] + new_routes[ri][pos:]
                next_states.append((new_routes, rest[:], ejections, score + delta))

            if ejections >= max_ejections:
                continue

            for eject_score, ri, new_route, ejected in _buffered_ejection_options(node, routes_cur, inst):
                new_routes = [r[:] for r in routes_cur]
                new_routes[ri] = new_route
                next_states.append((new_routes, rest + [ejected], ejections + 1, score + eject_score))

        if not next_states:
            break

        deduped: list[tuple[list[list[int]], list[int], int, float]] = []
        seen: set[tuple[tuple[tuple[int, ...], ...], tuple[int, ...]]] = set()
        for item in sorted(next_states, key=lambda s: (len(s[1]), s[2], s[3])):
            routes_cur, pending, _, _ = item
            signature = (tuple(tuple(route) for route in routes_cur), tuple(sorted(pending)))
            if signature in seen:
                continue
            seen.add(signature)
            deduped.append(item)
            if len(deduped) >= beam_width:
                break
        states = deduped

    for routes_cur, pending, _, _ in states:
        completed = finish_if_complete(routes_cur, pending)
        if completed is not None:
            return completed
    return None


def _buffered_route_elimination(
    plan: Plan,
    max_rounds: int = 2,
    max_ejections: int = 6,
    beam_width: int = 16,
    pool=None,
    hard_mode: bool = False,
) -> Plan:
    if hard_mode:
        beam_width = max(beam_width * 2, 32)
        max_ejections = max(max_ejections + 4, 10)
    best = plan.copy()
    for _ in range(max_rounds):
        if len(best.routes) <= 1:
            break
        ranked = sorted(
            range(len(best.routes)),
            key=lambda i: (
                len(best.routes[i]),
                _route_load(best.routes[i], best.inst),
                _route_cost_list(best.routes[i], best.inst),
            ),
        )
        # Try all routes as targets when the smallest route has ≤ 4 customers
        # (signals the instance is close to an NV drop, e.g. RC101's [61,81,90])
        smallest_len = len(best.routes[ranked[0]]) if ranked else 0
        n_targets = len(ranked) if smallest_len <= 4 else min(6, len(ranked))
        improved = False
        for target_idx in ranked[:n_targets]:
            local_ejections = max(2, min(max_ejections, len(best.routes[target_idx]) // 2 + 1))
            cand = _try_buffered_route_elimination(
                best,
                target_idx,
                max_ejections=local_ejections,
                beam_width=beam_width,
            )
            if cand is None:
                continue
            cand = local_search(cand, max_passes=1, nv_ceiling=cand.nv, max_ls_moves=10, pool=pool)
            if cand.feasible and cand.nv < best.nv and _covers_all_customers(cand.routes, best.inst):
                best = cand
                if pool is not None:
                    pool.add_plan(best)
                improved = True
                break
        if not improved:
            break
    return best


def _intra_route_or_opt(plan: Plan, nv_ceiling: int | None = None) -> Plan | None:
    """
    Intra-Route Or-Opt — JIT-accelerated.
    Moves customer segments (length 1-3) to better positions within
    the SAME route to minimise total distance (TD).
    """
    inst = plan.inst
    improved = False
    routes: list[list[int]] = []
    for route in plan.routes:
        if len(route) < 4:
            routes.append(route[:])
            continue
        route_arr = np.array(route, dtype=np.int64)
        result, imp = _or_opt_intra_numba(
            route_arr,
            inst.dist,
            inst.demands,
            inst.capacity,
            inst.ready_times,
            inst.due_times,
            inst.service_times,
        )
        if imp:
            improved = True
        routes.append(list(result))
    if not improved:
        return None
    cand = Plan(routes, inst, plan.algo)
    cand._ok = True
    if nv_ceiling is not None and cand.nv > nv_ceiling:
        return None
    return cand if cand.dominates(plan) else None


def _intra_route_optimize(route: list[int], inst: Inst, max_passes: int = 25) -> list[int]:
    """
    Run 2-opt and or-opt(1,2,3) on a single route until convergence.
    Fully JIT-compiled — designed for wide-TW instances where routes
    carry 25+ customers.
    """
    if len(route) < 4:
        return route[:]
    route_arr = np.array(route, dtype=np.int64)
    result = _intra_route_optimize_numba(
        route_arr,
        inst.dist,
        inst.demands,
        inst.capacity,
        inst.ready_times,
        inst.due_times,
        inst.service_times,
        max_passes,
    )
    return list(result)


def td_converge_polish(plan: Plan, max_passes: int = 25) -> Plan:
    """
    Apply _intra_route_optimize to every route independently.
    Called during the BKS-NV TD polish phase. Unlike local_search(),
    this never modifies route assignments — only improves sequence quality.
    """
    routes = [_intra_route_optimize(r, plan.inst, max_passes) for r in plan.routes]
    cand = Plan(routes, plan.inst, plan.algo)
    return cand if cand.feasible and cand.cost + 1e-9 < plan.cost else plan


def local_search(
    plan: Plan,
    max_passes: int = 1,
    nv_ceiling: int | None = None,
    max_ls_moves: int = 5,
    pool=None,
    heatmap: np.ndarray | None = None,
    pruning_threshold: float = 0.0,
) -> Plan:
    if not plan.feasible:
        return plan
    best = plan.copy()

    for _ in range(max_passes):
        improved = False
        routes = []
        for route in best.routes:
            nr = _two_opt_best(route, best.inst)
            routes.append(nr)
            if nr != route:
                improved = True
        if improved:
            best = Plan(routes, best.inst, best.algo)
            best._ok = True

        moves = 0
        while moves < max_ls_moves:
            # 1. Relocate Move
            res = _best_relocate(best, nv_ceiling=nv_ceiling, heatmap=heatmap, pruning_threshold=pruning_threshold)
            if res is not None:
                move, cost_delta = res
                cand = _apply_relocate(best, move)
                cand._cost = best.cost + cost_delta
                cand._ok = True
                if cand.dominates(best) or (cand.nv == best.nv and cand.cost + 1e-9 < best.cost):
                    best, improved = cand, True
                    moves += 1
                    if pool is not None:
                        pool.add_plan(best)  # Immediate hot-commit to active pool
                    continue

            # 2. Intra-Route Or-Opt
            intra = _intra_route_or_opt(best, nv_ceiling=nv_ceiling)
            if intra is not None:
                best, improved = intra, True
                moves += 1
                if pool is not None:
                    pool.add_plan(best)
                continue

            # 3. Swap Move
            res = _best_swap(best, heatmap=heatmap, pruning_threshold=pruning_threshold)
            if res is not None:
                move, cost_delta = res
                cand = _apply_swap(best, move)
                cand._cost = best.cost + cost_delta
                cand._ok = True
                if cand.cost + 1e-9 < best.cost:
                    best, improved = cand, True
                    moves += 1
                    if pool is not None:
                        pool.add_plan(best)
                    continue

            # 4. Or-Opt Move
            res = _best_or_opt(best, nv_ceiling=nv_ceiling, heatmap=heatmap, pruning_threshold=pruning_threshold)
            if res is not None:
                move, cost_delta = res
                cand = _apply_or_opt(best, move)
                cand._cost = best.cost + cost_delta
                cand._ok = True
                if cand.dominates(best) or (cand.nv == best.nv and cand.cost + 1e-9 < best.cost):
                    best, improved = cand, True
                    moves += 1
                    if pool is not None:
                        pool.add_plan(best)
                    continue

            # 5. Cross Exchange
            cross = _cross_exchange(best, nv_ceiling=nv_ceiling, heatmap=heatmap, pruning_threshold=pruning_threshold)
            if cross is not None:
                best, improved = cross, True
                moves += 1
                if pool is not None:
                    pool.add_plan(best)
                continue

            # 6. Route Compaction
            compact = _try_route_compact(best, nv_ceiling=nv_ceiling)
            if compact is not None:
                best, improved = compact, True
                moves += 1
                if pool is not None:
                    pool.add_plan(best)
                continue
            break

        if not improved:
            break

    # ── Post-Search Diversification Seeding (Executed exactly once at exit) ──
    if pool is not None:
        for route in merged_route_candidates(best):
            pool.add_route(route)
        merged = _try_route_merge(best)
        if merged is not None:
            pool.add_plan(merged)

    return best


def _try_chain_elimination(plan: Plan, target_idx: int) -> Plan | None:
    """
    Depth-3 ejection chain: c → Ri (displacing d) → d → Rj (displacing e) → e → Rk.
    Falls back to depth-2 then depth-1 per customer; depth-3 only fires when
    shallower levels fail, keeping average runtime close to depth-2.

    Branching cap: at depth-3, only the top-3 displacement candidates per route
    are evaluated to bound worst-case complexity at O(k × r × L × r × 3 × r).
    """
    inst = plan.inst
    target = plan.routes[target_idx]
    routes = [r[:] for i, r in enumerate(plan.routes) if i != target_idx]

    for c in sorted(target, key=lambda n: inst.due_times[n] - inst.ready_times[n]):
        # ── Level 1: direct insertion ─────────────────────────────────────────
        best_delta, best_ri, best_pos = float("inf"), None, None
        for ri, route in enumerate(routes):
            delta, pos = _best_insert_position(c, route, inst)
            if pos is not None and delta < best_delta:
                best_delta, best_ri, best_pos = delta, ri, pos
        if best_ri is not None:
            routes[best_ri].insert(best_pos, c)
            continue

        # ── Level 2: single ejection  c → Ri (ejects d) → d → Rj ────────────
        chain2: tuple | None = None
        best2 = float("inf")
        for ri, route in enumerate(routes):
            for eject_pos, d in enumerate(route):
                stripped = route[:eject_pos] + route[eject_pos + 1 :]
                dc, pc = _best_insert_position(c, stripped, inst)
                if pc is None:
                    continue
                for rj in range(len(routes)):
                    if rj == ri:
                        continue
                    dd, pd = _best_insert_position(d, routes[rj], inst)
                    if pd is not None and dc + dd < best2:
                        best2 = dc + dd
                        chain2 = (ri, eject_pos, d, rj)

        if chain2 is not None:
            ri, ep, d, rj = chain2
            stripped_ri = routes[ri][:ep] + routes[ri][ep + 1 :]
            _, pc = _best_insert_position(c, stripped_ri, inst)
            if pc is None:
                return None
            routes[ri] = stripped_ri[:pc] + [c] + stripped_ri[pc:]
            _, pd = _best_insert_position(d, routes[rj], inst)
            if pd is None:
                return None
            routes[rj].insert(pd, d)
            continue

        # ── Level 3: double ejection  c→Ri(d)→Rj(e)→Rk ─────────────────────
        # Capped branching: only top-3 (ri, d) pairs by marginal insertion cost
        depth3_candidates: list[tuple[float, int, int, int]] = []  # (cost_c, ri, eject_pos, d)
        for ri, route in enumerate(routes):
            for eject_pos, d in enumerate(route):
                stripped = route[:eject_pos] + route[eject_pos + 1 :]
                dc, pc = _best_insert_position(c, stripped, inst)
                if pc is not None:
                    depth3_candidates.append((dc, ri, eject_pos, d))
        depth3_candidates.sort()

        chain3: tuple | None = None
        best3 = float("inf")
        for dc, ri, eject_pos, d in depth3_candidates[:3]:  # cap at 3
            for rj in range(len(routes)):
                if rj == ri:
                    continue
                for eject_pos_j, e in enumerate(routes[rj]):
                    stripped_j = routes[rj][:eject_pos_j] + routes[rj][eject_pos_j + 1 :]
                    dd, pd = _best_insert_position(d, stripped_j, inst)
                    if pd is None:
                        continue
                    for rk in range(len(routes)):
                        if rk in (ri, rj):
                            continue
                        de, pe = _best_insert_position(e, routes[rk], inst)
                        if pe is not None and dc + dd + de < best3:
                            best3 = dc + dd + de
                            chain3 = (ri, eject_pos, d, rj, eject_pos_j, e, rk)

        if chain3 is None:
            return None  # c unplaceable at depth-3; this target route cannot be eliminated

        ri, ep_i, d, rj, ep_j, e, rk = chain3
        # Apply depth-3 chain
        stripped_ri = routes[ri][:ep_i] + routes[ri][ep_i + 1 :]
        _, pc = _best_insert_position(c, stripped_ri, inst)
        if pc is None:
            return None
        routes[ri] = stripped_ri[:pc] + [c] + stripped_ri[pc:]

        stripped_rj = routes[rj][:ep_j] + routes[rj][ep_j + 1 :]
        _, pd = _best_insert_position(d, stripped_rj, inst)
        if pd is None:
            return None
        routes[rj] = stripped_rj[:pd] + [d] + stripped_rj[pd:]

        _, pe = _best_insert_position(e, routes[rk], inst)
        if pe is None:
            return None
        routes[rk].insert(pe, e)

    cand = Plan([r for r in routes if r], inst, plan.algo)
    return cand if cand.feasible else None


def _ejection_chain_eliminate(plan: Plan) -> Plan | None:
    """
    Tries to eliminate up to the 4 smallest routes via depth-2 ejection chains.
    Complements _iterative_route_elimination: handles cases where greedy
    insertion fails due to TW blocking but a 2-step chain resolves the conflict.

    Complexity: O(k × n_target × n_routes × route_len × n_routes) per call —
    fast enough for post-search use on 100-customer instances.
    Returns first feasible NV-1 plan found, or None.
    """
    if len(plan.routes) <= 1:
        return None

    ranked = sorted(
        range(len(plan.routes)),
        key=lambda i: (len(plan.routes[i]), sum(plan.inst.demands[n] for n in plan.routes[i])),
    )
    for target_idx in ranked[:4]:
        result = _try_chain_elimination(plan, target_idx)
        if result is not None:
            return result
    return None


def _iterative_route_elimination(
    plan: Plan,
    inst: Inst,
    max_rounds: int = 6,
    pool=None,  # RoutePool | None — seeds pool after each success
) -> Plan:
    best = plan.copy()
    for _ in range(max_rounds):
        if len(best.routes) <= 1:
            break
        sorted_idxs = sorted(
            range(len(best.routes)),
            key=lambda i: (
                len(best.routes[i]),
                _route_load(best.routes[i], inst),
                _route_cost_list(best.routes[i], inst),
            ),
        )
        eliminated = False
        for target_idx in sorted_idxs[:5]:
            target = best.routes[target_idx]
            others = [r[:] for i, r in enumerate(best.routes) if i != target_idx]
            ok = True
            for node in sorted(target, key=lambda n: inst.due_times[n] - inst.ready_times[n]):
                best_d, best_r, best_p = float("inf"), None, None
                for oi, route in enumerate(others):
                    delta, pos = _best_insert_position(node, route, inst)
                    if pos is not None and delta < best_d:
                        best_d, best_r, best_p = delta, oi, pos
                if best_r is None:
                    ok = False
                    break
                others[best_r].insert(best_p, node)
            if not ok:
                continue
            cand = Plan([r for r in others if r], inst, best.algo)
            if not cand.feasible:
                continue
            cand = local_search(cand, max_passes=2, nv_ceiling=cand.nv, pool=pool)
            if cand.feasible:
                if pool is not None:
                    pool.add_plan(cand)
                best = cand
                eliminated = True
                break
        if not eliminated:
            break
    return best
