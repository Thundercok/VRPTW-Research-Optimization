"""
run_benchmark.py — Full Solomon RC1+RC2 benchmark runner.

Usage:
    cd docs
    python3 run_benchmark.py

Resumes automatically from benchmark_checkpoint.csv if interrupted.
Edit the Config block below to change algorithms, iteration counts, etc.
"""
import sys
import os

# Ensure the vrptw package is importable when run from docs/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vrptw import (
    Config,
    load_datasets,
    run_benchmark,
    print_summary_table,
    ALGO_ALNS_BASE,
    ALGO_HYBRID_FIXED,
    ALGO_HYBRID_RULE,
    ALGO_HYBRID_DDQN,
)

# ── REQUIRED: all execution must be inside this guard so that spawn workers
# ── that re-import this script do NOT re-execute the benchmark call.
if __name__ == "__main__":
    # ── Configuration ─────────────────────────────────────────────────────
    cfg = Config(
        data_path   = "./data/Solomon",
        output_dir  = "./logs",
        n_runs      = 3,
        alns_iterations    = 1200,
        hybrid_iterations  = 1200,
        early_stop_patience= 250,
        polish_iterations  = 80,
        max_wall_hours     = 9.5,
    )

    ALGORITHMS = [
        ALGO_ALNS_BASE,
        ALGO_HYBRID_FIXED,
        ALGO_HYBRID_RULE,
        ALGO_HYBRID_DDQN,
    ]

    # ── Load Solomon instances ─────────────────────────────────────────────
    print(f"Loading datasets from: {cfg.data_path}")
    datasets  = load_datasets(cfg.data_path)
    rc1_insts = datasets.get("rc1", [])
    rc2_insts = datasets.get("rc2", [])
    all_insts  = rc1_insts + rc2_insts
    print(f"  RC1: {len(rc1_insts)} instances  |  RC2: {len(rc2_insts)} instances")

    if not all_insts:
        print("ERROR: No instances found. Check data_path in Config.")
        sys.exit(1)

    os.makedirs(cfg.output_dir, exist_ok=True)

    # ── Run ───────────────────────────────────────────────────────────────
    df = run_benchmark(
        instances       = all_insts,
        algorithms      = ALGORITHMS,
        cfg             = cfg,
        result_path     = os.path.join(cfg.output_dir, "benchmark_clean.csv"),
        checkpoint_path = os.path.join(cfg.output_dir, "benchmark_checkpoint.csv"),
    )

    print("\n\n═══ BENCHMARK SUMMARY ═══")
    print_summary_table(df)
    print(f"\nFull results saved to: {os.path.join(cfg.output_dir, 'benchmark_clean.csv')}")
