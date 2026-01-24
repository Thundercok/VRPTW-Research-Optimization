# v9.6 Patch — 4 cells cần thay thế

## CHANGELOG v9.6 vs v9.5
- [CFG-1] alns_iterations: 2000 → 3000
- [CFG-2] hybrid_iterations: 2000 → 3000
- [CFG-3] n_runs: 5 → 8
- [CFG-4] early_stop_patience: 400 → 600
- [CFG-5] plateau_start: 60 → 80
- [CFG-6] ctrl_eps_decay: 0.992 → 0.995
- [BENCH-1] run_benchmark: checkpoint save mỗi 4 instances → phòng crash
- [BENCH-2] run_benchmark: lưu raw per-run costs cho Wilcoxon per-run
- [STATS-1] wilcoxon_per_run: paired test trên n=instances×runs thay vì n=instances
- [STATS-2] print_stats_table gọi cả 2 test versions
- [VER] version string → v9.6

---

## CELL 1 — Thay toàn bộ source của Cell 1 (Install, Imports & Config)

```python
# ── Cell 1 : Install, Imports & Config ─────────────────────────────────────
# !pip install numba safetensors scipy -q
 
import glob, math, os, random, time, json, shutil
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Iterable, List, Optional, Tuple
 
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from numba import njit
from scipy import stats
 
try:
    from safetensors.torch import save_file, load_file
    SAFETENSORS_OK = True
except ImportError:
    SAFETENSORS_OK = False
    print("⚠️  safetensors not available — transfer learning save/load disabled")
 
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f'✅ Device : {DEVICE}')
 
BKS: Dict[str, Dict[str, float]] = {
    "RC101": {"nv": 14, "td": 1696.94}, "RC102": {"nv": 12, "td": 1554.75},
    "RC103": {"nv": 11, "td": 1261.67}, "RC104": {"nv": 10, "td": 1135.48},
    "RC105": {"nv": 13, "td": 1629.44}, "RC106": {"nv": 11, "td": 1424.73},
    "RC107": {"nv": 11, "td": 1230.48}, "RC108": {"nv": 10, "td": 1139.82},
    "RC201": {"nv": 4,  "td": 1406.94}, "RC202": {"nv": 3,  "td": 1365.64},
    "RC203": {"nv": 3,  "td": 1049.62}, "RC204": {"nv": 3,  "td": 798.46},
    "RC205": {"nv": 4,  "td": 1297.65}, "RC206": {"nv": 3,  "td": 1146.32},
    "RC207": {"nv": 3,  "td": 1061.14}, "RC208": {"nv": 3,  "td": 828.14},
}
 
def default_data_path() -> str:
    candidates = [
        "/kaggle/input/vrptw-benchmark-datasets/data/Solomon",
        "/kaggle/input/datasets/senju14/vrptw-benchmark-datasets/data/Solomon",
        "/content/vrptw-benchmark/data/Solomon",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]
 
def default_output_dir() -> str:
    return "/kaggle/working" if os.path.exists("/kaggle/working") else "/content"
 
@dataclass
class Config:
    data_path:   str   = default_data_path()
    output_dir:  str   = default_output_dir()
 
    # [CFG-1][CFG-2] Increased iterations for 12h budget
    alns_iterations:   int   = 3000
    destroy_ratio_min: float = 0.10
    destroy_ratio_max: float = 0.40
    temp_control:      float = 0.05
    temp_decay:        float = 0.99975
    sigma1:            int   = 33
    sigma2:            int   = 9
    sigma3:            int   = 3
    weight_decay:      float = 0.10
    segment_size:      int   = 50
    # [CFG-4] scaled with iterations
    early_stop_patience: int = 600
 
    # [CFG-2] Hybrid iterations
    hybrid_iterations: int   = 3000
 
    # [CFG-3] More runs → stronger Wilcoxon (n=128 per-run pairs)
    n_runs: int = 8
    seed:   int = 42
 
    # PlateauController network
    ctrl_state_dim:   int   = 10
    ctrl_hidden:      int   = 96
    ctrl_lr:          float = 3e-4
    ctrl_gamma:       float = 0.95
    ctrl_buffer:      int   = 4096
    ctrl_batch:       int   = 64
    ctrl_target_freq: int   = 20
    ctrl_eps_start:   float = 0.35
    ctrl_eps_end:     float = 0.05
    # [CFG-6] slower decay for longer runs
    ctrl_eps_decay:   float = 0.995
 
    # [CFG-5] plateau trigger later — avoid premature RL activation
    plateau_start:                   int = 80
    post_improve_intensify_segments: int = 3
 
    # [PERF-1] NV penalty coefficient in segment reward
    nv_increase_penalty: float = 15.0
 
    # DQN ablation (only used by DQNSolver)
    dqn_state_dim:      int   = 13
    dqn_hidden:         int   = 128
    dqn_lr:             float = 1e-3
    dqn_gamma:          float = 0.99
    dqn_buffer:         int   = 8192
    dqn_batch:          int   = 64
    dqn_eps_start:      float = 1.0
    dqn_eps_end:        float = 0.05
    dqn_eps_decay:      float = 0.995
    dqn_target_freq:    int   = 20
    dqn_train_freq:     int   = 5
    dqn_vehicle_penalty:float = 5.0
 
@dataclass(frozen=True)
class ModeSpec:
    name:             str
    destroy_scale:    float
    temp_boost:       float
    temp_decay_scale: float
    destroy_bias:     Tuple[float, ...]
    repair_bias:      Tuple[float, ...]
 
MODES: Tuple[ModeSpec, ...] = (
    ModeSpec("default",    1.00, 1.00,  1.000,
             (1.0, 1.0, 1.0, 1.0, 1.0), (1.0, 1.0, 1.0, 1.0)),
    ModeSpec("intensify",  0.70, 0.98,  0.995,
             (0.8, 1.3, 1.2, 0.5, 1.0), (1.3, 1.2, 0.8, 1.0)),
    ModeSpec("diversify",  1.35, 1.08,  1.002,
             (1.3, 0.9, 1.3, 1.4, 1.0), (0.9, 1.0, 1.3, 1.0)),
    ModeSpec("tw_rescue",  1.10, 1.05,  1.000,
             (0.7, 0.9, 1.1, 0.8, 1.8), (0.8, 1.0, 1.2, 1.8)),
)
 
MODE_DEFAULT, MODE_INTENSIFY, MODE_DIVERSIFY, MODE_TW_RESCUE = 0, 1, 2, 3
CFG = Config()
 
# alias for export cell
OUTPUT_DIR = CFG.output_dir
 
print('✅ Config ready — v9.6 (iter=3000, n_runs=8, patience=600)')
```

