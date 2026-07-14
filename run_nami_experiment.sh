#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
#  NAMI Adaptive Feasibility Experiment
#  Compares Hybrid-DDQN under three regimes:
#  1. Baseline (strictly feasible search)
#  2. Penalty-Search (always on infeasible search)
#  3. Adaptive Feasibility (our new dynamic NAMI framework)
#
#  Expected runtime: ~3-5 hours (36 runs total: 4 instances × 3 seeds × 3 modes)
#  Output: results/nami-experiment/
# ═══════════════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────
ITERS=12000
EARLY_STOP=500
POLISH=80
SEEDS=(42 123 7)
OUT_DIR="results/nami-experiment"
LOG="$OUT_DIR/experiment.log"

INSTANCES=(
    "RC202"   # Wide TW, mixed — Penalty won heavily on TD (-22km)
    "RC207"   # Wide TW — Baseline won heavily on TD (-11km)
    "R104"    # Tight TW — Penalty won on TD (-10km)
    "R101"    # Tight TW — Baseline reached exact BKS, Penalty was worse
)

# ── Setup ─────────────────────────────────────────────────────────────────
cd "$(dirname "$0")"
mkdir -p "$OUT_DIR"

echo "═══════════════════════════════════════════════════════════════" | tee "$LOG"
echo "  NAMI Adaptive Feasibility Experiment — $(date)"                | tee -a "$LOG"
echo "  Instances: ${INSTANCES[*]}"                                    | tee -a "$LOG"
echo "  Seeds: ${SEEDS[*]}"                                            | tee -a "$LOG"
echo "  Iters: $ITERS, Early-stop: $EARLY_STOP"                       | tee -a "$LOG"
echo "═══════════════════════════════════════════════════════════════" | tee -a "$LOG"

# ── CSV header ────────────────────────────────────────────────────────────
CSV="$OUT_DIR/nami_comparison.csv"
echo "Instance,Seed,Mode,NV,TD,Runtime_s,BKS_NV,BKS_TD,NV_Gap,TD_Gap_pct" > "$CSV"

# ── Run function ──────────────────────────────────────────────────────────
run_one() {
    local inst="$1"
    local seed="$2"
    local mode="$3"  # "baseline", "penalty", or "adaptive"
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
    elif [ "$mode" = "penalty" ]; then
        flags="--penalty-search --no-adaptive-feasibility"
    elif [ "$mode" = "adaptive" ]; then
        flags=""  # defaults to adaptive
    fi

    local tag="${inst}_seed${seed}_${mode}"
    local run_log="$OUT_DIR/${tag}.log"

    echo "[$(date +%H:%M:%S)] START $tag" | tee -a "$LOG"
    local t0
    t0=$(python3 -c "import time; print(time.time())")

    PYTHONPATH=src uv run python -m vrptw solve "$file" \
        --algo Hybrid-DDQN \
        --iters "$ITERS" \
        --early-stop "$EARLY_STOP" \
        --polish "$POLISH" \
        --seed "$seed" \
        $flags \
        > "$run_log" 2>&1

    local t1
    t1=$(python3 -c "import time; print(time.time())")
    local runtime
    runtime=$(python3 -c "print(f'{$t1 - $t0:.1f}')")

    # Parse output
    local nv td
    nv=$(grep "^Vehicles:" "$run_log" | awk '{print $2}' || echo "?")
    td=$(grep "^Distance:" "$run_log" | awk '{print $2}' || echo "?")

    echo "[$(date +%H:%M:%S)] DONE  $tag → NV=$nv TD=$td (${runtime}s)" | tee -a "$LOG"

    # Look up BKS
    local bks_nv bks_td nv_gap td_gap
    bks_nv=$(python3 -c "
from src.vrptw.config import BKS
b = BKS.get('$inst', {})
print(int(b.get('nv', 0)))
")
    bks_td=$(python3 -c "
from src.vrptw.config import BKS
b = BKS.get('$inst', {})
print(f\"{b.get('td', 0):.2f}\")
")

    if [ "$nv" != "?" ] && [ "$bks_nv" != "0" ]; then
        nv_gap=$(python3 -c "print($nv - $bks_nv)")
        if [ "$nv" = "$bks_nv" ]; then
            td_gap=$(python3 -c "print(f'{($td - $bks_td) / $bks_td * 100:.2f}')")
        else
            td_gap="NV_MISMATCH"
        fi
    else
        nv_gap="?"
        td_gap="?"
    fi

    echo "$inst,$seed,$mode,$nv,$td,$runtime,$bks_nv,$bks_td,$nv_gap,$td_gap" >> "$CSV"
}

# ── Main execution: sequential to avoid EliteArchive cross-contamination ──
total=$((${#INSTANCES[@]} * ${#SEEDS[@]} * 3))
count=0

for inst in "${INSTANCES[@]}"; do
    for seed in "${SEEDS[@]}"; do
        for mode in "baseline" "penalty" "adaptive"; do
            count=$((count + 1))
            echo "" | tee -a "$LOG"
            echo "── [$count/$total] ─────────────────────────────────────" | tee -a "$LOG"
            rm -rf elite_plans/"${inst}"* 2>/dev/null || true
            run_one "$inst" "$seed" "$mode"
        done
    done
done

# ── Summary ───────────────────────────────────────────────────────────────
echo "" | tee -a "$LOG"
echo "═══════════════════════════════════════════════════════════════" | tee -a "$LOG"
echo "  EXPERIMENT COMPLETE — $(date)" | tee -a "$LOG"
echo "  Results: $CSV" | tee -a "$LOG"
echo "═══════════════════════════════════════════════════════════════" | tee -a "$LOG"

# Print summary table
echo "" | tee -a "$LOG"
echo "── Summary Table ──" | tee -a "$LOG"
python3 -c "
import pandas as pd
import sys

df = pd.read_csv('$CSV')
if df.empty:
    print('No results found.')
    sys.exit(0)

# Group by instance and mode, aggregate
summary = df.groupby(['Instance', 'Mode']).agg(
    Mean_NV=('NV', 'mean'),
    Mean_TD=('TD', 'mean'),
    Mean_Runtime=('Runtime_s', 'mean'),
    BKS_NV=('BKS_NV', 'first'),
    BKS_TD=('BKS_TD', 'first'),
).reset_index()

# Pivot for comparison
for inst in summary['Instance'].unique():
    rows = summary[summary['Instance'] == inst]
    base = rows[rows['Mode'] == 'baseline']
    pen = rows[rows['Mode'] == 'penalty']
    adap = rows[rows['Mode'] == 'adaptive']
    bks_nv = rows['BKS_NV'].iloc[0]
    bks_td = rows['BKS_TD'].iloc[0]

    b_nv = base['Mean_NV'].iloc[0] if len(base) else '?'
    b_td = base['Mean_TD'].iloc[0] if len(base) else '?'
    p_nv = pen['Mean_NV'].iloc[0] if len(pen) else '?'
    p_td = pen['Mean_TD'].iloc[0] if len(pen) else '?'
    a_nv = adap['Mean_NV'].iloc[0] if len(adap) else '?'
    a_td = adap['Mean_TD'].iloc[0] if len(adap) else '?'

    print(f'{inst:8s}  BKS={bks_nv}/{bks_td:>8.2f}  '
          f'Base={b_nv:.1f}/{b_td:>8.2f}  '
          f'Penalty={p_nv:.1f}/{p_td:>8.2f}  '
          f'Adaptive={a_nv:.1f}/{a_td:>8.2f}')
" 2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "Done. Full CSV at: $CSV" | tee -a "$LOG"
