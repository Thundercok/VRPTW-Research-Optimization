#!/bin/bash
set -e

# Make sure we are in the correct repository root directory
cd "$(dirname "$0")/.."

echo "=========================================================================="
echo "Starting overnight Solomon benchmark sweep (56 instances)..."
echo "=========================================================================="
PYTHONPATH=src python3 docs/run_benchmark.py \
  --data-path data/Solomon \
  --output-dir results/overnight_run/solomon \
  --runs 2 \
  --alns-iters 600 \
  --hybrid-iters 600 \
  --early-stop 120 \
  --polish-iters 40 \
  --algorithms ALNS-Base Hybrid-Fixed Hybrid-Rule Hybrid-DDQN OR-Tools

echo "=========================================================================="
echo "Starting overnight Gehring & Homberger 200 benchmark sweep (6 instances)..."
echo "=========================================================================="
PYTHONPATH=src python3 docs/run_benchmark.py \
  --data-path data/Gehring_Homberger/homberger_200_customer_instances \
  --output-dir results/overnight_run/homberger200 \
  --runs 2 \
  --alns-iters 600 \
  --hybrid-iters 600 \
  --early-stop 120 \
  --polish-iters 40 \
  --instances C1_2_1 C2_2_1 R1_2_1 R2_2_1 RC1_2_1 RC2_2_1 \
  --algorithms ALNS-Base Hybrid-Fixed Hybrid-Rule Hybrid-DDQN OR-Tools

echo "=========================================================================="
echo "Overnight benchmark runs completed successfully!"
echo "=========================================================================="
