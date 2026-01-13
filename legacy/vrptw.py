#!/usr/bin/env python
# coding: utf-8
# ============================================================
# Hybrid RL-ALNS for VRPTW  —  Kaggle Notebook v11
# Drop vrptw_v11.py into /kaggle/working/ before running.
# ============================================================

# ── Cell 1 : Install & Imports ───────────────────────────────────────────────
# !pip install numba safetensors scipy -q

import json
import math
import os
import random
import time
import warnings
from typing import Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

warnings.filterwarnings("ignore", category=RuntimeWarning)

# ── import our module (must be in /kaggle/working/) ──────────────────────────
import sys
sys.path.insert(0, "/kaggle/working")

from vrptw_v11 import (
    ALGO_ALNS_BASE,
    ALGO_HYBRID_DDQN,
    ALGO_HYBRID_DDQN_TRANSFER,
    ALGO_HYBRID_FIXED,
    ALGO_HYBRID_RULE,
    ALGO_ORDER,
    ALNSSolver,
    BKS,
    Config,
    HybridDDQNSolver,
    HybridFixedSolver,
    HybridRuleSolver,
    Inst,
    canonical_algo_label,
    load_datasets,
    load_transfer_model,
    normalize_algorithm_frame,
    print_summary_table,
    run_benchmark,
    smoke_test,
    train_transfer_model,
)

DEVICE_STR = "cuda" if __import__("torch").cuda.is_available() else "cpu"
print(f"✅ Device : {DEVICE_STR}")
print(f"✅ vrptw_v11 imported")


# ── Cell 2 : Config ──────────────────────────────────────────────────────────
CFG = Config(
    alns_iterations     = 2000,
    hybrid_iterations   = 2000,
    early_stop_patience = 600,
    n_runs              = 4,
    seed                = 42,
)

OUTPUT_DIR  = CFG.output_dir
RESULT_PATH = os.path.join(OUTPUT_DIR, "benchmark_clean.csv")
RESULT_TRANSFER = os.path.join(OUTPUT_DIR, "benchmark_transfer.csv")

print(f"✅ Config — alns={CFG.alns_iterations}, hybrid={CFG.hybrid_iterations}, "
      f"n_runs={CFG.n_runs}, patience={CFG.early_stop_patience}")


# ── Cell 3 : Load datasets ───────────────────────────────────────────────────
DATASETS = load_datasets(CFG.data_path)
RC1 = DATASETS.get("rc1", [])
RC2 = DATASETS.get("rc2", [])
assert RC1 and RC2, f"No data found at {CFG.data_path}"
print(f"✅ Loaded RC1={len(RC1)} instances, RC2={len(RC2)} instances")


# ── Cell 4 : Smoke test ──────────────────────────────────────────────────────
smoke_cfg = Config(
    alns_iterations     = 400,
    hybrid_iterations   = 600,
    early_stop_patience = 150,
    n_runs              = 1,
)
print(f"\nSmoke test — {RC1[0].name}\n")
smoke_results = smoke_test(RC1[0], smoke_cfg, seed=42)
print("\n✅ Smoke test passed — v11")


# ── Cell 5 : Convergence plot (smoke instance) ───────────────────────────────
def plot_convergence(inst: Inst, cfg: Config, seed: int = 42,
                     save_path: Optional[str] = None) -> None:
    COLORS = {
        ALGO_ALNS_BASE:   "#5f5fae",
        ALGO_HYBRID_RULE: "#72b7b2",
        ALGO_HYBRID_DDQN: "#1d9e75",
    }
    histories = {}
    for algo, SolverCls in [
        (ALGO_ALNS_BASE,   ALNSSolver),
        (ALGO_HYBRID_RULE, HybridRuleSolver),
        (ALGO_HYBRID_DDQN, HybridDDQNSolver),
    ]:
        s = SolverCls(inst, cfg)
        _, hist = s.solve(seed=seed)
        histories[algo] = hist

    fig, ax = plt.subplots(figsize=(9, 4))
    for algo, hist in histories.items():
        ax.plot(hist, label=algo, color=COLORS.get(algo, "#888"), lw=2, alpha=0.9)
    bks = BKS.get(inst.name, {})
    if bks:
        ax.axhline(bks["td"], color="gray", ls="--", lw=1.2, label="BKS distance")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Best Cost Found")
    ax.set_title(f"Convergence — {inst.name}", fontweight="bold")
    ax.legend(); ax.grid(alpha=0.2)
    plt.tight_layout()
    out = save_path or os.path.join(OUTPUT_DIR, f"convergence_{inst.name}.png")
    plt.savefig(out, dpi=120, bbox_inches="tight")
    plt.close()
    print(f"✅ Convergence plot → {out}")


