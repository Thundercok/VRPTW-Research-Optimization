#!/usr/bin/env bash
set -eo pipefail

OUTPUT_BASE="results/ultimate-publication-suite"
mkdir -p "$OUTPUT_BASE"

echo "=========================================================================="
echo " KICH HOAT DOT BENCHMARK SAN XUAT TONG LUC PHUCO VU CONG BO QUOC TE       "
echo " Config: 7 Runs (Solomon) | 5 Runs (H-200) | 3 Runs (H-400/600/800/1000) "
echo " Shards: 8 total | Solomon(3) + Homberger-200/400/600/800/1000(5)         "
echo "=========================================================================="

# Keep machine awake during long overnight runs
if command -v caffeinate &> /dev/null; then
    caffeinate -dism &
    CAFF_PID=$!
    trap 'kill $CAFF_PID 2>/dev/null || true' EXIT
fi

# ─────────────────────────────────────────────────────────────────────────────
# SOLOMON BENCHMARK (56 instances, 7 runs, 5000 iters)
# ─────────────────────────────────────────────────────────────────────────────

# ── SHARD 1: CLUSTERED INSTANCES (C1 & C2) ──────────────────────────────────
echo ""
echo "--> Shard 1: Solomon Clustered (C1/C2) — 17 instances, 7 runs"
PYTHONPATH=src .venv/bin/python docs/run_benchmark.py \
  --data-path data/Solomon \
  --output-dir "$OUTPUT_BASE/solomon_clustered" \
  --runs 7 \
  --alns-iters 5000 \
  --hybrid-iters 5000 \
  --early-stop 1000 \
  --polish-iters 300 \
  --algorithms ALNS-Base Hybrid-Fixed Hybrid-Rule Hybrid-DDQN OR-Tools \
  --instances C101 C102 C103 C104 C105 C106 C107 C108 C109 C201 C202 C203 C204 C205 C206 C207 C208

# ── SHARD 2: RANDOM/MIXED SHORT HORIZON (R1 & RC1) ──────────────────────────
echo ""
echo "--> Shard 2: Solomon Short-Horizon (R1/RC1) — 20 instances, 7 runs"
PYTHONPATH=src .venv/bin/python docs/run_benchmark.py \
  --data-path data/Solomon \
  --output-dir "$OUTPUT_BASE/solomon_short_horizon" \
  --runs 7 \
  --alns-iters 5000 \
  --hybrid-iters 5000 \
  --early-stop 1000 \
  --polish-iters 300 \
  --algorithms ALNS-Base Hybrid-Fixed Hybrid-Rule Hybrid-DDQN OR-Tools \
  --instances R101 R102 R103 R104 R105 R106 R107 R108 R109 R110 R111 R112 RC101 RC102 RC103 RC104 RC105 RC106 RC107 RC108

# ── SHARD 3: RANDOM/MIXED WIDE HORIZON (R2 & RC2) ───────────────────────────
echo ""
echo "--> Shard 3: Solomon Wide-Horizon (R2/RC2) — 20 instances, 7 runs"
PYTHONPATH=src .venv/bin/python docs/run_benchmark.py \
  --data-path data/Solomon \
  --output-dir "$OUTPUT_BASE/solomon_wide_horizon" \
  --runs 7 \
  --alns-iters 5000 \
  --hybrid-iters 5000 \
  --early-stop 1000 \
  --polish-iters 300 \
  --algorithms ALNS-Base Hybrid-Fixed Hybrid-Rule Hybrid-DDQN OR-Tools \
  --instances R201 R202 R203 R204 R205 R206 R207 R208 R209 R210 R211 RC201 RC202 RC203 RC204 RC205 RC206 RC207 RC208

# ─────────────────────────────────────────────────────────────────────────────
# GEHRING & HOMBERGER — 200 CUSTOMERS (ALL 60 INSTANCES, 5 runs, 800 iters)
# ─────────────────────────────────────────────────────────────────────────────

echo ""
echo "--> Shard 4: Homberger-200 (All 60 instances) — 5 runs"
PYTHONPATH=src .venv/bin/python docs/run_benchmark.py \
  --data-path data/Gehring_Homberger/homberger_200_customer_instances \
  --output-dir "$OUTPUT_BASE/gehring_homberger_200" \
  --runs 5 \
  --alns-iters 800 \
  --hybrid-iters 800 \
  --early-stop 200 \
  --polish-iters 60 \
  --algorithms ALNS-Base Hybrid-Fixed Hybrid-Rule Hybrid-DDQN OR-Tools \
  --instances \
    C1_2_1  C1_2_2  C1_2_3  C1_2_4  C1_2_5  C1_2_6  C1_2_7  C1_2_8  C1_2_9  C1_2_10 \
    C2_2_1  C2_2_2  C2_2_3  C2_2_4  C2_2_5  C2_2_6  C2_2_7  C2_2_8  C2_2_9  C2_2_10 \
    R1_2_1  R1_2_2  R1_2_3  R1_2_4  R1_2_5  R1_2_6  R1_2_7  R1_2_8  R1_2_9  R1_2_10 \
    R2_2_1  R2_2_2  R2_2_3  R2_2_4  R2_2_5  R2_2_6  R2_2_7  R2_2_8  R2_2_9  R2_2_10 \
    RC1_2_1 RC1_2_2 RC1_2_3 RC1_2_4 RC1_2_5 RC1_2_6 RC1_2_7 RC1_2_8 RC1_2_9 RC1_2_10 \
    RC2_2_1 RC2_2_2 RC2_2_3 RC2_2_4 RC2_2_5 RC2_2_6 RC2_2_7 RC2_2_8 RC2_2_9 RC2_2_10

