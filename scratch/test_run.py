import sys
import os

sys.path.insert(0, "src")

from vrptw import Config, load_datasets, HybridDDQNSolver

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

cfg = Config(
    alns_iterations=100,
    hybrid_iterations=100,
    early_stop_patience=50,
    polish_iterations=20,
    n_runs=1,
)

solver = HybridDDQNSolver(inst, cfg)
plan, history = solver.solve(seed=42)
print(f"Result: nv={plan.nv}, cost={plan.cost:.2f}, feasible={plan.feasible}")