plot_convergence(RC1[0], smoke_cfg, seed=42)


# ── Cell 6 : Phase 1 — Main Benchmark ───────────────────────────────────────
df = run_benchmark(
    instances   = RC1 + RC2,
    algorithms  = [ALGO_ALNS_BASE, ALGO_HYBRID_FIXED,
                   ALGO_HYBRID_RULE, ALGO_HYBRID_DDQN],
    cfg         = CFG,
    result_path = RESULT_PATH,
)
print_summary_table(df)


# ── Cell 7 : Paper table ─────────────────────────────────────────────────────
def print_paper_table(df: pd.DataFrame) -> None:
    df = normalize_algorithm_frame(df)
    summary = (
        df.groupby(["Dataset", "Algorithm"], observed=True)
          .agg(NV=("NV_mean","mean"), NV_std=("NV_std","mean"),
               NV_d=("NV_diff","mean"), TD=("TD_mean","mean"),
               TD_std=("TD_std","mean"), Gap=("Gap%","mean"),
               CV_nv=("NV_cv","mean"), CV_td=("TD_cv","mean"),
               OT=("OnTime","mean"), Time=("Time_s","mean"))
          .round(2).reset_index()
    )
    hdr = (f'{"DS":<4}{"Algorithm":<16}{"NV":>6}{"±":>4}{"vsBKS":>8}'
           f'{"TD":>9}{"±":>6}{"Gap%":>7}{"CV_NV":>6}{"CV_TD":>6}'
           f'{"OT%":>6}{"Time":>7}')
    sep = "─" * len(hdr)
    print("\n" + sep); print(hdr); print(sep)
    prev = ""
    for _, r in summary.iterrows():
        if r["Dataset"] != prev and prev:
            print(sep)
        prev  = r["Dataset"]
        nv_d  = f"{r['NV_d']:+.1f}" if pd.notna(r["NV_d"]) else "—"
        gap   = f"{r['Gap']:+.1f}%" if pd.notna(r["Gap"])   else "—"
        print(f"{r['Dataset']:<4}{r['Algorithm']:<16}"
              f"{r['NV']:>6.1f}{r['NV_std']:>4.1f}{nv_d:>8}"
              f"{r['TD']:>9.1f}{r['TD_std']:>6.1f}{gap:>7}"
              f"{r['CV_nv']:>6.1f}{r['CV_td']:>6.1f}"
              f"{r['OT']:>6.1f}{r['Time']:>6.1f}s")
    print(sep)
    print("CV = std/mean×100%. Negative Gap%: solution beats BKS distance.")


print_paper_table(df)


# ── Cell 8 : Statistical tests ───────────────────────────────────────────────
def wilcoxon_per_instance(df: pd.DataFrame, algo_a: str, algo_b: str,
                           metric: str = "Gap%",
                           dataset: Optional[str] = None) -> Dict:
    df = normalize_algorithm_frame(df)
    algo_a, algo_b = canonical_algo_label(algo_a), canonical_algo_label(algo_b)
    sub = df if dataset is None else df[df["Dataset"] == dataset]
    a = sub[sub["Algorithm"] == algo_a][metric].dropna().values
    b = sub[sub["Algorithm"] == algo_b][metric].dropna().values
    n = min(len(a), len(b)); a, b = a[:n], b[:n]
    if n < 3:
        return {"stat": None, "p": None, "sig": False, "n": n}
    stat, p = scipy_stats.wilcoxon(a, b, alternative="two-sided")
    return {"stat": round(stat, 3), "p": round(p, 4), "sig": p < 0.05,
            "n": n, "better": algo_a if a.mean() < b.mean() else algo_b}


