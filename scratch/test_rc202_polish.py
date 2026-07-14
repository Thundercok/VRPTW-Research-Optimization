"""Quick smoke test: run Hybrid-DDQN on RC202 with the upgraded TD polish cascade."""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from vrptw import Config, load_datasets, HybridDDQNSolver

cfg = Config(
    data_path="data/Solomon",
    output_dir="/tmp/rc202_test",
    hybrid_iterations=600,
    early_stop_patience=150,
    polish_iterations=50,
)

datasets = load_datasets(cfg.data_path)
rc202 = None
for group, insts in datasets.items():
    for inst in insts:
        if inst.name == "RC202":
            rc202 = inst
            break

if rc202 is None:
    print("RC202 not found!")
    sys.exit(1)

print(f"Running Hybrid-DDQN on RC202 (BKS: NV=3, TD=1159.21)...")
print(f"Config: {cfg.hybrid_iterations} iters, early_stop={cfg.early_stop_patience}")

results = []
for seed in [42, 123, 456]:
    t0 = time.time()
    solver = HybridDDQNSolver(rc202, cfg)
    plan, history = solver.solve(seed=seed)
    elapsed = time.time() - t0
    gap_td, _ = plan.gap()
    results.append((plan.nv, plan.cost, gap_td, elapsed))
    print(f"  seed={seed}: NV={plan.nv}, TD={plan.cost:.2f}, Gap={gap_td:+.2f}%, time={elapsed:.1f}s")

import numpy as np
nv_arr = [r[0] for r in results]
td_arr = [r[1] for r in results]
gap_arr = [r[2] for r in results]
print(f"\n=== RC202 Summary (3 seeds) ===")
print(f"  NV:  {np.mean(nv_arr):.2f} ± {np.std(nv_arr):.2f}")
print(f"  TD:  {np.mean(td_arr):.2f} ± {np.std(td_arr):.2f}")
print(f"  Gap: {np.mean(gap_arr):+.2f}%")
print(f"  (Previous clean_v3: NV=3.0, TD=1440.41, Gap=+24.26%)")
