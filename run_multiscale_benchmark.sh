#!/usr/bin/env bash
set -uo pipefail

OUTPUT_BASE="results/multiscale-publication-suite"
mkdir -p "$OUTPUT_BASE"

echo "=========================================================================="
echo " Starting Multi-Scale Benchmark Suite (Solomon + Homberger)               "
echo " Configuration: 3 Runs | Constant 1000 Iteration Search Budget            "
echo " Running all 10 algorithms side-by-side across all sizes (100 - 1000)      "
echo "=========================================================================="

ALGS="ALNS-Base GNN-ALNS-Base Hybrid-Fixed GNN-Hybrid-Fixed Hybrid-Rule GNN-Hybrid-Rule Hybrid-DDQN GNN-Hybrid-DDQN DQN OR-Tools"
RUNS=3
ITERS=1000
ORTOOLS_LIMIT=120

# ── 1. SOLOMON BENCHMARK (100 Customers) ───────────────────────────────────
echo ""
echo ">>> [RUNNING] Solomon (100 Customers)..."
solomon_insts=("C101" "C201" "R101" "R201" "RC101" "RC201")

PYTHONPATH=src .venv/bin/python -u docs/run_benchmark.py \
  --data-path "data/Solomon" \
  --output-dir "$OUTPUT_BASE/solomon_100" \
  --runs $RUNS \
  --alns-iters $ITERS \
  --hybrid-iters $ITERS \
  --algorithms $ALGS \
  --instances "${solomon_insts[@]}" \
  --ortools-time-limit $ORTOOLS_LIMIT \
  --no-checkpoint

# ── 2. HOMBERGER BENCHMARKS (200 to 1000 Customers) ──────────────────────
for size in 200 400 600 800 1000; do
  idx=$(( size / 100 ))
  echo ""
  echo ">>> [RUNNING] Homberger-$size Customers..."
  
  # Define the 6 representative instances for this size
  insts=(
    "C1_${idx}_1"
    "C2_${idx}_1"
    "R1_${idx}_1"
    "R2_${idx}_1"
    "RC1_${idx}_1"
    "RC2_${idx}_1"
  )
  
  echo "    Instances  : ${insts[*]}"
  echo "    Iterations : $ITERS"
  echo "    Runs       : $RUNS"
  
  PYTHONPATH=src .venv/bin/python -u docs/run_benchmark.py \
    --data-path "data/Gehring_Homberger/homberger_${size}_customer_instances" \
    --output-dir "$OUTPUT_BASE/homberger_$size" \
    --runs $RUNS \
    --alns-iters $ITERS \
    --hybrid-iters $ITERS \
    --algorithms $ALGS \
    --instances "${insts[@]}" \
    --ortools-time-limit $ORTOOLS_LIMIT \
    --no-checkpoint
done

echo "=========================================================================="
echo " Multi-Scale Benchmark Suite Completed!                                   "
echo " Results saved under: $OUTPUT_BASE/                                       "
echo "=========================================================================="

