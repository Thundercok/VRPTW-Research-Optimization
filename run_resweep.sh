#!/usr/bin/env bash
set -eo pipefail

export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONUNBUFFERED=1

OUTPUT_BASE="results/clean_v5"
mkdir -p "$OUTPUT_BASE"

# Max workers: default 6, can be overridden by environment variable
MAX_WORKERS=${MAX_WORKERS:-6}
MAX_HOURS=${MAX_HOURS:-48.0}  # Increased to 48.0 hours for comprehensive runs

# Helper function to print status of all sweep shards
print_status() {
  .venv/bin/python3 -c "
import os
import pandas as pd

shards = {
    'solomon_c': ('$OUTPUT_BASE/solomon_clustered', 17),
    'solomon_r1_rc1': ('$OUTPUT_BASE/solomon_short_horizon', 20),
    'solomon_r2_rc2': ('$OUTPUT_BASE/solomon_wide_horizon', 19),
    'h200_c1': ('$OUTPUT_BASE/gehring_homberger_200/c1', 10),
    'h200_c2': ('$OUTPUT_BASE/gehring_homberger_200/c2', 10),
    'h200_r1': ('$OUTPUT_BASE/gehring_homberger_200/r1', 10),
    'h200_r2': ('$OUTPUT_BASE/gehring_homberger_200/r2', 10),
    'h200_rc1': ('$OUTPUT_BASE/gehring_homberger_200/rc1', 10),
    'h200_rc2': ('$OUTPUT_BASE/gehring_homberger_200/rc2', 10),
    'h400': ('$OUTPUT_BASE/gehring_homberger_400', 24),
    'h600': ('$OUTPUT_BASE/gehring_homberger_600', 12),
    'h800': ('$OUTPUT_BASE/gehring_homberger_800', 6),
    'h1000': ('$OUTPUT_BASE/gehring_homberger_1000', 6),
}

print('=== BENCHMARK SWEEP STATUS ===')
suggested = None
for key, (path, total) in shards.items():
    clean = os.path.join(path, 'benchmark_clean.csv')
    ckpt = os.path.join(path, 'benchmark_checkpoint.csv')
    if os.path.exists(clean):
        status = 'COMPLETED'
    elif os.path.exists(ckpt):
        try:
            df = pd.read_csv(ckpt)
            done = df['Instance'].nunique()
            status = f'PARTIAL ({done}/{total} instances)'
            if suggested is None:
                suggested = key
        except Exception:
            status = 'PARTIAL'
            if suggested is None:
                suggested = key
    else:
        status = 'NOT STARTED'
        if suggested is None:
            suggested = key
    print(f'  {key:<16} : {status}')
print('==============================')
if suggested:
    print(f'Suggested next step: ./run_resweep.sh {suggested}\n')
else:
    print('All shards completed successfully!\n')
"
}

# Helper function to run a benchmark shard with native checkpoint resume
run_shard() {
  local shard_name="$1"
  local data_path="$2"
  local output_dir="$3"
  local runs="$4"
  local alns_iters="$5"
  local hybrid_iters="$6"
  local early_stop="$7"
  local polish_iters="$8"
  local instances="$9"
  
  echo "=========================================================================="
  echo " RUNNING SHARD: $shard_name"
  echo " Output: $output_dir"
  echo " Checkpoint Resume: ENABLED"
  echo "=========================================================================="
  
  PYTHONPATH=src .venv/bin/python -u docs/run_benchmark.py \
    --data-path "$data_path" \
    --output-dir "$output_dir" \
    --runs "$runs" \
    --alns-iters "$alns_iters" \
    --hybrid-iters "$hybrid_iters" \
    --early-stop "$early_stop" \
    --polish-iters "$polish_iters" \
    --max-workers "$MAX_WORKERS" \
    --max-hours "$MAX_HOURS" \
    --algorithms ALNS-Base Hybrid-DDQN OR-Tools \
    --instances $instances
}

