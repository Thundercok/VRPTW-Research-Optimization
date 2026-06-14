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
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from vrptw import (
    Config,
    load_datasets,
    run_benchmark,
    print_summary_table,
    ALGO_ALNS_BASE,
    ALGO_HYBRID_FIXED,
    ALGO_HYBRID_RULE,
    ALGO_HYBRID_DDQN,
    ALGO_ORTOOLS,
    ALGO_DQN,
)

# ── REQUIRED: all execution must be inside this guard so that spawn workers
# ── that re-import this script do NOT re-execute the benchmark call.
if __name__ == "__main__":
    import argparse

    base_dir = os.path.dirname(os.path.abspath(__file__))
    default_data = os.path.join(base_dir, "data", "Solomon")
    default_logs = os.path.join(base_dir, "logs")

    parser = argparse.ArgumentParser(
        description="Run VRPTW Solomon benchmark suite.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--data-path", type=str, default=default_data, help="Path to Solomon datasets")
    parser.add_argument("--output-dir", type=str, default=default_logs, help="Directory to save logs/results")
    parser.add_argument("--runs", type=int, default=3, help="Number of runs per algorithm/instance combo")
    parser.add_argument("--alns-iters", type=int, default=5000, help="ALNS iteration limit")
    parser.add_argument("--hybrid-iters", type=int, default=5000, help="Hybrid ALNS/DDQN iteration limit")
    parser.add_argument("--early-stop", type=int, default=250, help="Early stop patience")
    parser.add_argument("--polish-iters", type=int, default=80, help="Polish iterations")
    parser.add_argument("--max-hours", type=float, default=9.5, help="Max wall-clock execution time limit in hours")
    parser.add_argument("--gnn-path", type=str, default=None, help="Path to pre-trained GNN model weights")
    parser.add_argument(
        "--algorithms",
        nargs="+",
        choices=[
            ALGO_ALNS_BASE, ALGO_HYBRID_FIXED, ALGO_HYBRID_RULE, ALGO_HYBRID_DDQN, ALGO_ORTOOLS, ALGO_DQN,
            "GNN-ALNS-Base", "GNN-Hybrid-Fixed", "GNN-Hybrid-Rule", "GNN-Hybrid-DDQN"
        ],
        default=[ALGO_ALNS_BASE, ALGO_HYBRID_FIXED, ALGO_HYBRID_RULE, ALGO_HYBRID_DDQN],
        help="Algorithms to include in benchmark"
    )
    parser.add_argument(
        "--instances",
        nargs="+",
        default=[],
        help="List of specific instance names to run (e.g. RC101 RC201). If empty, runs all available."
    )

    parser.add_argument(
        "--no-checkpoint",
        action="store_true",
        help="Ignore existing checkpoints and start a fresh run."
    )

    args = parser.parse_args()

    gnn_path = args.gnn_path
    if gnn_path is None and any(a.startswith("GNN-") for a in args.algorithms):
        default_gnn = "docs/model/gnn_edge_predictor.pt"
        if os.path.exists(default_gnn):
            gnn_path = default_gnn
            print(f"Auto-configured GNN model path to: {default_gnn}")

    cfg = Config(
        data_path=args.data_path,
        output_dir=args.output_dir,
        n_runs=args.runs,
        alns_iterations=args.alns_iters,
        hybrid_iterations=args.hybrid_iters,
        early_stop_patience=args.early_stop,
        polish_iterations=args.polish_iters,
        max_wall_hours=args.max_hours,
        gnn_model_path=gnn_path,
    )

    # ── Load Solomon instances ─────────────────────────────────────────────
    print(f"Loading datasets from: {cfg.data_path}")
    datasets = load_datasets(cfg.data_path)
    all_insts = []
    counts_str = []
    for g, insts in datasets.items():
        all_insts.extend(insts)
        counts_str.append(f"{g.upper()}: {len(insts)}")
    
    # Filter by user-requested instances if provided
    if args.instances:
        req_lower = {inst.lower() for inst in args.instances}
        all_insts = [inst for inst in all_insts if inst.name.lower() in req_lower]
        print(f"Filtered to {len(all_insts)} requested instances: {[i.name for i in all_insts]}")
    else:
        print("  " + "  |  ".join(counts_str))

    if not all_insts:
        print("ERROR: No matching instances found. Check data-path and instance filters.")
        sys.exit(1)

    os.makedirs(cfg.output_dir, exist_ok=True)

    # ── Run ───────────────────────────────────────────────────────────────
    df = run_benchmark(
        instances=all_insts,
        algorithms=args.algorithms,
        cfg=cfg,
        result_path=os.path.join(cfg.output_dir, "benchmark_clean.csv"),
        checkpoint_path=os.path.join(cfg.output_dir, "benchmark_checkpoint.csv"),
        no_checkpoint=args.no_checkpoint,
    )

    print("\n\n═══ BENCHMARK SUMMARY ═══")
    print_summary_table(df)
    print(f"\nFull results saved to: {os.path.join(cfg.output_dir, 'benchmark_clean.csv')}")
