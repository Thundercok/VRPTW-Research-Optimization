import sys
sys.path.insert(0, "src")
from vrptw import Config, load_datasets, HybridDDQNSolver

datasets = load_datasets("data/Solomon")
inst = None
for g, insts in datasets.items():
    for i in insts:
        if i.name == "RC101":
            inst = i
            break
if not inst:
    print("RC101 not found")
    sys.exit(1)

cfg = Config(
    alns_iterations=2,
    hybrid_iterations=2,
    early_stop_patience=2,
    polish_iterations=2,
    n_runs=1,
)
solver = HybridDDQNSolver(inst, cfg)
plan, history = solver.solve(seed=42)
print(f"Success! Final NV: {plan.nv}, cost: {plan.cost:.2f}, feasible: {plan.feasible}")