# Command dispatcher
case "$1" in
  status)
    print_status
    ;;
  solomon_c)
    run_shard "Solomon Clustered (C1/C2)" "data/Solomon" "$OUTPUT_BASE/solomon_clustered" \
      7 5000 5000 1000 300 \
      "C101 C102 C103 C104 C105 C106 C107 C108 C109 C201 C202 C203 C204 C205 C206 C207 C208"
    ;;
  solomon_r1_rc1)
    run_shard "Solomon Short-Horizon (R1/RC1)" "data/Solomon" "$OUTPUT_BASE/solomon_short_horizon" \
      7 5000 5000 1000 300 \
      "R101 R102 R103 R104 R105 R106 R107 R108 R109 R110 R111 R112 RC101 RC102 RC103 RC104 RC105 RC106 RC107 RC108"
    ;;
  solomon_r2_rc2)
    run_shard "Solomon Wide-Horizon (R2/RC2)" "data/Solomon" "$OUTPUT_BASE/solomon_wide_horizon" \
      7 5000 5000 1000 300 \
      "R201 R202 R203 R204 R205 R206 R207 R208 R209 R210 R211 RC201 RC202 RC203 RC204 RC205 RC206 RC207 RC208"
    ;;
  h200_c1)
    run_shard "Homberger-200 C1" "data/Gehring_Homberger/homberger_200_customer_instances" "$OUTPUT_BASE/gehring_homberger_200/c1" \
      5 800 800 200 60 \
      "C1_2_1 C1_2_2 C1_2_3 C1_2_4 C1_2_5 C1_2_6 C1_2_7 C1_2_8 C1_2_9 C1_2_10"
    ;;
  h200_c2)
    run_shard "Homberger-200 C2" "data/Gehring_Homberger/homberger_200_customer_instances" "$OUTPUT_BASE/gehring_homberger_200/c2" \
      5 800 800 200 60 \
      "C2_2_1 C2_2_2 C2_2_3 C2_2_4 C2_2_5 C2_2_6 C2_2_7 C2_2_8 C2_2_9 C2_2_10"
    ;;
  h200_r1)
    run_shard "Homberger-200 R1" "data/Gehring_Homberger/homberger_200_customer_instances" "$OUTPUT_BASE/gehring_homberger_200/r1" \
      5 800 800 200 60 \
      "R1_2_1 R1_2_2 R1_2_3 R1_2_4 R1_2_5 R1_2_6 R1_2_7 R1_2_8 R1_2_9 R1_2_10"
    ;;
  h200_r2)
    run_shard "Homberger-200 R2" "data/Gehring_Homberger/homberger_200_customer_instances" "$OUTPUT_BASE/gehring_homberger_200/r2" \
      5 800 800 200 60 \
      "R2_2_1 R2_2_2 R2_2_3 R2_2_4 R2_2_5 R2_2_6 R2_2_7 R2_2_8 R2_2_9 R2_2_10"
    ;;
  h200_rc1)
    run_shard "Homberger-200 RC1" "data/Gehring_Homberger/homberger_200_customer_instances" "$OUTPUT_BASE/gehring_homberger_200/rc1" \
      5 800 800 200 60 \
      "RC1_2_1 RC1_2_2 RC1_2_3 RC1_2_4 RC1_2_5 RC1_2_6 RC1_2_7 RC1_2_8 RC1_2_9 RC1_2_10"
    ;;
  h200_rc2)
    run_shard "Homberger-200 RC2" "data/Gehring_Homberger/homberger_200_customer_instances" "$OUTPUT_BASE/gehring_homberger_200/rc2" \
      5 800 800 200 60 \
      "RC2_2_1 RC2_2_2 RC2_2_3 RC2_2_4 RC2_2_5 RC2_2_6 RC2_2_7 RC2_2_8 RC2_2_9 RC2_2_10"
    ;;
  h400)
    run_shard "Homberger-400" "data/Gehring_Homberger/homberger_400_customer_instances" "$OUTPUT_BASE/gehring_homberger_400" \
      3 600 600 150 50 \
      "C1_4_1 C1_4_2 C1_4_3 C1_4_4 C2_4_1 C2_4_2 C2_4_3 C2_4_4 R1_4_1 R1_4_2 R1_4_3 R1_4_4 R2_4_1 R2_4_2 R2_4_3 R2_4_4 RC1_4_1 RC1_4_2 RC1_4_3 RC1_4_4 RC2_4_1 RC2_4_2 RC2_4_3 RC2_4_4"
    ;;
  h600)
    run_shard "Homberger-600" "data/Gehring_Homberger/homberger_600_customer_instances" "$OUTPUT_BASE/gehring_homberger_600" \
      3 400 400 100 35 \
      "C1_6_1 C1_6_2 C2_6_1 C2_6_2 R1_6_1 R1_6_2 R2_6_1 R2_6_2 RC1_6_1 RC1_6_2 RC2_6_1 RC2_6_2"
    ;;
  h800)
    run_shard "Homberger-800" "data/Gehring_Homberger/homberger_800_customer_instances" "$OUTPUT_BASE/gehring_homberger_800" \
      3 300 300 75 25 \
      "C1_8_1 C2_8_1 R1_8_1 R2_8_1 RC1_8_1 RC2_8_1"
    ;;
  h1000)
    run_shard "Homberger-1000" "data/Gehring_Homberger/homberger_1000_customer_instances" "$OUTPUT_BASE/gehring_homberger_1000" \
      3 200 200 50 20 \
      "C1_10_1 C2_10_1 R1_10_1 R2_10_1 RC1_10_1 RC2_10_1"
    ;;
  all)
    $0 solomon_c
    $0 solomon_r1_rc1
    $0 solomon_r2_rc2
    $0 h200_c1
    $0 h200_c2
    $0 h200_r1
    $0 h200_r2
    $0 h200_rc1
    $0 h200_rc2
    $0 h400
    $0 h600
    $0 h800
    $0 h1000
    ;;
  *)
    echo "Usage: $0 {status|solomon_c|solomon_r1_rc1|solomon_r2_rc2|h200_c1|h200_c2|h200_r1|h200_r2|h200_rc1|h200_rc2|h400|h600|h800|h1000|all}"
    exit 1
    ;;
esac
