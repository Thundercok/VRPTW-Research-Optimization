#!/usr/bin/env bash
# V2 re-run sweeps, two protocols (see plan.md):
#   S5  iteration-bounded (--no-time-limit)  -> results/rerun_iters/   Solomon + H200 + H400
#   S6  time-bounded (anytime default)       -> results/rerun_time/    H600 + H800 + H1000
# Per-shard parameters mirror run_full_production.sh. Continues past a failed
# shard (checkpoints make re-runs cheap); per-shard logs live next to results.
set -uo pipefail

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONUNBUFFERED=1
# Windows console codepage (cp1258) cannot encode the checkpoint banner's "✓";
# with output redirected to a log the first checkpoint print killed the shard.
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1

PYTHON="${PYTHON:-/c/Users/han/AppData/Local/Programs/Python/Python311/python.exe}"
REPO="${REPO:-/c/D/Github/VRPTW-Research-Optimization}"
cd "$REPO" || exit 1

ITERS_BASE="results/rerun_iters"
TIME_BASE="results/rerun_time"
mkdir -p "$ITERS_BASE" "$TIME_BASE"

ALGOS=(ALNS-Base ALNS-Base+ Hybrid-Fixed Hybrid-Rule Hybrid-DDQN OR-Tools)
FAILED=0

run_shard() {
    local name="$1" logdir="$2"; shift 2
    local t0=$SECONDS
    echo "SHARD-START $name $(date +%H:%M:%S)"
    if "$PYTHON" docs/run_benchmark.py "$@" > "$logdir/shard.log" 2>&1; then
        echo "SHARD-OK $name $(( (SECONDS - t0) / 60 ))min"
    else
        echo "SHARD-FAILED $name exit=$? $(( (SECONDS - t0) / 60 ))min"
        FAILED=1
    fi
}

# ── S5: iteration-bounded ────────────────────────────────────────────────────
d="$ITERS_BASE/solomon_clustered"; mkdir -p "$d"
run_shard solomon_clustered "$d" \
  --data-path data/Solomon --output-dir "$d" --runs 7 \
  --alns-iters 5000 --hybrid-iters 5000 --early-stop 1000 --polish-iters 300 \
  --ortools-time-limit 120 --no-time-limit --algorithms "${ALGOS[@]}" \
  --instances C101 C102 C103 C104 C105 C106 C107 C108 C109 C201 C202 C203 C204 C205 C206 C207 C208

d="$ITERS_BASE/solomon_short_horizon"; mkdir -p "$d"
run_shard solomon_short_horizon "$d" \
  --data-path data/Solomon --output-dir "$d" --runs 7 \
  --alns-iters 5000 --hybrid-iters 5000 --early-stop 1000 --polish-iters 300 \
  --ortools-time-limit 120 --no-time-limit --algorithms "${ALGOS[@]}" \
  --instances R101 R102 R103 R104 R105 R106 R107 R108 R109 R110 R111 R112 RC101 RC102 RC103 RC104 RC105 RC106 RC107 RC108

d="$ITERS_BASE/solomon_wide_horizon"; mkdir -p "$d"
# Fuse 1200s: ~2.6x the healthy wide-TW run (~450s), so all 5000 iterations
# complete well before it fires; it only caps a runaway (e.g. an overnight
# machine-sleep, which polluted R211 on the first attempt and cascaded into a
# 3h OR-Tools iso-time budget). 18/19 instances here already ran unbounded;
# only R211 is being redone under the fuse for clean timing.
run_shard solomon_wide_horizon "$d" \
  --data-path data/Solomon --output-dir "$d" --runs 7 \
  --alns-iters 5000 --hybrid-iters 5000 --early-stop 1000 --polish-iters 300 \
  --ortools-time-limit 120 --time-limit 1200 --algorithms "${ALGOS[@]}" \
  --instances R201 R202 R203 R204 R205 R206 R207 R208 R209 R210 R211 RC201 RC202 RC203 RC204 RC205 RC206 RC207 RC208