def wilcoxon_per_run(df: pd.DataFrame, algo_a: str, algo_b: str,
                     dataset: Optional[str] = None) -> Dict:
    """Paired test on raw per-run costs. n = instances × n_runs."""
    df = normalize_algorithm_frame(df)
    algo_a, algo_b = canonical_algo_label(algo_a), canonical_algo_label(algo_b)
    sub    = df if dataset is None else df[df["Dataset"] == dataset]
    a_rows = sub[sub["Algorithm"] == algo_a]
    b_rows = sub[sub["Algorithm"] == algo_b]
    costs_a: List[float] = []; costs_b: List[float] = []
    common  = set(a_rows["Instance"]) & set(b_rows["Instance"])
    for inst_name in sorted(common):
        ra = a_rows[a_rows["Instance"] == inst_name]
        rb = b_rows[b_rows["Instance"] == inst_name]
        if ra.empty or rb.empty:
            continue
        if "raw_costs" in ra.columns:
            ac = [float(x) for x in ra["raw_costs"].values[0].split(";")]
            bc = [float(x) for x in rb["raw_costs"].values[0].split(";")]
            n  = min(len(ac), len(bc))
            costs_a.extend(ac[:n]); costs_b.extend(bc[:n])
        else:
            costs_a.append(float(ra["TD_mean"].values[0]))
            costs_b.append(float(rb["TD_mean"].values[0]))
    ca = np.array(costs_a); cb = np.array(costs_b); n = len(ca)
    if n < 6:
        return {"stat": None, "p": None, "sig": False, "n": n, "method": "per_run"}
    diff = ca - cb
    if (diff != 0).sum() < 6:
        return {"stat": None, "p": None, "sig": False, "n": n, "method": "per_run"}
    stat, p = scipy_stats.wilcoxon(ca, cb, alternative="two-sided")
    effect  = (cb.mean() - ca.mean()) / ca.mean() * 100
    return {"stat": round(stat, 3), "p": round(p, 4), "sig": p < 0.05, "n": n,
            "better": algo_a if ca.mean() < cb.mean() else algo_b,
            "effect_pct": round(effect, 3), "method": "per_run"}


def lexicographic_per_run(df: pd.DataFrame, algo_a: str, algo_b: str,
                           dataset: Optional[str] = None) -> Dict:
    df = normalize_algorithm_frame(df)
    algo_a, algo_b = canonical_algo_label(algo_a), canonical_algo_label(algo_b)
    sub    = df if dataset is None else df[df["Dataset"] == dataset]
    a_rows = sub[sub["Algorithm"] == algo_a]
    b_rows = sub[sub["Algorithm"] == algo_b]
    wins_a = wins_b = ties = 0
    common = set(a_rows["Instance"]) & set(b_rows["Instance"])
    for inst_name in sorted(common):
        ra = a_rows[a_rows["Instance"] == inst_name]
        rb = b_rows[b_rows["Instance"] == inst_name]
        if ra.empty or rb.empty:
            continue
        if "raw_nv" in ra.columns and "raw_costs" in ra.columns:
            an = [int(x)   for x in ra["raw_nv"].values[0].split(";")]
            ac = [float(x) for x in ra["raw_costs"].values[0].split(";")]
            bn = [int(x)   for x in rb["raw_nv"].values[0].split(";")]
            bc = [float(x) for x in rb["raw_costs"].values[0].split(";")]
            n  = min(len(an), len(ac), len(bn), len(bc))
            seq_a = list(zip(an[:n], ac[:n])); seq_b = list(zip(bn[:n], bc[:n]))
        else:
            seq_a = [(float(ra["NV_mean"].values[0]), float(ra["TD_mean"].values[0]))]
            seq_b = [(float(rb["NV_mean"].values[0]), float(rb["TD_mean"].values[0]))]
        for (nv_a, ca), (nv_b, cb) in zip(seq_a, seq_b):
            if   nv_a < nv_b or (nv_a == nv_b and ca + 1e-9 < cb): wins_a += 1
            elif nv_b < nv_a or (nv_a == nv_b and cb + 1e-9 < ca): wins_b += 1
            else: ties += 1
    n = wins_a + wins_b + ties; decisive = wins_a + wins_b
    if decisive == 0:
        return {"n": n, "wins_a": wins_a, "wins_b": wins_b,
                "ties": ties, "p": None, "sig": False, "better": "Tie"}
    p = scipy_stats.binomtest(wins_a, decisive, 0.5,
                              alternative="two-sided").pvalue
    better = (algo_a if wins_a > wins_b else
              algo_b if wins_b > wins_a else "Tie")
    return {"n": n, "decisive": decisive, "wins_a": wins_a, "wins_b": wins_b,
            "ties": ties, "p": round(p, 4), "sig": p < 0.05, "better": better}


