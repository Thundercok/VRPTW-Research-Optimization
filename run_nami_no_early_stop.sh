#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
#  NAMI Experiment - No Early Stopping
#  Compares Baseline vs Adaptive (NAMI) on RC202 across 3 seeds without early stopping.
#  Expected runtime: ~10 minutes
# ═══════════════════════════════════════════════════════════════════════════
set -euo pipefail

ITERS=12000
SEEDS=(42 123 7)
OUT_DIR="results/nami-no-early-stop"
LOG="$OUT_DIR/experiment.log"
CSV="$OUT_DIR/no_early_stop_comparison.csv"

mkdir -p "$OUT_DIR"
echo "Instance,Seed,Mode,NV,TD,Runtime_s" > "$CSV"

echo "═══════════════════════════════════════════════════════════════" | tee "$LOG"
echo "  NAMI No-Early-Stop Experiment - $(date)"                        | tee -a "$LOG"
echo "═══════════════════════════════════════════════════════════════" | tee -a "$LOG"

run_one() {
    local seed="$1"
    local mode="$2"
    local flags=""
    
    if [ "$mode" = "baseline" ]; then
        flags="--no-adaptive-feasibility"
    fi

    local tag="RC202_seed${seed}_${mode}"
    local run_log="$OUT_DIR/${tag}.log"

    echo "[$(date +%H:%M:%S)] START $tag" | tee -a "$LOG"
    local t0
    t0=$(python3 -c "import time; print(time.time())")

    # Clear elite plans directory to ensure strict independent cold-starts
    rm -rf elite_plans/RC202* 2>/dev/null || true

    PYTHONPATH=src uv run python -m vrptw solve data/Solomon/rc202.txt \
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

    echo "RC202,$seed,$mode,$nv,$td,$runtime" >> "$CSV"
}

for seed in "${SEEDS[@]}"; do
    run_one "$seed" "baseline"
    run_one "$seed" "adaptive"
done

echo "═══════════════════════════════════════════════════════════════" | tee -a "$LOG"
echo "  COMPLETED. Summary results:" | tee -a "$LOG"
python3 -c "
import pandas as pd
df = pd.read_csv('$CSV')
for mode in ['baseline', 'adaptive']:
    sub = df[df['Mode'] == mode]
    print(f'Mode: {mode:10s} Mean_TD: {sub[\"TD\"].mean():.2f} Mean_Time: {sub[\"Runtime_s\"].mean():.1f}s')
" 2>&1 | tee -a "$LOG"
echo "═══════════════════════════════════════════════════════════════" | tee -a "$LOG"
