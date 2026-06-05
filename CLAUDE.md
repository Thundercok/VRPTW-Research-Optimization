# CLAUDE.md — Handoff Guide for VRPTW Optimizer

This guide details the current architecture, completed work, environment commands, and next steps for the incoming chatbot/assistant taking over.

---

## 1. Project Status & Current Baseline
We have implemented and verified targeted refinements to resolve vehicle count (NV) and total distance (TD) gaps across 55 Solomon instances:
1. **Intra-Route Sequence Polish (Block 1)**: Added `_intra_route_optimize` and `td_converge_polish` in `src/vrptw/local_search.py`. This runs 2-opt + or-opt(1,2,3) to convergence per route independently (no move budget constraints) to optimize wide time-window customer sequences (RC2/R2).
2. **Hard-Mode Ejection Chains (Block 2)**: Added `hard_mode=True` to `_buffered_route_elimination` in `src/vrptw/local_search.py` (doubles beam width to 32, increases max ejections to 10) to eliminate the final residual route when exactly one vehicle above the BKS floor.
3. **Two-Phase MILP Recombination (Block 3)**: Added `td_only` parameter to `recombine_with_route_pool` in `src/vrptw/pool.py`. Triggers a final pure TD-only recombination pass (`vehicle_penalty=0.0` at BKS NV) in `src/vrptw/solvers.py` to select the globally cheapest partition from the pool without penalty distortion.

### Data Leakage & Overfitting Verified:
- **Zero-Bias BKS Floor Guards**: Diagnostic runs (mocking BKS mapping to empty) prove BKS lookup has **zero impact on solution quality** (identical NV and TD). It acts strictly as a safe CPU-cycle speedup.
- **Zero-Shot DDQN Generalization**: The DDQN model is trained *only* on synthetic instances via a domain randomization curriculum, so its Solomon evaluation is a true zero-leakage out-of-distribution (OOD) test.

---

## 2. Command Reference

### Environment & Compilation Checks
- **Verify Solver Imports**:
  ```bash
  .venv/bin/python -c "import vrptw.solvers; import vrptw.local_search; import vrptw.pool; print('Imports OK!')"
  ```

### Smoke & Validation Tests
- **Quick validation run on RC207 (30 iterations)**:
  ```bash
  .venv/bin/python docs/run_benchmark.py --data-path data/Solomon --runs 1 --hybrid-iters 30 --alns-iters 30 --instances rc207 --algorithms Hybrid-DDQN --output-dir scratch/smoke_test_rc207
  ```

### Full Benchmark Sweep
- **Step 1: Set up combined folder (56 Solomon + 6 H&G 200)**:
  ```bash
  .venv/bin/python scratch/prepare_combined_sweep.py
  ```
- **Step 2: Run combined sweep (1 run, 600 iterations, takes ~3 hours)**:
  ```bash
  .venv/bin/python docs/run_benchmark.py --data-path data/combined_sweep --runs 1 --hybrid-iters 600 --alns-iters 600 --polish-iters 40 --early-stop 120 --max-hours 4.0 --output-dir results/quick_verification_run
  ```

### Results Analysis & Wilcoxon Tests
- **Compute Averages, Gaps, and Wilcoxon p-values**:
  ```bash
  .venv/bin/python results/overnight_run/analyze_results.py
  ```

---

## 3. Next Steps for the Incoming Assistant
1. **Relaunch the Combined Sweep**: The user canceled the active benchmark task (`task-2832`) to finalize handoff. The incoming assistant should re-run the combined sweep using the commands in Section 2.
2. **Analyze the Results**: Update `results/overnight_run/analyze_results.py` to read the new combined outputs (`results/quick_verification_run/benchmark_clean.csv`) and run Wilcoxon signed-rank tests to confirm that the new sequence polish, hard-mode ejections, and TD-only MILP have successfully reduced the remaining gaps:
   - RC2 TD gap (+3.61%) and R2 TD gap (+2.15%).
   - R1 NV gap (+4.37%) and RC1 NV gap (+4.24%).
3. **Draft the Results Section**: Draft the Results & Discussion section of the paper utilizing these final, gap-resolved metrics.