def print_stats_table(df: pd.DataFrame) -> None:
    df = normalize_algorithm_frame(df)
    pairs = [
        (ALGO_HYBRID_RULE,        ALGO_HYBRID_FIXED),
        (ALGO_HYBRID_RULE,        ALGO_ALNS_BASE),
        (ALGO_HYBRID_DDQN,        ALGO_HYBRID_RULE),
        (ALGO_HYBRID_DDQN,        ALGO_HYBRID_FIXED),
        (ALGO_HYBRID_DDQN,        ALGO_ALNS_BASE),
        (ALGO_HYBRID_DDQN_TRANSFER, ALGO_HYBRID_RULE),
        (ALGO_HYBRID_DDQN_TRANSFER, ALGO_HYBRID_FIXED),
        (ALGO_HYBRID_DDQN_TRANSFER, ALGO_ALNS_BASE),
    ]
    avail = set(df["Algorithm"].dropna().unique())

    print("\n── Wilcoxon signed-rank — per-instance-mean (n=instances) ──")
    print(f'{"Comparison":<30}{"DS":<5}{"Metric":<8}{"W":>7}{"p":>9}{"Sig":>5}{"Better":>14}')
    print("─" * 72)
    for algo_a, algo_b in pairs:
        if algo_a not in avail or algo_b not in avail:
            continue
        for ds in ["RC1", "RC2"]:
            for metric in ["Gap%", "NV_mean"]:
                r = wilcoxon_per_instance(df, algo_a, algo_b, metric, ds)
                if r["stat"] is None:
                    continue
                sig = "✅" if r["sig"] else "—"
                print(f'  {algo_a} vs {algo_b:<10}  {ds:<5}{metric:<8}'
                      f'{r["stat"]:>7.1f}{r["p"]:>9.4f}{sig:>5}{r["better"]:>14}')
    print("─" * 72); print("✅ = p < 0.05")

    print("\n── Wilcoxon signed-rank — per-run paired (n=instances×n_runs) ──")
    print(f'{"Comparison":<30}{"DS":<5}{"n":>5}{"W":>9}{"p":>9}'
          f'{"Sig":>5}{"Effect%":>9}{"Better":>14}')
    print("─" * 80)
    for algo_a, algo_b in pairs:
        if algo_a not in avail or algo_b not in avail:
            continue
        for ds in ["RC1", "RC2"]:
            r = wilcoxon_per_run(df, algo_a, algo_b, ds)
            if r["stat"] is None:
                print(f'  {algo_a} vs {algo_b:<10}  {ds:<5}'
                      f'{"n="+str(r["n"]):>5}  insufficient data')
                continue
            sig = "✅" if r["sig"] else "—"
            print(f'  {algo_a} vs {algo_b:<10}  {ds:<5}{r["n"]:>5}'
                  f'{r["stat"]:>9.1f}{r["p"]:>9.4f}{sig:>5}'
                  f'{r["effect_pct"]:>+9.3f}%{r["better"]:>14}')
    print("─" * 80)
    print("Effect% = mean cost improvement of 'Better' over other.")
    try:
        sample = df[df["Algorithm"] == ALGO_ALNS_BASE]
        if not sample.empty and "raw_costs" in sample.columns:
            ex = sample.iloc[0]["raw_costs"].count(";") + 1
            print(f"✅ = p < 0.05  |  per-run n = {len(sample)} instances "
                  f"× {ex} runs = {len(sample)*ex} pairs/family")
    except Exception:
        pass

    print("\n── Lexicographic paired wins (NV → cost) ──")
    print(f'{"Comparison":<30}{"DS":<5}{"n":>5}{"A_wins":>8}'
          f'{"B_wins":>8}{"Ties":>6}{"p":>9}{"Sig":>5}{"Better":>14}')
    print("─" * 92)
    for algo_a, algo_b in pairs:
        if algo_a not in avail or algo_b not in avail:
            continue
        for ds in ["RC1", "RC2"]:
            r   = lexicographic_per_run(df, algo_a, algo_b, ds)
            p_t = f"{r['p']:.4f}" if r["p"] is not None else "   n/a"
            sig = "✅" if r["sig"] else "—"
            print(f'  {algo_a} vs {algo_b:<10}  {ds:<5}{r["n"]:>5}'
                  f'{r["wins_a"]:>8}{r["wins_b"]:>8}{r["ties"]:>6}'
                  f'{p_t:>9}{sig:>5}{r["better"]:>14}')
    print("─" * 92)
    print("Lexicographic: fewer vehicles first, then lower cost.")


