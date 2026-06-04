import sys
import os
import json
import random
import numpy as np

sys.path.insert(0, "src")

from vrptw import Config, load_datasets, HybridDDQNSolver
from vrptw.core import Plan, _check_route
from vrptw.pool import RoutePool, recombine_with_route_pool
from vrptw.heuristics import _best_insert_position

# Set seeds
random.seed(42)
np.random.seed(42)

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

# Load 15-vehicle elite plan
elite_path = "results/quick-check/elite_plans/RC101.json"
if not os.path.exists(elite_path):
    print(f"Elite plan {elite_path} not found!")
    sys.exit(1)

with open(elite_path, "r") as f:
    elite_data = json.load(f)

# Convert to Plan object
best = Plan([list(r) for r in elite_data["routes"]], inst)
assert len(best.routes) == elite_data["nv"]
assert best.feasible, "Loaded plan must be feasible!"

print(f"Loaded plan: nv={best.nv}, cost={best.cost:.2f}, feasible={best.feasible}")

cfg = Config(
    alns_iterations=1200,
    hybrid_iterations=1200,
    early_stop_patience=250,
    polish_iterations=80,
    n_runs=1,
)

solver = HybridDDQNSolver(inst, cfg)

# Let's seed the pool manually
pool = RoutePool(inst, cfg)

# Add routes from best plan
pool.add_plan(best)
print(f"Pool size after adding best plan: {len(pool._routes)}")

# Run Clarke-Wright savings seeding
solver._seed_savings_routes(pool, n_randomizations=10)
print(f"Pool size after savings: {len(pool._routes)}")
protected_savings = sum(1 for r in pool._routes.values() if r.protected)
print(f"Protected routes in pool: {protected_savings}")

# Run NV-targeted direct construction seeding
solver._seed_nv_targeted_construction(pool, target_nv=14, n_trials=35)
print(f"Pool size after construction target 14: {len(pool._routes)}")
protected_total = sum(1 for r in pool._routes.values() if r.protected)
print(f"Protected routes in pool now: {protected_total}")

# Run large-destroy seeding
solver._seed_pool_large_destroy(best, pool, n_seeds=20)
print(f"Pool size after large-destroy: {len(pool._routes)}")

# Try MILP recombination to 14 vehicles
rec = recombine_with_route_pool(best, pool, cfg, nv_target=14)
print(f"MILP recombination to 14: feasible={rec.feasible}, nv={rec.nv}, cost={rec.cost:.2f}")

# Analyze the specific route [61, 81, 90] and why its customers are hard to insert
target_route = [61, 81, 90]
print("\n--- Detailed Analysis of Customers 61, 81, 90 ---")
for c in target_route:
    print(f"Customer {c}: demand={inst.demands[c]}, ready={inst.ready_times[c]}, due={inst.due_times[c]}, service={inst.service_times[c]}")

print("\n--- Compatibility with other routes ---")
for c in target_route:
    print(f"\nCustomer {c}:")
    compatible_routes = []
    for ri, route in enumerate(best.routes):
        if route == target_route:
            continue
        # Check load compatibility
        load = sum(inst.demands[n] for n in route)
        if load + inst.demands[c] > inst.capacity:
            # print(f"  Route {ri} (load={load}): Exceeds capacity")
            continue
        
        # Check if there is any feasible insertion position
        delta, pos = _best_insert_position(c, route, inst)
        if pos is not None:
            print(f"  Route {ri} (load={load}, len={len(route)}): Feasible at pos {pos} with delta {delta:.2f}")
            compatible_routes.append(ri)
        else:
            # Let's find why it is infeasible at each position
            pass
    if not compatible_routes:
        print("  NO DIRECTLY COMPATIBLE ROUTES FOUND!")

# Check if we can merge Route 12 and Route 14 into a single feasible route
route_12 = [42, 44, 43, 37, 35]
route_14 = [61, 81, 90]
merged_nodes = route_12 + route_14

print("\n--- Checking all permutations of Route 12 + Route 14 ---")
import itertools
found_permutation = False
count = 0
for p in itertools.permutations(merged_nodes):
    count += 1
    if _check_route(list(p), inst):
        print(f"  FOUND FEASIBLE PERMUTATION: {list(p)}")
        found_permutation = True
        break
print(f"Checked {count} permutations. Found feasible={found_permutation}")

# Print all routes in the pool containing customer 81 and 90
print("\n--- Routes in Pool Containing Customer 81 ---")
routes_81 = []
for nodes_tuple, rec in pool._routes.items():
    if 81 in nodes_tuple:
        routes_81.append((nodes_tuple, rec))
print(f"Found {len(routes_81)} routes containing 81:")
for nodes, rec in sorted(routes_81, key=lambda x: len(x[0]), reverse=True)[:10]:
    print(f"  Route (len={len(nodes)}): {list(nodes)} (cost={rec.cost:.2f}, protected={rec.protected})")

print("\n--- Routes in Pool Containing Customer 90 ---")
routes_90 = []
for nodes_tuple, rec in pool._routes.items():
    if 90 in nodes_tuple:
        routes_90.append((nodes_tuple, rec))
print(f"Found {len(routes_90)} routes containing 90:")
for nodes, rec in sorted(routes_90, key=lambda x: len(x[0]), reverse=True)[:10]:
    print(f"  Route (len={len(nodes)}): {list(nodes)} (cost={rec.cost:.2f}, protected={rec.protected})")







