import sys
sys.path.insert(0, "src")
import time
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
    alns_iterations=400,
    hybrid_iterations=400,
    early_stop_patience=150,
    polish_iterations=50,
    n_runs=1,
)

for seed in (42, 43, 44):
    print(f"\n--- Running Seed {seed} ---")
    solver = HybridDDQNSolver(inst, cfg)
    
    t0 = time.time()
    plan, history = solver.solve(seed=seed)
    elapsed = time.time() - t0
    
    print(f"Finished in {elapsed:.1f}s")
    print(f"History start cost: {history[0]:.2f}")
    print(f"History end cost: {history[-1]:.2f}")
    print(f"Final Plan NV: {plan.nv}, Cost: {plan.cost:.2f}")
    
    assert history[-1] <= history[0], f"Cost regressed: seed={seed} (start={history[0]:.2f}, end={history[-1]:.2f})"
    print(f"seed={seed}: NV={plan.nv}, cost={plan.cost:.2f}")