print_stats_table(df)


# ── Cell 9 : Dashboard plot ──────────────────────────────────────────────────
COLORS = {
    ALGO_ALNS_BASE:            "#5f5fae",
    ALGO_HYBRID_FIXED:         "#4c78a8",
    ALGO_HYBRID_RULE:          "#72b7b2",
    ALGO_HYBRID_DDQN:          "#1d9e75",
    ALGO_HYBRID_DDQN_TRANSFER: "#e67e22",
}


def plot_dashboard(df: pd.DataFrame, out_path: Optional[str] = None) -> None:
    df = normalize_algorithm_frame(df)
    metrics = [
        ("Gap%",    "Distance Gap vs BKS (%)", "↓ lower is better"),
        ("NV_mean", "Vehicles Used (avg)",      "↓ lower is better"),
        ("TD_cv",   "TD Consistency (CV %)",    "↓ lower = more stable"),
    ]
    algos = [a for a in ALGO_ORDER if a in df["Algorithm"].values and a in COLORS]
    fig, axes = plt.subplots(2, 3, figsize=(18, 8))
    for ri, ds in enumerate(["RC1", "RC2"]):
        for ci, (met, label, note) in enumerate(metrics):
            ax  = axes[ri][ci]
            sub = df[df["Dataset"] == ds]
            insts = sub["Instance"].unique()
            x = np.arange(len(insts)); w = 0.8 / max(len(algos), 1)
            for ji, algo in enumerate(algos):
                vals = [sub[(sub["Algorithm"] == algo)
                            & (sub["Instance"] == i)][met].mean()
                        for i in insts]
                ax.bar(x + ji * w, vals, w, label=algo,
                       color=COLORS.get(algo, "#888"), alpha=0.85,
                       edgecolor="white")
            ax.set_xticks(x + w * (len(algos) - 1) / 2)
            ax.set_xticklabels([i[-3:] for i in insts], fontsize=8)
            ax.set_title(f"{ds} — {label}\n({note})", fontsize=9, fontweight="bold")
            ax.set_ylabel(met, fontsize=8); ax.grid(axis="y", alpha=0.3)
            if ri == 0 and ci == 0:
                ax.legend(fontsize=8)
    plt.suptitle("Algorithm Comparison — VRPTW Solomon RC Benchmarks v11",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    out = out_path or os.path.join(OUTPUT_DIR, "dashboard.png")
    plt.savefig(out, dpi=150, bbox_inches="tight"); plt.close()
    print(f"✅ dashboard.png → {out}")


plot_dashboard(df)


# ── Cell 10 : Phase 2 — Transfer learning ───────────────────────────────────
# Loads cached weights if available; trains from scratch otherwise.
transfer_weights = load_transfer_model(CFG)
if transfer_weights is None:
    transfer_weights = train_transfer_model(RC1, CFG, seed=CFG.seed)

df_tr = run_benchmark(
    instances        = RC2,
    algorithms       = [ALGO_HYBRID_DDQN_TRANSFER],
    cfg              = CFG,
    result_path      = RESULT_TRANSFER,
    transfer_weights = transfer_weights,
)

df_all = pd.concat([df, df_tr], ignore_index=True)
print("\n── RC2 full comparison (including transfer) ──")
print_paper_table(df_all[df_all["Dataset"] == "RC2"])


# ── Cell 11 : Transfer scatter plot ─────────────────────────────────────────
def plot_transfer_comparison(df_combined: pd.DataFrame,
                             out_path: Optional[str] = None) -> None:
    df_combined = normalize_algorithm_frame(df_combined)
    rc2 = df_combined[df_combined["Dataset"] == "RC2"]
    avail = set(rc2["Algorithm"].dropna().unique())
    candidates = [ALGO_HYBRID_RULE, ALGO_HYBRID_FIXED, ALGO_ALNS_BASE]
    baselines   = [a for a in candidates if a in avail]
    if not baselines:
        print("⚠️  No non-RL baseline results to compare.")
        return
    baseline = min(baselines,
                   key=lambda a: rc2[rc2["Algorithm"] == a]["Gap%"].mean())
    base = (rc2[rc2["Algorithm"] == baseline][["Instance", "Gap%"]]
               .set_index("Instance"))
    star = (rc2[rc2["Algorithm"] == ALGO_HYBRID_DDQN_TRANSFER][["Instance", "Gap%"]]
               .set_index("Instance"))
    common = base.index.intersection(star.index)
    if common.empty:
        print(f"⚠️  No {ALGO_HYBRID_DDQN_TRANSFER} results to plot yet.")
        return
    x = base.loc[common, "Gap%"].values
    y = star.loc[common, "Gap%"].values
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(x, y, s=90, color=COLORS[ALGO_HYBRID_DDQN_TRANSFER], zorder=3)
    for inst, xi, yi in zip(common, x, y):
        ax.annotate(inst[-3:], (xi, yi), textcoords="offset points",
                    xytext=(4, 4), fontsize=8)
    lim = [min(x.min(), y.min()) - 1, max(x.max(), y.max()) + 1]
    ax.plot(lim, lim, "k--", lw=1, alpha=0.5, label="y=x (same)")
    ax.axhline(0, color="gray", lw=0.8, alpha=0.5)
    ax.axvline(0, color="gray", lw=0.8, alpha=0.5)
    ax.set_xlabel(f"{baseline} Gap% (RC2)")
    ax.set_ylabel(f"{ALGO_HYBRID_DDQN_TRANSFER} Gap% (RC2, zero-shot)")
    ax.set_title(f"Transfer: {ALGO_HYBRID_DDQN_TRANSFER} vs {baseline} on RC2",
                 fontweight="bold")
    ax.legend(fontsize=8); ax.grid(alpha=0.25)
    plt.tight_layout()
    out = out_path or os.path.join(OUTPUT_DIR, "transfer_comparison.png")
    plt.savefig(out, dpi=120, bbox_inches="tight"); plt.close()
    print(f"✅ Transfer comparison → {out}")


plot_transfer_comparison(df_all)


# ── Cell 12 : Full stats (with transfer) ────────────────────────────────────
print("\n" + "=" * 60 + "\nFULL STATISTICAL TESTS (all algorithms)")
print_stats_table(df_all)


# ── Cell 13 : Per-instance appendix table ───────────────────────────────────
def print_per_instance_table(df: pd.DataFrame) -> None:
    df = normalize_algorithm_frame(df)
    for ds in ["RC1", "RC2"]:
        sub = df[df["Dataset"] == ds]
        if sub.empty:
            continue
        pivot = sub.pivot_table(
            index="Instance", columns="Algorithm",
            values=["NV_mean", "TD_mean", "Gap%", "NV_cv", "TD_cv"],
            aggfunc="mean",
        ).round(2)
        print(f"\n── {ds} per-instance detail ──")
        print(pivot.to_string())


print_per_instance_table(df_all)


# ── Cell 14 : Route visualisation ───────────────────────────────────────────
def plot_routes(plan, save: bool = True) -> None:
    RCOLS = [
        "#E63946","#2A9D8F","#E9C46A","#264653","#F4A261",
        "#A8DADC","#457B9D","#6A4C93","#F72585","#4CC9F0",
        "#80B918","#FF9F1C","#8338EC","#3A86FF","#CBFF8C",
    ]
    inst = plan.inst
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.scatter(*inst.coords[0], s=220, c="black", marker="s", zorder=5)
    ax.annotate("DEPOT", inst.coords[0], fontsize=8,
                ha="center", va="bottom", fontweight="bold")
    for i, route in enumerate(plan.routes):
        col   = RCOLS[i % len(RCOLS)]
        stops = [0] + route + [0]
        xs    = [inst.coords[n, 0] for n in stops]
        ys    = [inst.coords[n, 1] for n in stops]
        ax.plot(xs, ys, "-o", color=col, lw=1.5, ms=4, alpha=0.8,
                label=f"V{i+1}")
    td, nv = plan.gap()
    g = f" | BKS TD {td:+.1f}% NV {nv:+d}" if td is not None else ""
    ax.set_title(f"{plan.algo} — {inst.name}  nv={plan.nv}  "
                 f"cost={plan.cost:.1f}{g}", fontweight="bold")
    ax.legend(fontsize=6, ncol=3); ax.grid(alpha=0.2)
    plt.tight_layout()
    if save:
        out = os.path.join(OUTPUT_DIR, f"routes_{plan.algo}_{inst.name}.png")
        plt.savefig(out, dpi=120, bbox_inches="tight"); plt.close()
        print(f"✅ Route plot → {out}")
    else:
        plt.show()


for algo_name, SolverCls in [
    (ALGO_ALNS_BASE,   ALNSSolver),
    (ALGO_HYBRID_RULE, HybridRuleSolver),
    (ALGO_HYBRID_DDQN, HybridDDQNSolver),
]:
    s = SolverCls(RC1[0], CFG)
    plan, _ = s.solve(seed=CFG.seed)
    plot_routes(plan)


# ── Cell 15 : NEXUS demo export ──────────────────────────────────────────────
MAP_INST = RC1[0]
print(f"\nExporting NEXUS demo for {MAP_INST.name} ...")
_t0 = time.time()


def _solve_export(inst, SolverCls, label: str) -> Dict:
    s = SolverCls(inst, CFG)
    plan, hist = s.solve(seed=CFG.seed)
    routes_out = []
    for ri, route in enumerate(plan.routes):
        if not route:
            continue
        d = float(inst.dist[0, route[0]])
        for k in range(len(route) - 1):
            d += float(inst.dist[route[k], route[k + 1]])
        d += float(inst.dist[route[-1], 0])
        routes_out.append({"id": ri + 1, "nodes": [int(n) for n in route],
                            "dist": round(d, 2)})
    bks_td = BKS[inst.name]["td"]
    total  = sum(r["dist"] for r in routes_out)
    gap    = round((total - bks_td) / bks_td * 100, 2)
    print(f"  {label:12s}: nv={len(routes_out)}, td={total:.1f}, gap={gap:+.1f}%")
    return {"algo": label, "nv": len(routes_out), "td": round(total, 2),
            "gap_pct": gap, "bks_nv": BKS[inst.name]["nv"], "bks_td": bks_td,
            "routes": routes_out,
            "history": [round(float(c), 2) for c in hist] if hist else []}


alns_exp   = _solve_export(MAP_INST, ALNSSolver,      ALGO_ALNS_BASE)
rule_exp   = _solve_export(MAP_INST, HybridRuleSolver, ALGO_HYBRID_RULE)
ddqn_exp   = _solve_export(MAP_INST, HybridDDQNSolver, ALGO_HYBRID_DDQN)

# op_counts from the last DDQN solve for the matrix
_solver = HybridDDQNSolver(MAP_INST, CFG)
_solver.solve(seed=CFG.seed)
N_D_EXP, N_R_EXP = 6, 4
op_matrix = [
    [_solver.op_counts.get((di, ri), 0) for ri in range(N_R_EXP)]
    for di in range(N_D_EXP)
]

nodes_exp = [
    {"id": int(i), "x": float(MAP_INST.coords[i, 0]),
     "y": float(MAP_INST.coords[i, 1]),
     "demand": float(MAP_INST.demands[i]),
     "ready":  float(MAP_INST.ready_times[i]),
     "due":    float(MAP_INST.due_times[i]),
     "svc":    float(MAP_INST.service_times[i])}
    for i in range(MAP_INST.n + 1)
]

summary_exp = [
    {"instance": str(r["Instance"]), "algo": str(r["Algorithm"]),
     "nv":      float(r["NV_mean"]),  "td":  float(r["TD_mean"]),
     "gap_pct": float(r["Gap%"])  if pd.notna(r.get("Gap%"))  else 0.0,
     "cv_nv":   float(r["NV_cv"]), "cv_td": float(r["TD_cv"]),
     "time_s":  float(r["Time_s"])}
    for _, r in df.iterrows()
]

transfer_exp = []
if "df_tr" in dir() and not df_tr.empty:
    transfer_exp = [
        {"instance": str(r["Instance"]), "algo": str(r["Algorithm"]),
         "nv":      float(r["NV_mean"]), "td":  float(r["TD_mean"]),
         "gap_pct": float(r["Gap%"]) if pd.notna(r.get("Gap%")) else 0.0}
        for _, r in df_tr.iterrows()
    ]

OUT = {
    "meta": {
        "instance":    MAP_INST.name,
        "n_customers": int(MAP_INST.n),
        "capacity":    float(MAP_INST.capacity),
        "horizon":     float(MAP_INST.horizon),
        "dataset":     "Solomon RC1+RC2",
        "version":     "v11",
        "algo_desc": {
            ALGO_ALNS_BASE:   "Adaptive Large Neighbourhood Search baseline",
            ALGO_HYBRID_FIXED:"Shared hybrid stack, controller frozen (pure bandit op)",
            ALGO_HYBRID_RULE: "Shared hybrid stack, hand-coded rule scheduler",
            ALGO_HYBRID_DDQN: "Hierarchical DDQN: plateau mode + operator controllers",
            ALGO_HYBRID_DDQN_TRANSFER:
                "Zero-shot transfer of learned hybrid from RC1 to RC2",
        },
    },
    "nodes":        nodes_exp,
    "alns":         alns_exp,
    "alnspp":       rule_exp,
    "rl_alns":      ddqn_exp,
    "op_matrix":    op_matrix,
    "destroy_ops":  ["Random","Worst","Shaw","Route","TW-Urgent","RouteElim"],
    "repair_ops":   ["Greedy","Regret-2","Regret-3","TW-Greedy"],
    "summary":      summary_exp,
    "transfer":     transfer_exp,
}

out_json = os.path.join(OUTPUT_DIR, "nexus_demo.json")
with open(out_json, "w") as f:
    json.dump(OUT, f, separators=(",", ":"))

size_kb = os.path.getsize(out_json) / 1024
print(f"\n✅ nexus_demo.json → {out_json}  ({size_kb:.1f} KB)")
print(f"   Total export time: {time.time() - _t0:.1f}s")
print("   Drop nexus_demo.json into nexus_v2.html to view")
print("\n✅ All cells complete.")