---

## CELL 11 — Thay toàn bộ source của Cell 11 (Benchmark Runner)

```python
# ── Cell 11: Benchmark Runner ─────────────────────────────────────────────────
def run_instance(inst: Inst, algo: str, cfg: Config,
                 seed: int,
                 transfer_weights: Optional[Dict] = None) -> Dict:
    start = time.time()
 
    if algo == "ALNS":
        plan, history = ALNSSolver(inst, cfg).solve(seed=seed)
 
    elif algo in ("DDQN-ALNS", "PLATEAU-HYBRID"):
        solver = PlateauHybridSolver(inst, cfg)
        plan, history = solver.solve(seed=seed)
 
    elif algo == "DDQN-ALNS★":
        solver = PlateauHybridSolver(inst, cfg)
        if transfer_weights is not None:
            solver.load_weights(transfer_weights)
        plan, history = solver.solve(seed=seed, frozen=True)
 
    elif algo == "DQN":
        plan, history = DQNSolver(inst, cfg).solve(seed=seed)
 
    else:
        raise ValueError(f"Unsupported algorithm: {algo}")
 
    bks = BKS.get(inst.name)
    return {
        "nv":      plan.nv,
        "cost":    plan.cost,
        "time":    time.time() - start,
        "td_gap":  (plan.cost - bks["td"]) / bks["td"] * 100 if bks else None,
        "nv_diff": plan.nv - bks["nv"] if bks else None,
        "on_time": plan.on_time_rate,
        "hist":    history,
    }
 
 
def run_benchmark(instances:        Iterable[Inst],
                  algorithms:       List[str],
                  cfg:              Config,
                  result_path:      Optional[str]  = None,
                  transfer_weights: Optional[Dict]  = None) -> pd.DataFrame:
    """
    [BENCH-1] Checkpoint save every 4 instances to /kaggle/working/benchmark_checkpoint.csv
    [BENCH-2] Stores per-run costs in raw_costs column for Wilcoxon per-run analysis
    """
    instances    = list(instances)
    result_path  = result_path or os.path.join(cfg.output_dir, "benchmark_clean.csv")
    ckpt_path    = os.path.join(cfg.output_dir, "benchmark_checkpoint.csv")
    rows: List[Dict] = []
 
    total = len(instances) * len(algorithms)
    print(f"Total: {total} combos × {cfg.n_runs} runs\n" + "=" * 60)
    wall_start = time.time()
 
    for inst_idx, inst in enumerate(instances):
        dataset = "RC1" if inst.name[2] == "1" else "RC2"
        for algo in algorithms:
            print(f"\n[{inst.name}] {algo}")
            nv_v, cost_v, time_v, gap_v, nvd_v, ot_v = [], [], [], [], [], []
            for run_idx in range(cfg.n_runs):
                res = run_instance(inst, algo, cfg,
                                   cfg.seed + run_idx, transfer_weights)
                nv_v.append(res["nv"])
                cost_v.append(res["cost"])
                time_v.append(res["time"])
                gap_v.append(res["td_gap"])
                nvd_v.append(res["nv_diff"])
                ot_v.append(res["on_time"])
                elapsed = time.time() - wall_start
                print(f"  run {run_idx + 1}/{cfg.n_runs}: "
                      f"nv={res['nv']} cost={res['cost']:.1f} "
                      f"({res['time']:.1f}s) | wall {elapsed/3600:.2f}h")
 
            row = {
                "Dataset":   dataset,
                "Instance":  inst.name,
                "Algorithm": algo,
                "NV_mean":   round(np.mean(nv_v),   2),
                "NV_std":    round(np.std(nv_v),    2),
                "NV_diff":   round(np.mean(nvd_v),  2) if nvd_v[0] is not None else None,
                "TD_mean":   round(np.mean(cost_v), 2),
                "TD_std":    round(np.std(cost_v),  2),
                "Gap%":      round(np.mean(gap_v),  2) if gap_v[0] is not None else None,
                "OnTime":    round(np.mean(ot_v) * 100, 1),
                "Time_s":    round(np.mean(time_v), 1),
                "NV_cv":     round(np.std(nv_v)   / max(np.mean(nv_v),   1) * 100, 2),
                "TD_cv":     round(np.std(cost_v)  / max(np.mean(cost_v), 1) * 100, 2),
                # [BENCH-2] raw per-run costs, semicolon-separated
                "raw_costs": ";".join(f"{c:.4f}" for c in cost_v),
                "raw_nv":    ";".join(str(n) for n in nv_v),
            }
            rows.append(row)
            gap_text = f"{row['Gap%']:+.1f}%" if row["Gap%"] is not None else "--"
            print(f"  → nv={row['NV_mean']:.1f}±{row['NV_std']:.1f}  "
                  f"td={row['TD_mean']:.1f}±{row['TD_std']:.1f}  gap={gap_text}")
 
        # [BENCH-1] checkpoint every 4 instances
        if (inst_idx + 1) % 4 == 0:
            pd.DataFrame(rows).to_csv(ckpt_path, index=False)
            elapsed = time.time() - wall_start
            print(f"\n  💾 Checkpoint saved ({inst_idx+1}/{len(instances)} instances, "
                  f"{elapsed/3600:.2f}h elapsed) → {ckpt_path}")
 
    df = pd.DataFrame(rows)
    df.to_csv(result_path, index=False)
    total_time = time.time() - wall_start
    print(f"\n✅ Benchmark complete in {total_time/3600:.2f}h → {result_path}")
    return df
 
 
def print_summary_table(df: pd.DataFrame) -> None:
    summary = (
        df.groupby(["Dataset", "Algorithm"])
          .agg(NV=("NV_mean", "mean"), NV_std=("NV_std", "mean"),
               NV_diff=("NV_diff", "mean"), TD=("TD_mean", "mean"),
               TD_std=("TD_std", "mean"), Gap=("Gap%", "mean"),
               OnTime=("OnTime", "mean"), Time=("Time_s", "mean"))
          .round(2).reset_index()
    )
    print("\n" + "-" * 86)
    print(f"{'DS':<4}{'Algorithm':<18}{'NV':>6}{'+/-':>6}{'vsBKS':>8}"
          f"{'TD':>10}{'+/-':>8}{'Gap%':>8}{'OT%':>7}{'Time':>8}")
    print("-" * 86)
    for _, row in summary.iterrows():
        gap    = f"{row['Gap']:+.2f}%" if pd.notna(row["Gap"])    else "--"
        nv_diff = f"{row['NV_diff']:+.2f}" if pd.notna(row["NV_diff"]) else "--"
        print(f"{row['Dataset']:<4}{row['Algorithm']:<18}"
              f"{row['NV']:>6.2f}{row['NV_std']:>6.2f}{nv_diff:>8}"
              f"{row['TD']:>10.2f}{row['TD_std']:>8.2f}{gap:>8}"
              f"{row['OnTime']:>7.1f}{row['Time']:>7.1f}s")
    print("-" * 86)


print('✅ Benchmark runner ready.')
```

