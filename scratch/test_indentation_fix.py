import sys
import os
import json
import random
import numpy as np

sys.path.insert(0, "src")

from vrptw import Config, load_datasets
from vrptw.core import Plan, _check_route
from vrptw.heuristics import _route_cost_list, _route_load, _best_insert_position
from vrptw.local_search import (
    _covers_all_customers,
    _select_buffered_pending_node,
    _insertion_options,
    _buffered_ejection_options,
    local_search,
)

# Load dataset
datasets = load_datasets("data/Solomon")
inst = None
for g, insts in datasets.items():
    for i in insts:
        if i.name == "RC101":
            inst = i
            break

# Load 15-vehicle elite plan
elite_path = "results/quick-check/elite_plans/RC101.json"
with open(elite_path, "r") as f:
    elite_data = json.load(f)

best = Plan([list(r) for r in elite_data["routes"]], inst)
print(f"Loaded plan: nv={best.nv}, cost={best.cost:.2f}, feasible={best.feasible}")

# Define custom ejection options without orphan penalties
def custom_buffered_ejection_options(
    node: int,
    routes: list[list[int]],
    inst: Inst,
    max_options: int = 15,
) -> list[tuple[float, int, list[int], int]]:
    options = []
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

            route_delta = _route_cost_list(new_route, inst) - old_cost
            score = float(route_delta)
            options.append((score, ri, new_route, ejected))

    options.sort(key=lambda x: x[0])
    return options[:max_options]

# Fixed version of _try_buffered_route_elimination
def fixed_try_buffered_route_elimination(
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
    states = [(routes, target, 0, 0.0)]
    max_steps = len(target) + max_ejections

    def finish_if_complete(routes_: list[list[int]], pending_: list[int]) -> Plan | None:
        if pending_:
            return None
        cand = Plan([r for r in routes_ if r], inst, plan.algo)
        if cand.nv == plan.nv - 1 and cand.feasible and _covers_all_customers(cand.routes, inst):
            return cand
        return None

    for step in range(max_steps):
        next_states = []
        for routes_cur, pending, ejections, score in states:
            completed = finish_if_complete(routes_cur, pending)
            if completed is not None:
                print(f"    Found completed plan at step {step}!")
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

            # Use custom ejection finder
            for eject_score, ri, new_route, ejected in custom_buffered_ejection_options(node, routes_cur, inst, max_options=20):
                new_routes = [r[:] for r in routes_cur]
                new_routes[ri] = new_route
                next_states.append((new_routes, rest + [ejected], ejections + 1, score + eject_score))

        if not next_states:
            break

        # Update active states
        deduped = []
        seen = set()
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
        
        # Print progress
        if states:
            min_pending = min(len(s[1]) for s in states)
            max_eject = max(s[2] for s in states)
            print(f"      Step {step:2d}: active_states={len(states)}, min_pending={min_pending}, max_ejections={max_eject}")

    for routes_cur, pending, _, _ in states:
        completed = finish_if_complete(routes_cur, pending)
        if completed is not None:
            return completed
    return None

# Run the fixed version
print("\nRunning fixed buffered route elimination on 15-vehicle plan...")
for target_idx in range(len(best.routes)):
    print(f"Trying to eliminate route {target_idx}: {best.routes[target_idx]}")
    res = fixed_try_buffered_route_elimination(best, target_idx, max_ejections=6, beam_width=64)
    if res is not None:
        print(f"SUCCESS: Eliminated route {target_idx}! New plan: nv={res.nv}, cost={res.cost:.2f}, feasible={res.feasible}")
        break
else:
    print("FAILED: Fixed buffered route elimination could not empty any route directly.")

# Compare different sorting keys for unassigned customers in targeted construction
target_nv = 14
n_trials = 35

customers = list(range(1, inst.n + 1))
tw_sorted = sorted(customers, key=lambda n: (inst.ready_times[n] + inst.due_times[n]) / 2.0)
step = max(1, inst.n // target_nv)

for sort_name, sort_key in [
    ("TW Width", lambda n: inst.due_times[n] - inst.ready_times[n]),
    ("Due Time (EDF)", lambda n: inst.due_times[n]),
    ("Ready Time", lambda n: inst.ready_times[n]),
    ("Composite (Ready + Due)", lambda n: inst.ready_times[n] + inst.due_times[n]),
]:
    print(f"\n--- Checking sorting key: {sort_name} ---")
    total_unassigned = 0
    min_unassigned = inst.n
    for trial in range(n_trials):
        offset = trial % step
        seeds = [tw_sorted[min(i * step + offset, inst.n - 1)] for i in range(target_nv)]
        
        route_lists = [[s] for s in seeds]
        route_loads = [float(inst.demands[s]) for s in seeds]
        
        unassigned = [c for c in customers if c not in seeds]
        unassigned.sort(key=sort_key)
        
        unassigned_count = 0
        for c in unassigned:
            best_delta, best_ri, best_pos = float("inf"), None, None
            for ri, route in enumerate(route_lists):
                if route_loads[ri] + inst.demands[c] > inst.capacity:
                    continue
                delta, pos = _best_insert_position(c, route, inst)
                if pos is not None and delta < best_delta:
                    best_delta, best_ri, best_pos = delta, ri, pos
            if best_ri is not None:
                route_lists[best_ri].insert(best_pos, c)
                route_loads[best_ri] += inst.demands[c]
            else:
                unassigned_count += 1
        total_unassigned += unassigned_count
        if unassigned_count < min_unassigned:
            min_unassigned = unassigned_count
    print(f"  Avg unassigned: {total_unassigned / n_trials:.1f}, Min unassigned: {min_unassigned}")




