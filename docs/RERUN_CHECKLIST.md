# Re-run checklist for `paper.tex`

The solver changes described below alter search trajectories, so **every measured
number in the paper must be regenerated** before submission. This file lists
exactly what is invalidated, what has already been updated, and what has not.

## What changed in the solver

| Change | Effect on results |
|---|---|
| Push-forward O(1) insertion feasibility; batched repair kernels; incremental regret columns; vectorised centroid filters; hoisted route timings | **None** — verified bit-identical against `tests/golden/baseline.json` |
| `op_fts_greedy` feasibility fix (was returning an infeasible plan on 100% of trials) | Changes trajectories; recovers ~20% of the ALNS iteration budget |
| `op_fts_greedy` slack-bonus term removed | Changes trajectories; protects vehicle counts |
| Anytime wall-clock budget, on by default | Changes the experimental protocol |
| Sparse-kNN GNN edge predictor | Requires a retrained checkpoint; heatmap quality not yet validated |

Measured on 90 paired runs (9 instances x 2 solvers x 5 seeds, 400 iterations,
n<=200): **2.62x faster**, mean gap-to-BKS 3.92% -> 3.84%, vehicle count
statistically unchanged (Wilcoxon p=0.617).

> Caveat: that A/B ran at n<=200 with 400 iterations. Production runs 5000
> iterations at up to n=1000. Do not assume the deltas transfer.

## Already updated in `paper.tex`

- [x] GNN Edge Predictor subsection — rewritten for the sparse-kNN architecture
      and the bilinear output head, including the measured memory/latency figures
      (1517 MB / 3.96 s -> 1.3 MB / 0.049 s at n=1000).
- [x] Setup subsection — added the anytime budget paragraph and the iso-time
      justification for the OR-Tools comparison.

**Not verified:** no LaTeX toolchain was available, so the PDF was not recompiled.
Run `pdflatex -interaction=nonstopmode -output-directory=docs docs/paper.tex`
before trusting the edits.

## Must be regenerated (numbers untouched — do NOT trust these as they stand)

| Location | Claim |
|---|---|
| Abstract, ~line 80 | `+0.139` NV inflation, `13.3%` vs ALNS-Base, `92.7%` vs OR-Tools, `5.8%` TD gain |
| Setup, ~line 640 | Runtimes `31.5 / 47.1 / 58.9` s; `24.4%` neural overhead; `861.3 s -> 60.3 s (14x)` Numba claim — **all now stale, the solver is materially faster** |
| Table, ~line 672 | Ablation ($N=62$): NV diff `+0.276 / +0.171 / +0.161 / +0.161`, TD Gap `+0.231 / +0.174 / -0.069 / -0.138`% |
| Table, ~line 694 | $NV_\text{diff}$ on Solomon |
| Table, ~line 729 | NV-filtered TD Gap% |
| Table, ~line 755 | Strict fair intersection ($N=39$) by family |
| Table, ~line 780 | Gehring-Homberger 200-customer at 800 iterations |
| Table, ~line 862 | Baseline vs GNN-guided at 150 iterations; `1.2-1.7x` acceleration claim |
| Throughout | All Wilcoxon p-values, including the H400 significance boundary recorded in `CLAUDE.md` |

## Procedure

```bash
# 1. Retrain the GNN — the sparse architecture cannot load the old checkpoint
PYTHONPATH=src python -m vrptw.train_gnn 150

# 2. Full production sweep (multi-day; PYTHON overrides the interpreter)
PYTHON=python ./run_full_production.sh

# 3. Regenerate tables from results/clean_v2/, then recompile
pdflatex -interaction=nonstopmode -output-directory=docs docs/paper.tex
```

## GNN guidance is NOT currently a quality win

The sparse predictor was retrained (150 epochs, loss 0.969 -> 0.228, 116 pairs —
60 Homberger-200 instances now included for the first time). Falling loss only
shows it fits elite plans, so `scripts/validate_gnn.py` measures whether the
heatmap actually helps: same instances, same seeds, guidance on vs off.

Result over 15 paired runs (5 instances x 3 seeds, 400 iterations):

| Metric | Guidance off | Guidance on |
|---|---|---|
| Vehicle count | 11.800 | 11.800 — **identical in 15/15 runs** |
| Mean distance | 1996.83 | 1991.12 |
| **Gap-to-BKS** | **2.05%** | **2.27% (+0.22 pp, worse)** |

TD better on 8, worse on 6, Wilcoxon p=0.683. The mean-distance improvement and
the gap-to-BKS regression disagree because the mean is dominated by one large
instance; gap-to-BKS weights instances equally and is the metric the paper uses.

The effect is family-dependent and consistent within family:

| Family | Seeds improved |
|---|---|
| R1 (R101) | 3/3 |
| C2 (C203) | 2/3 — reaches the BKS optimum of 591.17 |
| RC1 (RC105) | 1/3 |
| RC2 (RC207) | **0/3** — worse by +31 to +47 every seed |

**Do not claim GNN guidance improves solution quality without re-establishing it.**
Two things are untested: `gnn_guidance_strength = 0.45` was tuned for the dense
architecture and may not transfer, and the sparse predictor has never been
compared against the dense one head-to-head — only against no guidance at all.
What Phase 5 does establish is scalability: 1517 MB -> 1.3 MB and 3.96 s -> 0.049 s
per forward pass at n=1000.

The previous dense checkpoint was overwritten by retraining. Recover it with
`git checkout HEAD -- docs/model/gnn_edge_predictor.pt` (it will not load into the
sparse architecture, but is needed for any dense-vs-sparse comparison).

## Open risk

`op_fts_greedy` was inert before this work — it returned an infeasible plan every
time, so its composite objective had never been exercised by any experiment. Its
remaining weight, `wait_weight = 0.10 + 0.35 * tw_tight_frac`, is therefore still
un-validated, exactly as the removed slack term was. It was left at its original
value rather than tuned, because tuning it on the same instances the paper reports
would be fitting to the test set. If it is to be tuned, hold out a separate set.
