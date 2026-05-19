from __future__ import annotations
import time
import random
import os
import torch
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional, Iterable
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from .config import Config, BKS, canonical_algo_label, normalize_algorithm_frame, ALGO_ORTOOLS, ALGO_ALNS_BASE, ALGO_HYBRID_FIXED, ALGO_HYBRID_RULE, ALGO_HYBRID_DDQN, ALGO_HYBRID_DDQN_TRANSFER, ALGO_HYBRID_DDQN_TRANSFER_RC2, ALGO_HYBRID_DDQN_TRANSFER_DR
from .core import Inst, Plan
from .generators import SyntheticVRPTWGenerator
from .solvers import ALNSSolver, HybridFixedSolver, HybridRuleSolver, HybridDDQNSolver, run_ortools
from .operators import op_shaw, op_regret_2
from .rl import EliteArchive, DEVICE

try:
    from safetensors.torch import load_file as _st_load, save_file as _st_save
    SAFETENSORS_OK = True
except Exception:
    SAFETENSORS_OK = False
    _st_load = _st_save = None

def _save_weights(weights: Dict, stem: str) -> None:
    if SAFETENSORS_OK and _st_save is not None:
        path = stem + ".safetensors"
        _st_save(weights, path)
    else:
        path = stem + ".pt"
        torch.save({k: v.cpu() for k, v in weights.items()}, path)
    print(f"Weights saved → {path}")


def _load_weights(stem: str) -> Optional[Dict]:
    for suffix, loader in (
        (".safetensors", _st_load if SAFETENSORS_OK else None),
        (".pt",          lambda f: torch.load(f, map_location="cpu")),
    ):
        p = stem + suffix
        if os.path.exists(p) and loader is not None:
            print(f"Weights loaded → {p}")
            return loader(p)
    return None


def run_instance(inst: Inst, algo: str, cfg: Config, seed: int,
                 transfer_weights: Optional[Dict] = None,
                 init_plan: Optional[Plan] = None) -> Tuple[Dict, Optional[Plan]]:
    start = time.time()
    algo  = canonical_algo_label(algo)
    plan: Optional[Plan] = None
    if algo == ALGO_ORTOOLS:
        plan, elapsed = run_ortools(inst, cfg)
        if plan is None:
            return {"algo": ALGO_ORTOOLS, "nv": None, "cost": None,
                    "time": time.time() - start, "td_gap": None, "nv_diff": None,
                    "on_time": None, "hist": []}, None
        history = [plan.cost]
    elif algo == ALGO_ALNS_BASE:
        plan, history = ALNSSolver(inst, cfg).solve(seed=seed, init=init_plan)
    elif algo == ALGO_HYBRID_FIXED:
        plan, history = HybridFixedSolver(inst, cfg).solve(seed=seed, init=init_plan)
    elif algo == ALGO_HYBRID_RULE:
        plan, history = HybridRuleSolver(inst, cfg).solve(seed=seed, init=init_plan)
    elif algo == ALGO_HYBRID_DDQN:
        plan, history = HybridDDQNSolver(inst, cfg).solve(seed=seed, init=init_plan)
    elif algo in (ALGO_HYBRID_DDQN_TRANSFER, ALGO_HYBRID_DDQN_TRANSFER_RC2,
                  ALGO_HYBRID_DDQN_TRANSFER_DR):
        solver = HybridDDQNSolver(inst, cfg)
        if transfer_weights is not None:
            solver.load_weights(transfer_weights)
        plan, history = solver.solve(seed=seed, frozen=True, init=init_plan)
        plan.algo = algo
    else:
        raise ValueError(f"Unsupported algorithm: {algo}")
    bks = BKS.get(inst.name)
    return {
        "algo":    plan.algo,
        "nv":      plan.nv,
        "cost":    plan.cost,
        "time":    time.time() - start,
        "td_gap":  (plan.cost - bks["td"]) / bks["td"] * 100 if bks else None,
        "nv_diff": plan.nv - bks["nv"] if bks else None,
        "on_time": plan.on_time_rate,
        "hist":    history,
    }, plan


