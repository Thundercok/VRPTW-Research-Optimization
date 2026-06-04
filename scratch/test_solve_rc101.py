import sys
import os

sys.path.insert(0, "src")

from vrptw import Config, load_datasets, HybridDDQNSolver
from vrptw.core import _check_route

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

# Configure with 400 iterations
cfg = Config(
    alns_iterations=400,
    hybrid_iterations=400,
    early_stop_patience=200,
    polish_iterations=80,
    n_runs=1,
)

solver = HybridDDQNSolver(inst, cfg)

# Let's override the solver methods to print debug info
original_savings = solver._seed_savings_routes
def debug_savings(pool, n_randomizations=10):
    before = len(pool._routes)
    original_savings(pool, n_randomizations)
    after = len(pool._routes)
    print(f"[DEBUG] _seed_savings_routes added {after - before} routes. Total pool size: {after}")

original_targeted = solver._seed_nv_targeted_construction
def debug_targeted(pool, target_nv, n_trials=40):
    before = len(pool._routes)
    original_targeted(pool, target_nv, n_trials)
    after = len(pool._routes)
    print(f"[DEBUG] _seed_nv_targeted_construction(target={target_nv}) added {after - before} routes. Total pool size: {after}")

solver._seed_savings_routes = debug_savings
def debug_targeted_nv(pool, target_nv, n_trials):
    debug_targeted(pool, target_nv, n_trials)
solver._seed_nv_targeted_construction = debug_targeted_nv

original_committed = solver._committed_nv_search
def debug_committed(start, pool, target_nv, n_iters=500):
    print(f"[DEBUG] Starting _committed_nv_search: current_nv={start.nv}, target_nv={target_nv}, pool_size={len(pool._routes)}")
    res = original_committed(start, pool, target_nv, n_iters)
    if res is not None:
        print(f"[DEBUG] _committed_nv_search succeeded! Found plan with nv={res.nv}, cost={res.cost:.2f}")
    else:
        print(f"[DEBUG] _committed_nv_search failed to find target nv={target_nv}")
    return res
solver._committed_nv_search = debug_committed

plan, history = solver.solve(seed=42)
print(f"Final Solution: nv={plan.nv}, cost={plan.cost:.2f}, feasible={plan.feasible}")
