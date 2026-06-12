from __future__ import annotations

import numpy as np
from numba import njit

from .core import Inst, Plan, _route_cost


@njit(cache=True)
def _best_insert_position_numba(
    node: int,
    route: np.ndarray,
    dist: np.ndarray,
    demands: np.ndarray,
    capacity: float,
    ready: np.ndarray,
    due: np.ndarray,
    service: np.ndarray,
) -> tuple[float, int]:
    best_cost = 1e18
    best_pos = -1
    
    n_nodes = len(route)
    current_load = 0.0
    for idx in range(n_nodes):
        current_load += demands[route[idx]]
    if current_load + demands[node] > capacity:
        return 1e18, -1

    for pos in range(n_nodes + 1):
        prev = route[pos - 1] if pos > 0 else 0
        nxt = route[pos] if pos < n_nodes else 0
        delta = dist[prev, node] + dist[node, nxt] - dist[prev, nxt]
        if delta >= best_cost:
            continue
            
        t = 0.0
        prev_node = 0
        feasible = True
        
        for idx in range(n_nodes + 1):
            if idx == pos:
                curr = node
            else:
                curr = route[idx if idx < pos else idx - 1]
            
            t += dist[prev_node, curr]
            if t < ready[curr]:
                t = ready[curr]
            if t > due[curr]:
                feasible = False
                break
            t += service[curr]
            prev_node = curr
            
        if feasible and t + dist[prev_node, 0] <= due[0]:
            best_cost = delta
            best_pos = pos
            
    return best_cost, best_pos



@njit(cache=True)
def _best_insert_position_pruned_numba(
    node: int,
    route: np.ndarray,
    dist: np.ndarray,
    demands: np.ndarray,
    capacity: float,
    ready: np.ndarray,
    due: np.ndarray,
    service: np.ndarray,
    heatmap: np.ndarray,
    pruning_threshold: float,
) -> tuple[float, int]:
    best_cost = 1e18
    best_pos = -1
    
    n_nodes = len(route)
    current_load = 0.0
    for idx in range(n_nodes):
        current_load += demands[route[idx]]
    if current_load + demands[node] > capacity:
        return 1e18, -1

    for pos in range(n_nodes + 1):
        prev = route[pos - 1] if pos > 0 else 0
        nxt = route[pos] if pos < n_nodes else 0
        
        # Check GNN heatmap pruning
        if heatmap[prev, node] < pruning_threshold or heatmap[node, nxt] < pruning_threshold:
            continue
            
        delta = dist[prev, node] + dist[node, nxt] - dist[prev, nxt]
        if delta >= best_cost:
            continue
            
        t = 0.0
        prev_node = 0
        feasible = True
        
        for idx in range(n_nodes + 1):
            if idx == pos:
                curr = node
            else:
                curr = route[idx if idx < pos else idx - 1]
            
            t += dist[prev_node, curr]
            if t < ready[curr]:
                t = ready[curr]
            if t > due[curr]:
                feasible = False
                break
            t += service[curr]
            prev_node = curr
            
        if feasible and t + dist[prev_node, 0] <= due[0]:
            best_cost = delta
            best_pos = pos
            
    return best_cost, best_pos


def _best_insert_position(node: int, route: list[int], inst: Inst) -> tuple[float, int | None]:
    route_arr = np.array(route, dtype=np.int64)
    best_cost, best_pos = _best_insert_position_numba(
        node,
        route_arr,
        inst.dist,
        inst.demands,
        inst.capacity,
        inst.ready_times,
        inst.due_times,
        inst.service_times,
    )
    if best_pos == -1:
        return float("inf"), None
    return float(best_cost), int(best_pos)