# ─────────────────────────────────────────────────────────────────────────────
# GEHRING & HOMBERGER — 400 CUSTOMERS (24 instances, 3 runs, 600 iters)
# Representatives: *_1 through *_4 from each of the 6 problem families
# ─────────────────────────────────────────────────────────────────────────────

echo ""
echo "--> Shard 5: Homberger-400 (24 instances) — 3 runs"
PYTHONPATH=src .venv/bin/python docs/run_benchmark.py \
  --data-path data/Gehring_Homberger/homberger_400_customer_instances \
  --output-dir "$OUTPUT_BASE/gehring_homberger_400" \
  --runs 3 \
  --alns-iters 600 \
  --hybrid-iters 600 \
  --early-stop 150 \
  --polish-iters 50 \
  --algorithms ALNS-Base Hybrid-Fixed Hybrid-Rule Hybrid-DDQN OR-Tools \
  --instances \
    C1_4_1  C1_4_2  C1_4_3  C1_4_4 \
    C2_4_1  C2_4_2  C2_4_3  C2_4_4 \
    R1_4_1  R1_4_2  R1_4_3  R1_4_4 \
    R2_4_1  R2_4_2  R2_4_3  R2_4_4 \
    RC1_4_1 RC1_4_2 RC1_4_3 RC1_4_4 \
    RC2_4_1 RC2_4_2 RC2_4_3 RC2_4_4

# ─────────────────────────────────────────────────────────────────────────────
# GEHRING & HOMBERGER — 600 CUSTOMERS (12 instances, 3 runs, 400 iters)
# Representatives: *_1 and *_2 from each of the 6 problem families
# ─────────────────────────────────────────────────────────────────────────────

echo ""
echo "--> Shard 6: Homberger-600 (12 instances) — 3 runs"
PYTHONPATH=src .venv/bin/python docs/run_benchmark.py \
  --data-path data/Gehring_Homberger/homberger_600_customer_instances \
  --output-dir "$OUTPUT_BASE/gehring_homberger_600" \
  --runs 3 \
  --alns-iters 400 \
  --hybrid-iters 400 \
  --early-stop 100 \
  --polish-iters 35 \
  --algorithms ALNS-Base Hybrid-Fixed Hybrid-Rule Hybrid-DDQN OR-Tools \
  --instances \
    C1_6_1  C1_6_2 \
    C2_6_1  C2_6_2 \
    R1_6_1  R1_6_2 \
    R2_6_1  R2_6_2 \
    RC1_6_1 RC1_6_2 \
    RC2_6_1 RC2_6_2

# ─────────────────────────────────────────────────────────────────────────────
# GEHRING & HOMBERGER — 800 CUSTOMERS (6 instances, 3 runs, 300 iters)
# Representatives: *_1 only from each of the 6 problem families
# ─────────────────────────────────────────────────────────────────────────────

echo ""
echo "--> Shard 7: Homberger-800 (6 instances) — 3 runs"
PYTHONPATH=src .venv/bin/python docs/run_benchmark.py \
  --data-path data/Gehring_Homberger/homberger_800_customer_instances \
  --output-dir "$OUTPUT_BASE/gehring_homberger_800" \
  --runs 3 \
  --alns-iters 300 \
  --hybrid-iters 300 \
  --early-stop 75 \
  --polish-iters 25 \
  --algorithms ALNS-Base Hybrid-Fixed Hybrid-Rule Hybrid-DDQN OR-Tools \
  --instances C1_8_1 C2_8_1 R1_8_1 R2_8_1 RC1_8_1 RC2_8_1

# ─────────────────────────────────────────────────────────────────────────────
# GEHRING & HOMBERGER — 1000 CUSTOMERS STRESS TEST (6 instances, 3 runs, 200 iters)
# Representatives: *_1 only from each of the 6 problem families
# NOTE: Low iter budget — intended as a scalability demonstration.
# ─────────────────────────────────────────────────────────────────────────────

echo ""
echo "--> Shard 8: Homberger-1000 STRESS (6 instances) — 3 runs"
PYTHONPATH=src .venv/bin/python docs/run_benchmark.py \
  --data-path data/Gehring_Homberger/homberger_1000_customer_instances \
  --output-dir "$OUTPUT_BASE/gehring_homberger_1000" \
  --runs 3 \
  --alns-iters 200 \
  --hybrid-iters 200 \
  --early-stop 50 \
  --polish-iters 20 \
  --algorithms ALNS-Base Hybrid-Fixed Hybrid-Rule Hybrid-DDQN OR-Tools \
  --instances C1_10_1 C2_10_1 R1_10_1 R2_10_1 RC1_10_1 RC2_10_1

echo ""
echo "=========================================================================="
echo " TOAN BO SUITE BENCHMARK DA HOAN THANH XUAT SAC                           "
echo " Coverage: 56 Solomon + 60 H-200 + 24 H-400 + 12 H-600 + 6 H-800 + 6 H-1000"
echo " Total   : 164 instances across 8 shards                                  "
echo "=========================================================================="