---

## CELL 13 — Thay toàn bộ source của Cell 13 (Statistical Tests & Paper Tables)

```python
# ── Cell 13: Statistical Tests & Paper Tables ─────────────────────────────────
def wilcoxon_test(df: pd.DataFrame, algo_a: str, algo_b: str,
                  metric: str = 'Gap%',
                  dataset: Optional[str] = None) -> Dict:
    """Per-instance-mean test (n=8). Legacy approach, kept for comparison."""
    sub = df if dataset is None else df[df['Dataset'] == dataset]
    a   = sub[sub['Algorithm'] == algo_a][metric].dropna().values
    b   = sub[sub['Algorithm'] == algo_b][metric].dropna().values
    n   = min(len(a), len(b))
    a, b = a[:n], b[:n]
    if n < 3:
        return {'stat': None, 'p': None, 'sig': False, 'n': n}
    stat, p = stats.wilcoxon(a, b, alternative='two-sided')
    return {
        'stat': round(stat, 3), 'p': round(p, 4), 'sig': p < 0.05,
        'n': n, 'better': algo_a if a.mean() < b.mean() else algo_b,
        'method': 'per_instance_mean',
    }


def wilcoxon_per_run(df: pd.DataFrame, algo_a: str, algo_b: str,
                     dataset: Optional[str] = None) -> Dict:
    """
    [STATS-1] Per-run paired test on raw costs.
    n = instances × n_runs (e.g. 8 × 8 = 64 per family).
    Much stronger statistical power than per-instance-mean (n=8).

    Pairing: run_k of algo_a on instance_i  vs  run_k of algo_b on instance_i.
    This is valid because same seed+k guarantees same initial solution.
    """
    sub = df if dataset is None else df[df['Dataset'] == dataset]
    a_rows = sub[sub['Algorithm'] == algo_a]
    b_rows = sub[sub['Algorithm'] == algo_b]

    costs_a, costs_b = [], []
    common_instances = set(a_rows['Instance']) & set(b_rows['Instance'])

    for inst_name in sorted(common_instances):
        ra = a_rows[a_rows['Instance'] == inst_name]
        rb = b_rows[b_rows['Instance'] == inst_name]
        if ra.empty or rb.empty:
            continue
        # raw_costs column: "c1;c2;...;cn_runs"
        if 'raw_costs' not in ra.columns:
            # fallback: use TD_mean as single observation
            costs_a.append(float(ra['TD_mean'].values[0]))
            costs_b.append(float(rb['TD_mean'].values[0]))
        else:
            ac = [float(x) for x in ra['raw_costs'].values[0].split(';')]
            bc = [float(x) for x in rb['raw_costs'].values[0].split(';')]
            n  = min(len(ac), len(bc))
            costs_a.extend(ac[:n])
            costs_b.extend(bc[:n])

    costs_a = np.array(costs_a)
    costs_b = np.array(costs_b)
    n = len(costs_a)

    if n < 6:
        return {'stat': None, 'p': None, 'sig': False, 'n': n,
                'method': 'per_run'}

    # Skip zero-difference pairs (wilcoxon requirement)
    diff = costs_a - costs_b
    nonzero = diff[diff != 0]
    if len(nonzero) < 6:
        return {'stat': None, 'p': None, 'sig': False, 'n': n,
                'method': 'per_run'}

    stat, p = stats.wilcoxon(costs_a, costs_b, alternative='two-sided')
    effect = (costs_b.mean() - costs_a.mean()) / costs_a.mean() * 100  # % improvement of a over b
    return {
        'stat':   round(stat, 3),
        'p':      round(p, 4),
        'sig':    p < 0.05,
        'n':      n,
        'better': algo_a if costs_a.mean() < costs_b.mean() else algo_b,
        'effect_pct': round(effect, 3),  # positive = algo_a is better by this %
        'method': 'per_run',
    }


def print_paper_table(df: pd.DataFrame) -> None:
    summary = (
        df.groupby(['Dataset', 'Algorithm'])
          .agg(NV=('NV_mean', 'mean'), NV_std=('NV_std', 'mean'),
               NV_d=('NV_diff', 'mean'),
               TD=('TD_mean', 'mean'), TD_std=('TD_std', 'mean'),
               Gap=('Gap%', 'mean'),
               CV_nv=('NV_cv', 'mean'), CV_td=('TD_cv', 'mean'),
               OT=('OnTime', 'mean'), Time=('Time_s', 'mean'))
          .round(2).reset_index()
    )
    hdr = (f'{"DS":<4}{"Algorithm":<14}{"NV":>6}{"±":>4}{"vsBKS":>8}'
           f'{"TD":>9}{"±":>6}{"Gap%":>7}{"CV_NV":>6}{"CV_TD":>6}'
           f'{"OT%":>6}{"Time":>7}')
    sep = '─' * len(hdr)
    print('\n' + sep)
    print(hdr)
    print(sep)
    prev = ''
    for _, r in summary.iterrows():
        if r['Dataset'] != prev and prev:
            print(sep)
        prev   = r['Dataset']
        nv_d   = f"{r['NV_d']:+.1f}" if pd.notna(r['NV_d']) else '—'
        gap    = f"{r['Gap']:+.1f}%" if pd.notna(r['Gap'])   else '—'
        print(f"{r['Dataset']:<4}{r['Algorithm']:<14}"
              f"{r['NV']:>6.1f}{r['NV_std']:>4.1f}{nv_d:>8}"
              f"{r['TD']:>9.1f}{r['TD_std']:>6.1f}{gap:>7}"
              f"{r['CV_nv']:>6.1f}{r['CV_td']:>6.1f}"
              f"{r['OT']:>6.1f}{r['Time']:>6.1f}s")
    print(sep)
    print('CV = std/mean×100%. Negative Gap%: solution beats BKS distance.')


def print_stats_table(df: pd.DataFrame) -> None:
    """[STATS-2] Print both per-instance-mean and per-run Wilcoxon results."""
    pairs = [('DDQN-ALNS', 'ALNS'), ('DDQN-ALNS★', 'ALNS')]

    # ── Per-instance-mean (n=8 per family) ──────────────────────────────────
    print('\n── Wilcoxon signed-rank — per-instance-mean (n=instances) ──')
    print(f'{"Comparison":<28}{"DS":<5}{"Metric":<8}'
          f'{"W":>7}{"p":>9}{"Sig":>5}{"Better":>12}')
    print('─' * 70)
    for algo_a, algo_b in pairs:
        if algo_a not in df['Algorithm'].values:
            continue
        for ds in ['RC1', 'RC2']:
            for metric in ['Gap%', 'NV_mean']:
                res = wilcoxon_test(df, algo_a, algo_b, metric, ds)
                if res['stat'] is None:
                    continue
                sig = '✅' if res['sig'] else '—'
                print(f'  {algo_a} vs {algo_b:<8}  {ds:<5}{metric:<8}'
                      f'{res["stat"]:>7.1f}{res["p"]:>9.4f}'
                      f'{sig:>5}{res["better"]:>12}')
    print('─' * 70)
    print('✅ = p < 0.05')

    # ── Per-run (n=instances×n_runs, much stronger) ──────────────────────────
    print('\n── Wilcoxon signed-rank — per-run paired (n=instances×n_runs) ──')
    print(f'{"Comparison":<28}{"DS":<5}{"n":>5}'
          f'{"W":>9}{"p":>9}{"Sig":>5}{"Effect%":>9}{"Better":>12}')
    print('─' * 78)
    for algo_a, algo_b in pairs:
        if algo_a not in df['Algorithm'].values:
            continue
        for ds in ['RC1', 'RC2']:
            res = wilcoxon_per_run(df, algo_a, algo_b, ds)
            if res['stat'] is None:
                print(f'  {algo_a} vs {algo_b:<8}  {ds:<5}'
                      f'{"n=" + str(res["n"]):>5}  insufficient data')
                continue
            sig = '✅' if res['sig'] else '—'
            eff = f"{res['effect_pct']:+.3f}%"
            print(f'  {algo_a} vs {algo_b:<8}  {ds:<5}{res["n"]:>5}'
                  f'{res["stat"]:>9.1f}{res["p"]:>9.4f}'
                  f'{sig:>5}{eff:>9}{res["better"]:>12}')
    print('─' * 78)
    print('Effect% = mean cost improvement of "Better" over other.')
    print('✅ = p < 0.05  |  per-run n =', end=' ')
    try:
        sample = df[df['Algorithm'] == 'ALNS']
        if 'raw_costs' in sample.columns:
            ex = sample.iloc[0]['raw_costs'].count(';') + 1
            print(f'{len(sample)} instances × {ex} runs = {len(sample)*ex} pairs/family')
        else:
            print('(raw_costs not available)')
    except Exception:
        print('?')


print('✅ Stats & table utilities ready.')
```