d="$ITERS_BASE/gehring_homberger_200"; mkdir -p "$d"
run_shard gehring_homberger_200 "$d" \
  --data-path data/Gehring_Homberger/homberger_200_customer_instances \
  --output-dir "$d" --runs 5 \
  --alns-iters 800 --hybrid-iters 800 --early-stop 200 --polish-iters 60 \
  --ortools-time-limit 120 --max-hours 48.0 --time-limit 1500 --algorithms "${ALGOS[@]}" \
  --instances \
    C1_2_1 C1_2_2 C1_2_3 C1_2_4 C1_2_5 C1_2_6 C1_2_7 C1_2_8 C1_2_9 C1_2_10 \
    C2_2_1 C2_2_2 C2_2_3 C2_2_4 C2_2_5 C2_2_6 C2_2_7 C2_2_8 C2_2_9 C2_2_10 \
    R1_2_1 R1_2_2 R1_2_3 R1_2_4 R1_2_5 R1_2_6 R1_2_7 R1_2_8 R1_2_9 R1_2_10 \
    R2_2_1 R2_2_2 R2_2_3 R2_2_4 R2_2_5 R2_2_6 R2_2_7 R2_2_8 R2_2_9 R2_2_10 \
    RC1_2_1 RC1_2_2 RC1_2_3 RC1_2_4 RC1_2_5 RC1_2_6 RC1_2_7 RC1_2_8 RC1_2_9 RC1_2_10 \
    RC2_2_1 RC2_2_2 RC2_2_3 RC2_2_4 RC2_2_5 RC2_2_6 RC2_2_7 RC2_2_8 RC2_2_9 RC2_2_10

d="$ITERS_BASE/gehring_homberger_400"; mkdir -p "$d"
run_shard gehring_homberger_400 "$d" \
  --data-path data/Gehring_Homberger/homberger_400_customer_instances \
  --output-dir "$d" --runs 3 \
  --alns-iters 600 --hybrid-iters 600 --early-stop 150 --polish-iters 50 \
  --ortools-time-limit 120 --max-hours 48.0 --time-limit 3600 --algorithms "${ALGOS[@]}" \
  --instances \
    C1_4_1 C1_4_2 C1_4_3 C1_4_4 C2_4_1 C2_4_2 C2_4_3 C2_4_4 \
    R1_4_1 R1_4_2 R1_4_3 R1_4_4 R2_4_1 R2_4_2 R2_4_3 R2_4_4 \
    RC1_4_1 RC1_4_2 RC1_4_3 RC1_4_4 RC2_4_1 RC2_4_2 RC2_4_3 RC2_4_4

echo "S5-DONE $(date +%H:%M:%S)"

# ── S6: time-bounded (anytime default 0.6 s/customer) ────────────────────────
d="$TIME_BASE/gehring_homberger_600"; mkdir -p "$d"
run_shard gehring_homberger_600 "$d" \
  --data-path data/Gehring_Homberger/homberger_600_customer_instances \
  --output-dir "$d" --runs 3 \
  --alns-iters 400 --hybrid-iters 400 --early-stop 100 --polish-iters 35 \
  --ortools-time-limit 120 --max-hours 48.0 --algorithms "${ALGOS[@]}" \
  --instances C1_6_1 C1_6_2 C2_6_1 C2_6_2 R1_6_1 R1_6_2 R2_6_1 R2_6_2 RC1_6_1 RC1_6_2 RC2_6_1 RC2_6_2

d="$TIME_BASE/gehring_homberger_800"; mkdir -p "$d"
run_shard gehring_homberger_800 "$d" \
  --data-path data/Gehring_Homberger/homberger_800_customer_instances \
  --output-dir "$d" --runs 3 \
  --alns-iters 300 --hybrid-iters 300 --early-stop 75 --polish-iters 25 \
  --ortools-time-limit 120 --max-hours 48.0 --algorithms "${ALGOS[@]}" \
  --instances C1_8_1 C2_8_1 R1_8_1 R2_8_1 RC1_8_1 RC2_8_1

d="$TIME_BASE/gehring_homberger_1000"; mkdir -p "$d"
run_shard gehring_homberger_1000 "$d" \
  --data-path data/Gehring_Homberger/homberger_1000_customer_instances \
  --output-dir "$d" --runs 3 \
  --alns-iters 200 --hybrid-iters 200 --early-stop 50 --polish-iters 20 \
  --ortools-time-limit 120 --max-hours 48.0 --algorithms "${ALGOS[@]}" \
  --instances C1_10_1 C2_10_1 R1_10_1 R2_10_1 RC1_10_1 RC2_10_1

echo "S6-DONE $(date +%H:%M:%S)"
echo "ALL-SWEEPS-DONE failed_any=$FAILED"
exit $FAILED
