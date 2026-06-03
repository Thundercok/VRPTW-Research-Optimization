print("1: script started")
import sys
sys.path.insert(0, "src")
print("2: path inserted")
import vrptw
print("3: vrptw imported")
from vrptw import Config, load_datasets
print("4: names imported")
datasets = load_datasets("data/Solomon")
print("5: datasets loaded")
inst = None
for g, insts in datasets.items():
    for i in insts:
        if i.name == "RC101":
            inst = i
            break
print(f"6: instance: {inst.name if inst else 'None'}")
cfg = Config(alns_iterations=5, hybrid_iterations=5, early_stop_patience=5, polish_iterations=5, n_runs=1)
print("7: config created")
from vrptw import HybridDDQNSolver
print("8: solver imported")
solver = HybridDDQNSolver(inst, cfg)
print("9: solver initialized")
plan, history = solver.solve(seed=42)
print(f"10: plan solved: nv={plan.nv}, cost={plan.cost:.2f}, feasible={plan.feasible}")
