#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
#  NAMI Full Experiment - No Early Stopping
#  Compares Baseline vs Adaptive (NAMI) on all 4 key instances across 3 seeds.
#  Expected runtime: ~2-3 hours (24 runs total: 4 instances × 3 seeds × 2 modes)
#  Output: results/nami-full-no-early-stop/
# ═══════════════════════════════════════════════════════════════════════════
set -euo pipefail

ITERS=12000
SEEDS=(42 123 7)
OUT_DIR="results/nami-full-no-early-stop"
LOG="$OUT_DIR/experiment.log"
CSV="$OUT_DIR/full_no_early_stop_comparison.csv"

INSTANCES=(
    "RC202"
    "RC207"
    "R104"
    "R101"
)

mkdir -p "$OUT_DIR"
echo "Instance,Seed,Mode,NV,TD,Runtime_s" > "$CSV"

echo "═══════════════════════════════════════════════════════════════" | tee "$LOG"
echo "  NAMI Full No-Early-Stop Experiment - $(date)"                   | tee -a "$LOG"
echo "  Instances: ${INSTANCES[*]}"                                    | tee -a "$LOG"
echo "  Seeds: ${SEEDS[*]}"                                            | tee -a "$LOG"
echo "═══════════════════════════════════════════════════════════════" | tee -a "$LOG"

run_one() {
    local inst="$1"
    local seed="$2"
    local mode="$3"
    local inst_lower
    inst_lower=$(echo "$inst" | tr '[:upper:]' '[:lower:]')
    local file="data/Solomon/${inst_lower}.txt"

    if [ ! -f "$file" ]; then
        echo "[SKIP] File not found: $file" | tee -a "$LOG"
        return
    fi

    local flags=""
    if [ "$mode" = "baseline" ]; then
        flags="--no-adaptive-feasibility"
    fi

    local tag="${inst}_seed${seed}_${mode}"
    local run_log="$OUT_DIR/${tag}.log"

    echo "[$(date +%H:%M:%S)] START $tag" | tee -a "$LOG"
    local t0
    t0=$(python3 -c "import time; print(time.time())")

    # Clear elite plans directory to ensure strict independent cold-starts
    rm -rf elite_plans/"${inst}"* 2>/dev/null || true

    PYTHONPATH=src uv run python -m vrptw solve "$file" \
        --algo Hybrid-DDQN \
        --iters "$ITERS" \
        --early-stop 999999 \
        --polish 80 \
        --seed "$seed" \
        $flags \
        > "$run_log" 2>&1

    local t1
    t1=$(python3 -c "import time; print(time.time())")
    local runtime
    runtime=$(python3 -c "print(f'{$t1 - $t0:.1f}')")

    local nv td
    nv=$(grep "^Vehicles:" "$run_log" | awk '{print $2}' || echo "?")
    td=$(grep "^Distance:" "$run_log" | awk '{print $2}' || echo "?")
    
    # Parse phase transition log
    local trans_log
    trans_log=$(grep "phase_transition_log" "$run_log" || echo "N/A")

    echo "[$(date +%H:%M:%S)] DONE  $tag → NV=$nv TD=$td (${runtime}s)" | tee -a "$LOG"
    if [ "$trans_log" != "N/A" ]; then
        echo "                 $trans_log" | tee -a "$LOG"
    fi

    echo "$inst,$seed,$mode,$nv,$td,$runtime" >> "$CSV"
}

total=$((${#INSTANCES[@]} * ${#SEEDS[@]} * 2))
count=0

for inst in "${INSTANCES[@]}"; do
    for seed in "${SEEDS[@]}"; do
        for mode in "baseline" "adaptive"; do
            count=$((count + 1))
            echo "" | tee -a "$LOG"
            echo "── [$count/$total] ─────────────────────────────────────" | tee -a "$LOG"
            run_one "$inst" "$seed" "$mode"
        done
    done
done

echo "" | tee -a "$LOG"
echo "═══════════════════════════════════════════════════════════════" | tee -a "$LOG"
echo "  COMPLETED. Full Table Summary:" | tee -a "$LOG"
python3 -c "
import pandas as pd
df = pd.read_csv('$CSV')
summary = df.groupby(['Instance', 'Mode']).agg(
    Mean_NV=('NV', 'mean'),
    Mean_TD=('TD', 'mean'),
    Mean_Time=('Runtime_s', 'mean')
).reset_index()
print(summary.to_string(index=False))
" 2>&1 | tee -a "$LOG"
echo "═══════════════════════════════════════════════════════════════" | tee -a "$LOG"
