import sys
import os
import time

# Ensure src/ is importable
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import vrptw
from vrptw import Config, load_datasets, HybridDDQNSolver

def run_test(instance_name: str, iters: int = 150):
    # Load dataset
    datasets = load_datasets(os.path.join(ROOT, "data", "Solomon"))
    # Find the instance
    target_inst = None
    for g, insts in datasets.items():
        for inst in insts:
            if inst.name.lower() == instance_name.lower():
                target_inst = inst
                break
    if target_inst is None:
        raise ValueError(f"Could not find instance {instance_name}")

    cfg = Config(
        hybrid_iterations=iters,
        early_stop_patience=50,
        polish_iterations=20,
        n_runs=1,
    )

    print(f"\n=======================================================")
    print(f"DIAGNOSTIC TEST: {target_inst.name} ({iters} iterations)")
    print(f"=======================================================")

    # 1. RUN WITH BKS FLOOR GUARD (Standard Solver)
    t0 = time.time()
    solver_with_bks = HybridDDQNSolver(target_inst, cfg)
    plan_with, _ = solver_with_bks.solve(seed=42)
    time_with = time.time() - t0
    print(f"WITH BKS Floor Guard:   NV={plan_with.nv}  TD={plan_with.cost:.2f}  Time={time_with:.1f}s")

    # 2. RUN WITHOUT BKS FLOOR GUARD (Mock BKS database to be empty)
    # This represents zero BKS guidance (no data leakage)
    import vrptw.config
    original_bks = dict(vrptw.config.BKS)
    vrptw.config.BKS = {}  # Empty BKS mapping

    t0 = time.time()
    solver_no_bks = HybridDDQNSolver(target_inst, cfg)
    plan_no, _ = solver_no_bks.solve(seed=42)
    time_no = time.time() - t0
    print(f"WITHOUT BKS Floor Guard (No Leakage): NV={plan_no.nv}  TD={plan_no.cost:.2f}  Time={time_no:.1f}s")

    # Restore BKS
    vrptw.config.BKS = original_bks

    # Analyze
    nv_diff = plan_no.nv - plan_with.nv
    td_diff_pct = (plan_no.cost - plan_with.cost) / plan_with.cost * 100
    speedup = time_no / time_with if time_with > 0 else 1.0

    print(f"\nAnalysis:")
    print(f"  Vehicle Count (NV) difference: {nv_diff:+.0f} vehicles")
    print(f"  Total Distance (TD) difference: {td_diff_pct:+.2f}%")
    print(f"  Floor Guard Speedup Factor:     {speedup:.2f}x")

if __name__ == "__main__":
    # Run a quick check on RC207 (our key wide-TW diagnostic instance)
    run_test("RC207", iters=100)
    # Run a quick check on C103 (clustered instance)
    run_test("C103", iters=100)
