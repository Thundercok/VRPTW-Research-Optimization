import sys
import os
import random
import numpy as np
import torch
import math

sys.path.insert(0, "src")

from vrptw import Config, load_datasets, HybridDDQNSolver
from vrptw.core import _check_route, _avg_slack
from vrptw.heuristics import _route_cost_list, _route_load, _route_avg_slack
from vrptw.pool import RoutePool, RouteRecord

# Load dataset
datasets = load_datasets("data/Solomon")
inst = None
for g, insts in datasets.items():
    for i in insts:
        if i.name == "RC101":
            inst = i
            break

if inst is None:
    print("Instance RC101 not found!")
    sys.exit(1)

print(f"Loaded instance: {inst.name}")

# Configure
cfg = Config(
    alns_iterations=5,
    hybrid_iterations=5,
    early_stop_patience=5,
    polish_iterations=5,
    n_runs=1,
)

solver = HybridDDQNSolver(inst, cfg)

# Let's inspect the pool after 5 iterations
pool = RoutePool(inst, cfg)
# Populate the pool with initial routes from solver run
plan, history = solver.solve(seed=42)
print(f"ALNS best solution: nv={plan.nv}, cost={plan.cost:.2f}")

# Re-create a fresh pool or use the solver's pool?
# Let's look at solver's pool
solver_pool = solver.archive._plans.get(inst.name, [])
print(f"Plans in archive: {len(solver_pool)}")

# Let's look at solver's active pool size
print("Let's check solver's final pool")

print("\n--- Diagnostic for _seed_savings_routes ---")
# Let's run a custom version of _seed_savings_routes that counts everything
n_randomizations = 10
inst = solver.inst
savings_gen = 0
savings_feasible = 0
savings_new = 0
savings_retained = 0

# Copy solver's pool to analyze it
test_pool = RoutePool(inst, cfg)
for r in solver.archive._plans.get(inst.name, []):
    test_pool.add_plan(r)

# Let's also add routes from ALNS run to test_pool
for r in plan.routes:
    test_pool.add_route(r)

initial_pool_size = len(test_pool._routes)
print(f"Initial pool size: {initial_pool_size}")

for run in range(n_randomizations):
    # savings computation
    savings = []
    for i in range(1, inst.n + 1):
        for j in range(i + 1, inst.n + 1):
            s = float(inst.dist[0, i] + inst.dist[0, j] - inst.dist[i, j])
            if run > 0:
                s *= 1.0 + (random.random() - 0.5) * 0.08 * run
            savings.append((s, i, j))
    savings.sort(key=lambda x: -x[0])

    routes = [[i] for i in range(inst.n + 1)]
    loads = [0.0] + [float(inst.demands[i]) for i in range(1, inst.n + 1)]
    which_route = {i: i for i in range(1, inst.n + 1)}

    for _, i, j in savings:
        ri = which_route.get(i)
        rj = which_route.get(j)
        if ri is None or rj is None or ri == rj:
            continue
        r1 = routes[ri]
        r2 = routes[rj]
        if not r1 or not r2:
            continue
        if loads[ri] + loads[rj] > inst.capacity:
            continue

        merged = None
        for a, b in (
            (r1, r2),
            (r1[::-1], r2),
            (r1, r2[::-1]),
            (r1[::-1], r2[::-1]),
        ):
            candidate = a + b
            savings_gen += 1
            if _check_route(candidate, inst):
                savings_feasible += 1
                merged = candidate
                break

        if merged is None:
            continue

        routes[ri] = merged
        loads[ri] += loads[rj]
        routes[rj] = []
        loads[rj] = 0.0
        for c in r2:
            which_route[c] = ri

    for idx, route in enumerate(routes):
        if idx > 0 and route:
            key = tuple(route)
            if key not in test_pool._routes:
                savings_new += 1
                before_add = len(test_pool._routes)
                test_pool.add_route(route)
                if key in test_pool._routes:
                    savings_retained += 1

print(f"Generated candidate merges: {savings_gen}")
print(f"Feasible merges: {savings_feasible}")
print(f"New routes (not in pool): {savings_new}")
print(f"Retained in pool (after trim): {savings_retained}")
print(f"Final pool size after savings: {len(test_pool._routes)}")


print("\n--- Diagnostic for _seed_nv_targeted_construction ---")
test_pool = RoutePool(inst, cfg)
# Reset pool
for r in plan.routes:
    test_pool.add_route(r)
initial_pool_size = len(test_pool._routes)
print(f"Initial pool size: {initial_pool_size}")

target_nv = 14
n_trials = 35
const_gen = 0
const_feasible = 0
const_new = 0
const_retained = 0

customers = list(range(1, inst.n + 1))
tw_sorted = sorted(customers, key=lambda n: (inst.ready_times[n] + inst.due_times[n]) / 2.0)
step = max(1, inst.n // target_nv)

from vrptw.heuristics import _best_insert_position
from vrptw.local_search import _two_opt_best

for trial in range(n_trials):
    offset = trial % step
    seeds = []
    seen_seeds = set()
    for i in range(target_nv):
        idx = min(i * step + offset, inst.n - 1)
        s = tw_sorted[idx]
        if s not in seen_seeds:
            seeds.append(s)
            seen_seeds.add(s)

    route_lists = [[s] for s in seeds]
    route_loads = [float(inst.demands[s]) for s in seeds]

    unassigned = [c for c in customers if c not in seeds]
    unassigned.sort(key=lambda n: inst.due_times[n] - inst.ready_times[n])

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

    # Check and add
    for route in route_lists:
        if route:
            const_gen += 1
            if _check_route(route, inst):
                const_feasible += 1
                key = tuple(route)
                if key not in test_pool._routes:
                    const_new += 1
                    test_pool.add_route(route)
                    if key in test_pool._routes:
                        const_retained += 1

            if len(route) >= 4:
                improved = _two_opt_best(route, inst)
                if improved != route:
                    const_gen += 1
                    if _check_route(improved, inst):
                        const_feasible += 1
                        key = tuple(improved)
                        if key not in test_pool._routes:
                            const_new += 1
                            test_pool.add_route(improved)
                            if key in test_pool._routes:
                                const_retained += 1

print(f"Generated routes (incl. 2-opt): {const_gen}")
print(f"Feasible routes: {const_feasible}")
print(f"New routes (not in pool): {const_new}")
print(f"Retained in pool (after trim): {const_retained}")
print(f"Final pool size after construction: {len(test_pool._routes)}")
