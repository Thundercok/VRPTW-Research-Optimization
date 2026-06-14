#!/usr/bin/env bash
set -uo pipefail

OUTPUT_BASE="results/ultimate-publication-suite"
LOG_DIR="$OUTPUT_BASE/runtime_logs"
mkdir -p "$OUTPUT_BASE" "$LOG_DIR"

echo "=========================================================================="
echo " KICH HOAT DOT BENCHMARK SAN XUAT TONG LUC PHUCO VU CONG BO QUOC TE       "
echo " Config: 7 Runs (Solomon) | 5 Runs (H-200) | 3 Runs (H-400/600/800/1000) "
echo " Shards: 8 total | Solomon(3) + Homberger-200/400/600/800/1000(5)         "
echo " Safety Mode: Fault-Tolerant Loop Enabled                                  "
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
    local runs="$4"
    local alns_iters="$5"
    local hybrid_iters="$6"
    local early_stop="$7"
    local polish_iters="$8"
    shift 8
    local instances=("$@")

    local shard_log_name="${shard_name// /_}"
    shard_log_name="${shard_log_name//[\/()]/_}"

    echo ""
    echo "--> Running Shard: $shard_name"
    echo "    Instances : ${#instances[@]}"
    echo "    Runs      : $runs"
    echo "    ALNS iters: $alns_iters | Hybrid iters: $hybrid_iters"
    echo "    Early-stop: $early_stop | Polish iters: $polish_iters"

    local gnn_arg=()
    if [[ -n "${GNN_PATH:-}" ]]; then
        gnn_arg+=(--gnn-path "$GNN_PATH")
        echo "    GNN Model : $GNN_PATH"
    fi

    if PYTHONPATH=src .venv/bin/python -u docs/run_benchmark.py \
        --data-path "$data_path" \
        --output-dir "$output_dir" \
        --runs "$runs" \
        --alns-iters "$alns_iters" \
        --hybrid-iters "$hybrid_iters" \
        --early-stop "$early_stop" \
        --polish-iters "$polish_iters" \
        --algorithms $ALGS \
        "${gnn_arg[@]}" \
        --instances "${instances[@]}" 2>&1 < /dev/null | tee "$LOG_DIR/shard_${shard_log_name}.log"; then

        echo "--> [SUCCESS] Shard $shard_name completed."
    else
        echo "--> [!!! CRITICAL ERROR !!!] Shard $shard_name execution failed. Check log at: $LOG_DIR/shard_${shard_log_name}.log" >&2
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# SOLOMON BENCHMARK (56 instances, 7 runs, 5000 iters)
# ─────────────────────────────────────────────────────────────────────────────

# ── SHARD 1: CLUSTERED INSTANCES (C1 & C2) ──────────────────────────────────
C1_C2_INSTANCES=(C101 C102 C103 C104 C105 C106 C107 C108 C109 C201 C202 C203 C204 C205 C206 C207 C208)
execute_benchmark_safe \
    "Solomon Clustered (C1/C2)" \
    "data/Solomon" "$OUTPUT_BASE/solomon_clustered" \
    7 5000 5000 1000 300 \
    "${C1_C2_INSTANCES[@]}"

# ── SHARD 2: RANDOM/MIXED SHORT HORIZON (R1 & RC1) ──────────────────────────
R1_RC1_INSTANCES=(R101 R102 R103 R104 R105 R106 R107 R108 R109 R110 R111 R112 RC101 RC102 RC103 RC104 RC105 RC106 RC107 RC108)
execute_benchmark_safe \
    "Solomon Short-Horizon (R1/RC1)" \
    "data/Solomon" "$OUTPUT_BASE/solomon_short_horizon" \
    7 5000 5000 1000 300 \
    "${R1_RC1_INSTANCES[@]}"

# ── SHARD 3: RANDOM/MIXED WIDE HORIZON (R2 & RC2) ───────────────────────────
R2_RC2_INSTANCES=(R201 R202 R203 R204 R205 R206 R207 R208 R209 R210 R211 RC201 RC202 RC203 RC204 RC205 RC206 RC207 RC208)
execute_benchmark_safe \
    "Solomon Wide-Horizon (R2/RC2)" \
    "data/Solomon" "$OUTPUT_BASE/solomon_wide_horizon" \
    7 5000 5000 1000 300 \
    "${R2_RC2_INSTANCES[@]}"

# ─────────────────────────────────────────────────────────────────────────────
# GEHRING & HOMBERGER — 200 CUSTOMERS (ALL 60 INSTANCES, 5 runs, 800 iters)
# ─────────────────────────────────────────────────────────────────────────────