---

## CELL 16 — Thay toàn bộ source của Cell 16 (Phase 1 — Main Benchmark)

```python
# ── Cell 16: Phase 1 — Main Benchmark ────────────────────────────────────────
# v9.6: iter=3000, n_runs=8, patience=600, plateau_start=80
# Expected runtime: ~9.5h for this cell alone
RESULT_PATH = os.path.join(CFG.output_dir, 'benchmark_clean.csv')
 
df = run_benchmark(
    instances  = RC1 + RC2,
    algorithms = ['ALNS', 'DDQN-ALNS'],
    cfg        = CFG,
    result_path= RESULT_PATH,
)
print_summary_table(df)
print_paper_table(df)
print_stats_table(df)
plot_dashboard(df)
```

---

## CŨNG CẦN: Sửa version string trong Cell 21 (NEXUS Export)

Tìm dòng:
```python
"version":     "v9.5",
```
Đổi thành:
```python
"version":     "v9.6",
```

Và sửa title trong `plt.suptitle` ở `plot_dashboard` (Cell 14):
Tìm:
```python
plt.suptitle('Algorithm Comparison — VRPTW Solomon RC Benchmarks v9.5',
```
Đổi thành:
```python
plt.suptitle('Algorithm Comparison — VRPTW Solomon RC Benchmarks v9.6',
```
