"""Proper RC202 test with standard benchmark budget."""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from vrptw import Config, load_datasets, HybridDDQNSolver

cfg = Config(
    data_path="data/Solomon",
    output_dir="/tmp/rc202_proper",
    hybrid_iterations=2000,
    early_stop_patience=500,
    polish_iterations=80,
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
for seed in range(10):
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
# Only count NV=3 results for fair comparison
nv3_results = [(nv, td, gap, t) for nv, td, gap, t in results if nv == 3]
print(f"\n=== RC202 Summary (10 seeds, all) ===")
print(f"  NV:  {np.mean(nv_arr):.2f} ± {np.std(nv_arr):.2f}")
print(f"  TD:  {np.mean(td_arr):.2f} ± {np.std(td_arr):.2f}")
print(f"  Gap: {np.mean(gap_arr):+.2f}%")
print(f"  NV distribution: {sorted(nv_arr)}")
if nv3_results:
    print(f"\n=== RC202 Summary (NV=3 only, {len(nv3_results)}/{len(results)} seeds) ===")
    td3 = [r[1] for r in nv3_results]
    gap3 = [r[2] for r in nv3_results]
    print(f"  TD:  {np.mean(td3):.2f} ± {np.std(td3):.2f}")
    print(f"  Gap: {np.mean(gap3):+.2f}%")
print(f"\n  (Previous clean_v3: NV=3.0, TD=1440.41, Gap=+24.26%)")