@njit(cache=True)
def _best_insert_position_biased_numba(
    node: int,
    route: np.ndarray,
    dist: np.ndarray,
    demands: np.ndarray,
    capacity: float,
    ready: np.ndarray,
    due: np.ndarray,
    service: np.ndarray,
    heatmap: np.ndarray,
    gamma: float,
) -> tuple[float, float, int]:
    best_biased_cost = 1e18
    actual_cost = 1e18
    best_pos = -1
    
    n_nodes = len(route)
    current_load = 0.0
    for idx in range(n_nodes):
        current_load += demands[route[idx]]
    if current_load + demands[node] > capacity:
        return 1e18, 1e18, -1

    for pos in range(n_nodes + 1):
        prev = route[pos - 1] if pos > 0 else 0
        nxt = route[pos] if pos < n_nodes else 0
        delta = dist[prev, node] + dist[node, nxt] - dist[prev, nxt]
        
        # Apply GNN heatmap edge prediction bias
        p_prev_node = heatmap[prev, node]
        p_node_nxt = heatmap[node, nxt]
        delta_biased = delta * (1.0 - gamma * p_prev_node) * (1.0 - gamma * p_node_nxt)
        
        if delta_biased >= best_biased_cost:
            continue
            
        t = 0.0
        prev_node = 0
        feasible = True
        
        for idx in range(n_nodes + 1):
            if idx == pos:
                curr = node
            else:
                curr = route[idx if idx < pos else idx - 1]
            
            t += dist[prev_node, curr]
            if t < ready[curr]:
                t = ready[curr]
            if t > due[curr]:
                feasible = False
                break
            t += service[curr]
            prev_node = curr
            
        if feasible and t + dist[prev_node, 0] <= due[0]:
            best_biased_cost = delta_biased
            actual_cost = delta
            best_pos = pos
            
    return best_biased_cost, actual_cost, best_pos


def _best_insert_position_biased(
    node: int,
    route: list[int],
    inst: Inst,
    heatmap: np.ndarray,
    gamma: float,
) -> tuple[float, float, int | None]:
    route_arr = np.array(route, dtype=np.int64)
    best_biased, actual_cost, best_pos = _best_insert_position_biased_numba(
        node,
        route_arr,
        inst.dist,
        inst.demands,
        inst.capacity,
        inst.ready_times,
        inst.due_times,
        inst.service_times,
        heatmap,
        gamma,
    )
    if best_pos == -1:
        return float("inf"), float("inf"), None
    return float(best_biased), float(actual_cost), int(best_pos)


def _insert_customer(plan: Plan, node: int, inst: Inst) -> None:
    best_cost, best_route, best_pos = float("inf"), None, None
    for ri, route in enumerate(plan.routes):
        delta, pos = _best_insert_position(node, route, inst)
        if pos is not None and delta < best_cost:
            best_cost, best_route, best_pos = delta, ri, pos
    if best_route is not None:
        plan.routes[best_route].insert(best_pos, node)
    else:
        plan.routes.append([node])
    plan.invalidate()


def _insert_customer_biased(
    plan: Plan,
    node: int,
    inst: Inst,
    heatmap: np.ndarray,
    gamma: float,
) -> None:
    best_biased_cost, best_actual_cost, best_route, best_pos = float("inf"), float("inf"), None, None
    for ri, route in enumerate(plan.routes):
        biased, actual, pos = _best_insert_position_biased(node, route, inst, heatmap, gamma)
        if pos is not None and biased < best_biased_cost:
            best_biased_cost, best_actual_cost, best_route, best_pos = biased, actual, ri, pos
    if best_route is not None:
        plan.routes[best_route].insert(best_pos, node)
    else:
        plan.routes.append([node])
    plan.invalidate()



def _route_cost_list(route: list[int], inst: Inst) -> float:
    if not route:
        return 0.0
    return float(_route_cost(np.array(route, np.int64), inst.dist))


def _route_load(route: list[int], inst: Inst) -> float:
    return float(sum(inst.demands[n] for n in route))


def _route_avg_slack(route: list[int], inst: Inst) -> float:
    if not route:
        return 0.0
    slack, t, prev = 0.0, 0.0, 0
    for node in route:
        t += inst.dist[prev, node]
        t = max(t, inst.ready_times[node])
        slack += inst.due_times[node] - t
        t += inst.service_times[node]
        prev = node
    return slack / len(route)


