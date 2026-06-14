#!/usr/bin/env bash
set -uo pipefail

OUTPUT_BASE="results/multiscale-publication-suite"
mkdir -p "$OUTPUT_BASE"

echo "=========================================================================="
echo " Starting Multi-Scale Benchmark Suite (Solomon + Homberger)               "
echo " Running all 10 algorithms side-by-side across all sizes (100 - 1000)      "
echo "=========================================================================="

ALGS="ALNS-Base GNN-ALNS-Base Hybrid-Fixed GNN-Hybrid-Fixed Hybrid-Rule GNN-Hybrid-Rule Hybrid-DDQN GNN-Hybrid-DDQN DQN OR-Tools"

# ── 1. SOLOMON BENCHMARK (100 Customers) ───────────────────────────────────
echo ""
echo ">>> [RUNNING] Solomon (100 Customers)..."
solomon_insts=("C101" "C201" "R101" "R201" "RC101" "RC201")
solomon_iters=1000

PYTHONPATH=src .venv/bin/python docs/run_benchmark.py \
  --data-path "data/Solomon" \
  --output-dir "$OUTPUT_BASE/solomon_100" \
  --runs 1 \
  --alns-iters "$solomon_iters" \
  --hybrid-iters "$solomon_iters" \
  --algorithms $ALGS \
  --instances "${solomon_insts[@]}" \
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
  
  # Configure budget based on customer size
  if [ "$size" -le 200 ]; then
    iters=800
  elif [ "$size" -le 600 ]; then
    iters=400
  else
    iters=200
  fi
  
  echo "    Instances  : ${insts[*]}"
  echo "    Iterations : $iters"
  
  PYTHONPATH=src .venv/bin/python docs/run_benchmark.py \
    --data-path "data/Gehring_Homberger/homberger_${size}_customer_instances" \
    --output-dir "$OUTPUT_BASE/homberger_$size" \
    --runs 1 \
    --alns-iters "$iters" \
    --hybrid-iters "$iters" \
    --algorithms $ALGS \
    --instances "${insts[@]}" \
    --no-checkpoint
done

echo "=========================================================================="
echo " Multi-Scale Benchmark Suite Completed!                                   "
echo " Results saved under: $OUTPUT_BASE/                                       "
echo "=========================================================================="
