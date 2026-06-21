# CLAUDE.md — Handoff Guide for VRPTW Optimizer

This guide details the current architecture, completed work, environment commands, and next steps for the incoming assistant.

---

## 1. Project Status & Current Baseline
We have implemented and verified targeted refinements to resolve vehicle count (NV) and total distance (TD) gaps under strict independent cold-starts (cleared archive, empty cache).

### Verified Findings:
1. **Budget Propagation Audit**: Verified empirically via child-worker log trace that CLI overrides propagate correctly (confirmed `cfg.alns_iterations=1000` inside a spawned worker).
2. **Scale-Aware Divergence (Solomon + H200)**: Under cold-starts, NV-flattening holds. Both ALNS-Base and Hybrid-DDQN converge to the same minimum vehicle count floor (e.g. Solomon `R101`/`RC101` and Homberger `r1_2_1`/`rc1_2_1`). Hybrid-DDQN wins on **consistency** (hitting floor in 100% of runs vs. 30%–70% for ALNS-Base) and **TD minimization** (1.75% to 4.07% gap reduction at matched NV).
3. **Large Scale Graceful Degradation (H400)**: Neither solver approaches BKS at 400 customers. However, Hybrid-DDQN achieves a small but statistically significant vehicle count edge on `c2_4_1` ($p=0.0078$) and `r2_4_1` ($p=0.0156$). The $0.30$-vehicle delta on `rc2_4_1` is **not statistically significant** ($p=0.3750$). Sign consistency of differences across all three instances supports a genuine small effect.
4. **LaTeX Updates**: Updated `docs/paper.tex` to honestly state the large gap-to-BKS, Wilcoxon p-values, and the significance boundary. PDF compiled successfully.

---

## 2. Command Reference

### Environment & Compilation Checks
- **Verify Solver Imports**:
  ```bash
  .venv/bin/python -c "import vrptw.solvers; import vrptw.local_search; import vrptw.pool; print('Imports OK!')"
  ```
- **Recompile Paper PDF**:
  ```bash
  pdflatex -interaction=nonstopmode -output-directory=docs docs/paper.tex
  ```

### Smoke & Validation Tests
- **Quick validation run on RC207 (30 iterations)**:
  ```bash
  .venv/bin/python docs/run_benchmark.py --data-path data/Solomon --runs 1 --hybrid-iters 30 --alns-iters 30 --instances rc207 --algorithms Hybrid-DDQN --output-dir scratch/smoke_test_rc207
  ```

---

## 3. Next Steps for the Incoming Assistant
1. **Resume Production Sweep**: Run `./run_full_production.sh`. Because the 15s-capped OR-Tools rows have been purged from the checkpoints and `run_full_production.sh` is now updated with `--ortools-time-limit 120`, resuming the script will automatically run only the missing OR-Tools baselines under the correct 120s budget for the completed shards (Solomon, H200, H400), before finishing H600/800/1000.
2. **Tabulate and Analyze**: Once the sweep finishes, run results analysis and generate the final publication tables.
3. **Verify paper.pdf Typesetting**: Verify the compiled PDF for proper alignment and typesetting of updated tables.