# ── SHARD 4: HOMBERGER 200 — ALL INSTANCES ───────────────────────────────────
HOMBERGER_200=(
    C1_2_1  C1_2_2  C1_2_3  C1_2_4  C1_2_5  C1_2_6  C1_2_7  C1_2_8  C1_2_9  C1_2_10
    C2_2_1  C2_2_2  C2_2_3  C2_2_4  C2_2_5  C2_2_6  C2_2_7  C2_2_8  C2_2_9  C2_2_10
    R1_2_1  R1_2_2  R1_2_3  R1_2_4  R1_2_5  R1_2_6  R1_2_7  R1_2_8  R1_2_9  R1_2_10
    R2_2_1  R2_2_2  R2_2_3  R2_2_4  R2_2_5  R2_2_6  R2_2_7  R2_2_8  R2_2_9  R2_2_10
    RC1_2_1 RC1_2_2 RC1_2_3 RC1_2_4 RC1_2_5 RC1_2_6 RC1_2_7 RC1_2_8 RC1_2_9 RC1_2_10
    RC2_2_1 RC2_2_2 RC2_2_3 RC2_2_4 RC2_2_5 RC2_2_6 RC2_2_7 RC2_2_8 RC2_2_9 RC2_2_10
)
execute_benchmark_safe \
    "Homberger-200 (All 60)" \
    "data/Gehring_Homberger/homberger_200_customer_instances" "$OUTPUT_BASE/gehring_homberger_200" \
    5 800 800 200 60 \
    "${HOMBERGER_200[@]}"

# ─────────────────────────────────────────────────────────────────────────────
# GEHRING & HOMBERGER — 400 CUSTOMERS (24 instances, 3 runs, 600 iters)
# Representatives: *_1 through *_4 from each of the 6 problem families
# ─────────────────────────────────────────────────────────────────────────────

# ── SHARD 5: HOMBERGER 400 ───────────────────────────────────────────────────
HOMBERGER_400=(
    C1_4_1  C1_4_2  C1_4_3  C1_4_4
    C2_4_1  C2_4_2  C2_4_3  C2_4_4
    R1_4_1  R1_4_2  R1_4_3  R1_4_4
    R2_4_1  R2_4_2  R2_4_3  R2_4_4
    RC1_4_1 RC1_4_2 RC1_4_3 RC1_4_4
    RC2_4_1 RC2_4_2 RC2_4_3 RC2_4_4
)
execute_benchmark_safe \
    "Homberger-400 (24 instances)" \
    "data/Gehring_Homberger/homberger_400_customer_instances" "$OUTPUT_BASE/gehring_homberger_400" \
    3 600 600 150 50 \
    "${HOMBERGER_400[@]}"

# ─────────────────────────────────────────────────────────────────────────────
# GEHRING & HOMBERGER — 600 CUSTOMERS (12 instances, 3 runs, 400 iters)
# Representatives: *_1 and *_2 from each of the 6 problem families
# ─────────────────────────────────────────────────────────────────────────────

# ── SHARD 6: HOMBERGER 600 ───────────────────────────────────────────────────
HOMBERGER_600=(
    C1_6_1  C1_6_2
    C2_6_1  C2_6_2
    R1_6_1  R1_6_2
    R2_6_1  R2_6_2
    RC1_6_1 RC1_6_2
    RC2_6_1 RC2_6_2
)
execute_benchmark_safe \
    "Homberger-600 (12 instances)" \
    "data/Gehring_Homberger/homberger_600_customer_instances" "$OUTPUT_BASE/gehring_homberger_600" \
    3 400 400 100 35 \
    "${HOMBERGER_600[@]}"

# ─────────────────────────────────────────────────────────────────────────────
# GEHRING & HOMBERGER — 800 CUSTOMERS (6 instances, 3 runs, 300 iters)
# Representatives: *_1 only from each of the 6 problem families
# ─────────────────────────────────────────────────────────────────────────────

# ── SHARD 7: HOMBERGER 800 ───────────────────────────────────────────────────
HOMBERGER_800=(C1_8_1 C2_8_1 R1_8_1 R2_8_1 RC1_8_1 RC2_8_1)
execute_benchmark_safe \
    "Homberger-800 (6 instances)" \
    "data/Gehring_Homberger/homberger_800_customer_instances" "$OUTPUT_BASE/gehring_homberger_800" \
    3 300 300 75 25 \
    "${HOMBERGER_800[@]}"

# ─────────────────────────────────────────────────────────────────────────────
# GEHRING & HOMBERGER — 1000 CUSTOMERS STRESS TEST (6 instances, 3 runs, 200 iters)
# Representatives: *_1 only from each of the 6 problem families
# NOTE: Low iter budget — intended as a scalability demonstration, not optimality.
# ─────────────────────────────────────────────────────────────────────────────

# ── SHARD 8: HOMBERGER 1000 (STRESS) ─────────────────────────────────────────
HOMBERGER_1000=(C1_10_1 C2_10_1 R1_10_1 R2_10_1 RC1_10_1 RC2_10_1)
execute_benchmark_safe \
    "Homberger-1000 Stress (6 instances)" \
    "data/Gehring_Homberger/homberger_1000_customer_instances" "$OUTPUT_BASE/gehring_homberger_1000" \
    3 200 200 50 20 \
    "${HOMBERGER_1000[@]}"

echo ""
echo "=========================================================================="
echo " TOAN BO SUITE BENCHMARK DA HOAN THANH XUAT SAC                           "
echo " Coverage: 56 Solomon + 60 H-200 + 24 H-400 + 12 H-600 + 6 H-800 + 6 H-1000"
echo " Total: 164 instances across 8 shards                                     "
echo "=========================================================================="
