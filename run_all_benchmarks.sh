#!/usr/bin/env bash
set -uo pipefail

OUTPUT_BASE="results/ultimate-publication-suite"
LOG_DIR="$OUTPUT_BASE/runtime_logs"
mkdir -p "$OUTPUT_BASE" "$LOG_DIR"

echo "=========================================================================="
echo " KICH HOAT DOT BENCHMARK SAN XUAT TONG LUC PHUCO VU CONG BO QUOC TE       "
echo " Configuration: 5 Runs | 5000 Main Iters | 1000 Patience | 300 Polish    "
echo " Safety Mode: Fault-Tolerant Loop Enabled                                 "
echo "=========================================================================="

if command -v caffeinate &> /dev/null; then
    caffeinate -dism &
    CAFF_PID=$!
    trap 'kill $CAFF_PID 2>/dev/null || true' EXIT
fi

ALGS="ALNS-Base Hybrid-Fixed Hybrid-Rule Hybrid-DDQN OR-Tools"

execute_benchmark_safe() {
    local shard_name="$1"
    local data_path="$2"
    local output_dir="$3"
    local alns_iters="$4"
    local hybrid_iters="$5"
    local early_stop="$6"
    local polish_iters="$7"
    shift 7
    local instances=("$@")

    local shard_log_name="${shard_name// /_}"
    shard_log_name="${shard_log_name//[\/()]/_}"

    echo "--> Running Shard: $shard_name (${#instances[@]} instances in parallel)"
    
    if PYTHONPATH=src .venv/bin/python -u docs/run_benchmark.py \
        --data-path "$data_path" \
        --output-dir "$output_dir" \
        --runs 5 \
        --alns-iters "$alns_iters" \
        --hybrid-iters "$hybrid_iters" \
        --early-stop "$early_stop" \
        --polish-iters "$polish_iters" \
        --algorithms $ALGS \
        --instances "${instances[@]}" 2>&1 < /dev/null | tee "$LOG_DIR/shard_${shard_log_name}.log"; then
        
        echo "--> [SUCCESS] Shard $shard_name completed."
    else
        echo "--> [!!! CRITICAL ERROR !!!] Shard $shard_name execution failed. Check log at: $LOG_DIR/shard_${shard_log_name}.log" >&2
    fi
}

# ── SHARD 1: CLUSTERED INSTANCES (C1 & C2) ──
C1_C2_INSTANCES=(C101 C102 C103 C104 C105 C106 C107 C108 C109 C201 C202 C203 C204 C205 C206 C207 C208)
execute_benchmark_safe "Clustered (C1/C2)" "data/Solomon" "$OUTPUT_BASE/solomon_clustered" 5000 5000 1000 300 "${C1_C2_INSTANCES[@]}"

# ── SHARD 2: RANDOM/MIXED SHORT HORIZON (R1 & RC1) ──
R1_RC1_INSTANCES=(R101 R102 R103 R104 R105 R106 R107 R108 R109 R110 R111 R112 RC101 RC102 RC103 RC104 RC105 RC106 RC107 RC108)
execute_benchmark_safe "Short-Horizon (R1/RC1)" "data/Solomon" "$OUTPUT_BASE/solomon_short_horizon" 5000 5000 1000 300 "${R1_RC1_INSTANCES[@]}"

# ── SHARD 3: RANDOM/MIXED WIDE HORIZON (R2 & RC2) ──
R2_RC2_INSTANCES=(R201 R202 R203 R204 R205 R206 R207 R208 R209 R210 R211 RC201 RC202 RC203 RC204 RC205 RC206 RC207 RC208)
execute_benchmark_safe "Wide-Horizon (R2/RC2)" "data/Solomon" "$OUTPUT_BASE/solomon_wide_horizon" 5000 5000 1000 300 "${R2_RC2_INSTANCES[@]}"

# ── SHARD 4: GEHRING & HOMBERGER (200 CUSTOMERS) ──
HOMBERGER_200=(C1_2_1 C2_2_1 R1_2_1 R2_2_1 RC1_2_1 RC2_2_1)
execute_benchmark_safe "Homberger-200" "data/Gehring_Homberger/homberger_200_customer_instances" "$OUTPUT_BASE/gehring_homberger_200" 600 600 150 50 "${HOMBERGER_200[@]}"

echo "=========================================================================="
echo " TOAN BO SUITE BENCHMARK DA HOAN THANH XUAT SAC                           "
echo "=========================================================================="