# ---------------------------------------------------------------------------
# Top-level worker  — must be module-level for ProcessPoolExecutor pickling
# ---------------------------------------------------------------------------
def _benchmark_worker(packed: Tuple) -> Tuple[Dict, Optional[Plan]]:
    inst, algo, cfg, seed, transfer_weights, init_plan = packed
    return run_instance(inst, algo, cfg, seed, transfer_weights, init_plan)


def _diversified_init(run_idx: int, inst: Inst, archive: EliteArchive,
                      cfg: Config) -> Optional[Plan]:
    """
    run 0 → archive best       (exploitation of known-good solution)
    run 1 → shaw-perturbed     (exploration from good neighbourhood)
    run 2 → fresh greedy build (independent trajectory)
    Avoids 3 seeds converging to the same local optimum.
    """
    base = archive.best(inst.name)
    if run_idx == 0:
        return base
    if run_idx == 1 and base is not None:
        random.seed(cfg.seed + 7919); np.random.seed(cfg.seed + 7919)
        size = max(4, int(0.20 * inst.n))
        dest, removed = op_shaw(base.copy(), size)
        cand = op_regret_2(dest, removed)
        return cand if (cand.feasible and cand.nv <= base.nv + 1) else base
    return None  # run_instance will call build_greedy


# ---------------------------------------------------------------------------
# run_benchmark  (ProcessPoolExecutor for true GIL bypass)
# ---------------------------------------------------------------------------
def run_benchmark(
    instances: Iterable[Inst],
    algorithms: List[str],
    cfg: Config,
    result_path:      Optional[str]  = None,
    transfer_weights: Optional[Dict] = None,
    archive:          Optional[EliteArchive] = None,
    checkpoint_path:  Optional[str]  = None,
) -> pd.DataFrame:
    cfg.validate()
    instances   = list(instances)
    result_path = result_path or os.path.join(cfg.output_dir, "benchmark_clean.csv")
    ckpt_path   = checkpoint_path or os.path.join(cfg.output_dir, "benchmark_checkpoint.csv")
    if archive is None:
        archive = EliteArchive(k=cfg.elite_archive_k)

    rows:      List[Dict] = []
    completed: set        = set()
    if os.path.exists(ckpt_path):
        try:
            ckpt_df = pd.read_csv(ckpt_path)
            rows    = ckpt_df.to_dict("records")
            for row in rows:
                completed.add((row["Instance"], canonical_algo_label(str(row["Algorithm"]))))
            print(f"Resumed from checkpoint: {len(completed)} combo(s) already done")
        except Exception as exc:
            print(f"Checkpoint read failed ({exc}), starting fresh")

    total    = len(instances) * len(algorithms)
    n_workers= min(cfg.n_runs, max(1, os.cpu_count() // 2))
    print(f"Total: {total} combos × {cfg.n_runs} runs  |  wall limit: {cfg.max_wall_hours:.1f}h")
    print(f"Parallel workers: {n_workers}  (ProcessPool — true GIL bypass)")
    print("=" * 64)
    wall_start = time.time()

    for inst_idx, inst in enumerate(instances):
        dataset = "RC1" if inst.name[2] == "1" else "RC2"
        for algo in algorithms:
            algo_label = canonical_algo_label(algo)
            if (inst.name, algo_label) in completed:
                print(f"  [SKIP] {inst.name} {algo_label}")
                continue
            elapsed_h = (time.time() - wall_start) / 3600
            if elapsed_h >= cfg.max_wall_hours:
                print(f"\n⚠️  Wall-clock limit {cfg.max_wall_hours:.1f}h — stopping early.")
                pd.DataFrame(rows).to_csv(ckpt_path, index=False)
                return normalize_algorithm_frame(pd.DataFrame(rows))

            print(f"\n[{inst.name}] {algo_label}")
            nv_v, cost_v, time_v, gap_v, nvd_v, ot_v = [], [], [], [], [], []
            n_runs_eff = 1 if algo_label == ALGO_ORTOOLS else cfg.n_runs

            worker_args = [
                (inst, algo_label, cfg, cfg.seed + i,
                 transfer_weights, _diversified_init(i, inst, archive, cfg))
                for i in range(n_runs_eff)
            ]
            _n_workers = 1 if algo_label == ALGO_ORTOOLS else n_workers
            
            # --- THE SPAWN FIX ---
            ctx = mp.get_context('spawn')
            with ProcessPoolExecutor(max_workers=_n_workers, mp_context=ctx) as ex:
                run_results = list(ex.map(_benchmark_worker, worker_args))
                
            for i, (res, plan) in enumerate(run_results):
                if plan is not None:
                    archive.update(plan)
                time_v.append(res["time"])
                elapsed_h = (time.time() - wall_start) / 3600
                if res["nv"] is not None:
                    nv_v.append(res["nv"]); cost_v.append(res["cost"])
                    gap_v.append(res["td_gap"]); nvd_v.append(res["nv_diff"])
                    ot_v.append(res["on_time"])
                    print(f"  run {i+1}/{n_runs_eff}: nv={res['nv']} cost={res['cost']:.1f} "
                          f"({res['time']:.1f}s) | wall {elapsed_h:.2f}h")
                else:
                    print(f"  run {i+1}/{n_runs_eff}: FAILED ({res['time']:.1f}s)")

            if not nv_v:
                continue

            bks = BKS.get(inst.name)
            nv_inflated = (bks is not None
                           and float(np.mean(nv_v)) > bks["nv"] + 0.4
                           and gap_v[0] is not None
                           and float(np.mean(gap_v)) < 0)
            if nv_inflated:
                print(f"  ⚠️  NV_mean={np.mean(nv_v):.1f} > BKS_NV={bks['nv']} "
                      f"— Gap% comparison misleading (extra vehicle reduces TD)")

            row = {
                "Dataset":     dataset,
                "Instance":    inst.name,
                "Algorithm":   run_results[-1][0]["algo"],
                "NV_mean":     round(float(np.mean(nv_v)),  2),
                "NV_std":      round(float(np.std(nv_v)),   2),
                "NV_diff":     round(float(np.mean(nvd_v)), 2) if nvd_v[0] is not None else None,
                "TD_mean":     round(float(np.mean(cost_v)),2),
                "TD_std":      round(float(np.std(cost_v)), 2),
                "Gap%":        round(float(np.mean(gap_v)), 2) if gap_v[0] is not None else None,
                "OnTime":      round(float(np.mean(ot_v)) * 100, 1),
                "Time_s":      round(float(np.mean(time_v)), 1),
                "NV_cv":       round(float(np.std(nv_v))   / max(float(np.mean(nv_v)),   1) * 100, 2),
                "TD_cv":       round(float(np.std(cost_v)) / max(float(np.mean(cost_v)), 1) * 100, 2),
                "NV_inflated": nv_inflated,
                "raw_costs":   ";".join(f"{c:.4f}" for c in cost_v),
                "raw_nv":      ";".join(str(n) for n in nv_v),
            }
            rows.append(row)
            completed.add((inst.name, algo_label))
            gap_text = f"{row['Gap%']:+.1f}%" if row["Gap%"] is not None else "--"
            print(f"  -> nv={row['NV_mean']:.1f}±{row['NV_std']:.1f}  "
                  f"td={row['TD_mean']:.1f}±{row['TD_std']:.1f}  gap={gap_text}")

        if (inst_idx + 1) % 4 == 0:
            pd.DataFrame(rows).to_csv(ckpt_path, index=False)
            elapsed_h = (time.time() - wall_start) / 3600
            print(f"\n  ✓ Checkpoint ({inst_idx+1}/{len(instances)} inst, "
                  f"{elapsed_h:.2f}h) → {ckpt_path}")

    df = normalize_algorithm_frame(pd.DataFrame(rows))
    df.to_csv(result_path, index=False)
    print(f"\nBenchmark complete in {(time.time()-wall_start)/3600:.2f}h → {result_path}")
    return df


# ---------------------------------------------------------------------------
# Summary table  (with completeness + NV-inflation guards)
# ---------------------------------------------------------------------------
def print_summary_table(df: pd.DataFrame) -> None:
    df = normalize_algorithm_frame(df)

    # Completeness check
    expected = {"RC1": 8, "RC2": 8}
    for ds, exp_n in expected.items():
        for algo in df[df["Dataset"] == ds]["Algorithm"].dropna().unique():
            n = len(df[(df["Dataset"] == ds) & (df["Algorithm"] == algo)])
            if n < exp_n:
                print(f"  ⚠️  {ds}/{algo}: {n}/{exp_n} instances — summary is PARTIAL")

    # NV-inflation warning
    if "NV_inflated" in df.columns:
        flagged = df[df["NV_inflated"] == True][["Instance", "Algorithm", "Gap%", "NV_mean"]]
        for _, r in flagged.iterrows():
            print(f"  ⚠️  {r['Instance']} {r['Algorithm']}: Gap%={r['Gap%']:+.1f}% "
                  f"with NV={r['NV_mean']:.1f} > BKS_NV — not a fair comparison")

    summary = (
        df.groupby(["Dataset", "Algorithm"], observed=True)
        .agg(NV=("NV_mean","mean"), NV_std=("NV_std","mean"), NV_diff=("NV_diff","mean"),
             TD=("TD_mean","mean"), TD_std=("TD_std","mean"),
             Gap=("Gap%","mean"), OnTime=("OnTime","mean"), Time=("Time_s","mean"))
        .round(2).reset_index()
    )
    print("\n" + "-" * 96)
    print(f"{'DS':<4}{'Algorithm':<28}{'NV':>6}{'+/-':>6}{'vsBKS':>8}"
          f"{'TD':>10}{'+/-':>8}{'Gap%':>8}{'OT%':>7}{'Time':>8}")
    print("-" * 96)
    for _, row in summary.iterrows():
        gap     = f"{row['Gap']:+.2f}%"    if pd.notna(row["Gap"])     else "--"
        nv_diff = f"{row['NV_diff']:+.2f}" if pd.notna(row["NV_diff"]) else "--"
        print(f"{row['Dataset']:<4}{row['Algorithm']:<28}"
              f"{row['NV']:>6.2f}{row['NV_std']:>6.2f}{nv_diff:>8}"
              f"{row['TD']:>10.2f}{row['TD_std']:>8.2f}{gap:>8}"
              f"{row['OnTime']:>7.1f}{row['Time']:>7.1f}s")
    print("-" * 96)


# ---------------------------------------------------------------------------
# Transfer / domain randomization
# ---------------------------------------------------------------------------
def train_transfer_model(instances: List[Inst], cfg: Config,
                         seed: int = 42, label: str = "RC1") -> Dict:
    print(f"Training transfer model on {label} ({len(instances)} instances)...")
    if not instances:
        raise ValueError("No source instances provided.")
    weights = None
    for epoch in range(cfg.transfer_epochs):
        order = list(instances)
        if cfg.transfer_shuffle:
            random.Random(seed + epoch).shuffle(order)
        print(f"  Epoch {epoch + 1}/{cfg.transfer_epochs}")
        for idx, inst in enumerate(order):
            solver = HybridDDQNSolver(inst, cfg)
            if weights is not None:
                solver.load_weights(weights)
            plan, _ = solver.solve(seed=seed + epoch * 100 + idx)
            weights  = solver.clone_weights()
            td_gap, _= plan.gap()
            print(f"    [{epoch+1}:{idx+1}] {inst.name}: nv={plan.nv} gap={td_gap:+.1f}%")
    stem = os.path.join(cfg.output_dir, f"rl_alns_transfer_{label.lower()}_v15")
    _save_weights(weights, stem)
    return weights


def train_domain_randomization(cfg: Config, seed: int = 42) -> Dict:
    """
    3-phase curriculum:
      Phase 1 (0-40%):   Easy   — 20-40 nodes
      Phase 2 (40-80%):  Target — 40-80 nodes
      Phase 3 (80-100%): Chaos  — 20-100 nodes
    """
    total_epochs  = int(cfg.domain_randomization_epochs)
    batch_size    = int(cfg.domain_randomization_batch)
    distributions = ("C", "R", "RC")
    rng     = random.Random(seed)
    weights: Optional[Dict] = None
    print(f"Domain-randomization curriculum: {total_epochs} epochs × {batch_size} instances/epoch")

    for epoch in range(total_epochs):
        frac = (epoch + 1) / max(total_epochs, 1)
        if   frac <= 0.40: phase, n_min, n_max = "Easy  ", 20, 40
        elif frac <= 0.80: phase, n_min, n_max = "Target", 40, 80
        else:              phase, n_min, n_max = "Chaos ", 20, 100
        print(f"  Epoch {epoch+1:>2}/{total_epochs}  [{phase}  N={n_min}-{n_max}]")
        batch: List[Inst] = []
        for idx in range(batch_size):
            n_nodes  = rng.randint(n_min, n_max)
            dist     = distributions[(epoch + idx) % len(distributions)]
            gen_seed = seed + epoch * 10_000 + idx
            batch.append(SyntheticVRPTWGenerator(n_nodes, dist, seed=gen_seed).generate())
        for idx, inst in enumerate(batch):
            solver = HybridDDQNSolver(inst, cfg)
            if weights is not None:
                solver.load_weights(weights)
            plan, _ = solver.solve(seed=seed + epoch * 1_000 + idx)
            weights  = solver.clone_weights()
            print(f"    [{idx+1:>2}/{batch_size}] {inst.name}: "
                  f"n={inst.n}  nv={plan.nv}  cost={plan.cost:.1f}  feasible={plan.feasible}")

    if weights is None:
        raise RuntimeError("Domain randomization produced no weights.")
    os.makedirs(cfg.output_dir, exist_ok=True)
    stem = os.path.join(cfg.output_dir, "rl_alns_dr_v15")
    _save_weights(weights, stem)
    return weights


def train_transfer_model_within_rc2(rc2_instances: List[Inst], cfg: Config,
                                     seed: int = 42) -> Dict:
    source = rc2_instances[:cfg.rc2_transfer_split]
    print(f"RC2-within transfer: train on {[i.name for i in source]}")
    return train_transfer_model(source, cfg, seed=seed, label="RC2-src")


def load_transfer_model(cfg: Config, label: str = "rc1") -> Optional[Dict]:
    stem = os.path.join(cfg.output_dir, f"rl_alns_transfer_{label}_v15")
    return _load_weights(stem)


# ---------------------------------------------------------------------------
# Smoke test  — per-algo timing for accurate wall estimate
# ---------------------------------------------------------------------------
def smoke_test(inst: Inst, seed: int = 42) -> Dict[str, Tuple[float, float]]:
    """
    Returns {algo_name: (gap_pct, elapsed_s)} for the 4 main solvers.
    Uses short iterations so it completes in < 5 min on any hardware.
    """
    short_cfg = Config(
        alns_iterations=300, hybrid_iterations=400,
        early_stop_patience=100, polish_iterations=50,
        polish_patience=30, n_runs=1,
    )
    results: Dict[str, Tuple[float, float]] = {}
    for algo_name, solver_cls in (
        (ALGO_ALNS_BASE,    ALNSSolver),
        (ALGO_HYBRID_FIXED, HybridFixedSolver),
        (ALGO_HYBRID_RULE,  HybridRuleSolver),
        (ALGO_HYBRID_DDQN,  HybridDDQNSolver),
    ):
        random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
        t0    = time.time()
        plan, _= solver_cls(inst, short_cfg).solve(seed=seed)
        elapsed= time.time() - t0
        td_gap, nv_gap = plan.gap()
        gap_str = f"{td_gap:+.1f}%" if td_gap is not None else "N/A"
        nv_str  = f"{nv_gap:+d}"   if nv_gap  is not None else "N/A"
        print(f"{algo_name:<24} nv={plan.nv:>3} cost={plan.cost:>8.1f} "
              f"BKS TD {gap_str} NV {nv_str} ({elapsed:.1f}s)")
        results[algo_name] = (float(td_gap) if td_gap is not None else 0.0, elapsed)
    return results