def build_greedy(inst: Inst, algo: str = "") -> Plan:
    def arrival(route, pos, node, arrivals):
        prev = route[pos - 1] if pos > 0 else 0
        t = arrivals[pos - 1] if pos > 0 else 0.0
        return max(t + inst.dist[prev, node], inst.ready_times[node])

    def feasible_insert(route, pos, node, arrivals, load):
        if load + inst.demands[node] > inst.capacity:
            return False, None
        t = arrival(route, pos, node, arrivals)
        if t > inst.due_times[node]:
            return False, None
        ft, prev = t + inst.service_times[node], node
        for idx in range(pos, len(route)):
            nxt = route[idx]
            ft += inst.dist[prev, nxt]
            ft = max(ft, inst.ready_times[nxt])
            if ft > inst.due_times[nxt]:
                return False, None
            ft += inst.service_times[nxt]
            prev = nxt
        return True, t

    def compute_arrivals(route):
        arrivals, t, prev = [], 0.0, 0
        for node in route:
            t += inst.dist[prev, node]
            t = max(t, inst.ready_times[node])
            arrivals.append(t)
            t += inst.service_times[node]
            prev = node
        return arrivals

    def best_insert_cost(route, node, arrivals, load):
        best_cost, best_pos = float("inf"), None
        for pos in range(len(route) + 1):
            ok, _ = feasible_insert(route, pos, node, arrivals, load)
            if not ok:
                continue
            prev = route[pos - 1] if pos > 0 else 0
            nxt = route[pos] if pos < len(route) else 0
            delta = inst.dist[prev, node] + inst.dist[node, nxt] - inst.dist[prev, nxt]
            if delta < best_cost:
                best_cost, best_pos = delta, pos
        return best_cost, best_pos

    unrouted = list(range(1, inst.n + 1))
    routes: list[list[int]] = []
    while unrouted:
        seed = max(unrouted, key=lambda n: inst.dist[0, n])
        if max(inst.dist[0, seed], inst.ready_times[seed]) > inst.due_times[seed]:
            seed = min(unrouted, key=lambda n: inst.due_times[n])
        route = [seed]
        load = inst.demands[seed]
        arrivals = [max(inst.dist[0, seed], inst.ready_times[seed])]
        unrouted.remove(seed)
        improved = True
        while improved and unrouted:
            improved = False
            best_regret, best_node, best_pos = -float("inf"), None, None
            for node in unrouted:
                c1, pos = best_insert_cost(route, node, arrivals, load)
                if pos is None:
                    continue
                c2 = inst.dist[0, node] + inst.dist[node, 0] - c1
                if c2 > best_regret:
                    best_regret, best_node, best_pos = c2, node, pos
            if best_node is not None:
                route.insert(best_pos, best_node)
                load += inst.demands[best_node]
                arrivals = compute_arrivals(route)
                unrouted.remove(best_node)
                improved = True
        routes.append(route)

    plan = Plan(routes, inst, algo)
    if plan.feasible:
        return plan

    customers = sorted(range(1, inst.n + 1), key=lambda n: (inst.due_times[n], inst.ready_times[n]))
    unrouted_set = set(customers)
    fallback: list[list[int]] = []
    while unrouted_set:
        route_fb: list[int] = []
        node, load, t = 0, 0.0, 0.0
        while unrouted_set:
            feasible = [
                c
                for c in unrouted_set
                if load + inst.demands[c] <= inst.capacity and t + inst.dist[node, c] <= inst.due_times[c]
            ]
            if not feasible:
                break
            nxt = min(feasible, key=lambda c: inst.dist[node, c])
            route_fb.append(nxt)
            unrouted_set.remove(nxt)
            load += inst.demands[nxt]
            t = max(t + inst.dist[node, nxt], inst.ready_times[nxt]) + inst.service_times[nxt]
            node = nxt
        if route_fb:
            fallback.append(route_fb)
        elif unrouted_set:
            nxt = next(iter(unrouted_set))
            fallback.append([nxt])
            unrouted_set.remove(nxt)
    return Plan(fallback, inst, algo)
