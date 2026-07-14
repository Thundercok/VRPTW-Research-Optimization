#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
#  Penalty Search Experiment — Overnight Run
#  Compares Hybrid-DDQN with penalty_search ON vs OFF
#  on 8 representative Solomon instances × 3 seeds each.
#
#  Expected runtime: ~6-10 hours on M-series Mac (48 jobs total)
#  Output: results/penalty-experiment/
# ═══════════════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────
ITERS=12000           # 2.4× default — enough for RL to learn + penalty to adapt
EARLY_STOP=500        # 2× default — let penalty search explore longer
POLISH=80
SEEDS=(42 123 7)
OUT_DIR="results/penalty-experiment"
LOG="$OUT_DIR/experiment.log"

# Target instances: chosen for known TD gap + NV-matchable at Solomon 100 scale
# R1: tight TW, high NV → penalty helps escape local optima
# R2: wide TW, low NV → penalty can push TD toward BKS
# RC1: mixed, hardest family for NV reduction
# RC2: mixed wide, known TD gap
INSTANCES=(
    "RC101"   # BKS: NV=14, TD=1696.94 — historically NV=15 cold-start
    "RC207"   # BKS: NV=3,  TD=1061.14 — wide TW, TD gap target
    "R101"    # BKS: NV=19, TD=1650.80 — tight TW baseline
    "R201"    # BKS: NV=4,  TD=1252.37 — wide TW, low NV
    "R104"    # BKS: NV=9,  TD=1007.31 — tight TW, hard TD
    "RC104"   # BKS: NV=10, TD=1135.48 — tight mixed
    "R207"    # BKS: NV=2,  TD=890.61  — minimal vehicles
    "RC202"   # BKS: NV=3,  TD=1159.21 — wide mixed
)

# ── Setup ─────────────────────────────────────────────────────────────────
cd "$(dirname "$0")"
mkdir -p "$OUT_DIR"

echo "═══════════════════════════════════════════════════════════════" | tee "$LOG"
echo "  Penalty Search Experiment — $(date)"                          | tee -a "$LOG"
echo "  Instances: ${INSTANCES[*]}"                                    | tee -a "$LOG"
echo "  Seeds: ${SEEDS[*]}"                                            | tee -a "$LOG"
echo "  Iters: $ITERS, Early-stop: $EARLY_STOP"                       | tee -a "$LOG"
echo "═══════════════════════════════════════════════════════════════" | tee -a "$LOG"

# ── CSV header ────────────────────────────────────────────────────────────
CSV="$OUT_DIR/penalty_comparison.csv"
echo "Instance,Seed,Mode,NV,TD,Runtime_s,BKS_NV,BKS_TD,NV_Gap,TD_Gap_pct" > "$CSV"

# ── Run function ──────────────────────────────────────────────────────────
run_one() {
    local inst="$1"
    local seed="$2"
    local mode="$3"  # "baseline" or "penalty"
    local inst_lower
    inst_lower=$(echo "$inst" | tr '[:upper:]' '[:lower:]')
    local file="data/Solomon/${inst_lower}.txt"

    if [ ! -f "$file" ]; then
        echo "[SKIP] File not found: $file" | tee -a "$LOG"
        return
    fi

    local penalty_flag=""
    if [ "$mode" = "penalty" ]; then
        penalty_flag="--penalty-search"
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
        $penalty_flag \
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
# This ensures strict independent cold-starts per AGENTS.md rules.
total=$((${#INSTANCES[@]} * ${#SEEDS[@]} * 2))
count=0

for inst in "${INSTANCES[@]}"; do
    for seed in "${SEEDS[@]}"; do
        for mode in "baseline" "penalty"; do
            count=$((count + 1))
            echo "" | tee -a "$LOG"
            echo "── [$count/$total] ─────────────────────────────────────" | tee -a "$LOG"
            # Clear elite archive between runs to enforce cold-starts
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

# Pivot for side-by-side comparison
for inst in summary['Instance'].unique():
    rows = summary[summary['Instance'] == inst]
    base = rows[rows['Mode'] == 'baseline']
    pen = rows[rows['Mode'] == 'penalty']
    bks_nv = rows['BKS_NV'].iloc[0]
    bks_td = rows['BKS_TD'].iloc[0]

    b_nv = base['Mean_NV'].iloc[0] if len(base) else '?'
    b_td = base['Mean_TD'].iloc[0] if len(base) else '?'
    p_nv = pen['Mean_NV'].iloc[0] if len(pen) else '?'
    p_td = pen['Mean_TD'].iloc[0] if len(pen) else '?'

    print(f'{inst:8s}  BKS={bks_nv}/{bks_td:>8.2f}  '
          f'Base={b_nv:.1f}/{b_td:>8.2f}  '
          f'Penalty={p_nv:.1f}/{p_td:>8.2f}  '
          f'Δ_NV={p_nv - b_nv:+.1f}  '
          f'Δ_TD={p_td - b_td:+.2f}')
" 2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "Done. Full CSV at: $CSV" | tee -a "$LOG"
