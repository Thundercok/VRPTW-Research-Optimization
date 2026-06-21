# Project Rules & Reference Memory

## Critical Benchmark Findings (Updated)

* **Independent Cold-Starts Enforced**: Sequential execution in the benchmark runner previously warm-started downstream solvers via the shared `EliteArchive` directory, which loaded cached solutions from prior sweeps and produced non-reproducible vehicle count reductions (e.g. $NV=14$ on `RC101` and $NV=18$ on `r1_2_1`/`rc1_2_1`). Under strict independent cold-starts starting from `build_greedy` in a cleared directory, these instances convergence to $NV=15$, $NV=20$, and $NV=19$ respectively.
* **Scale-Aware Performance Divergence**: The hybrid solvers' performance advantage exhibits a clear scale-aware divergence under strict cold-starts:
  - **200-Customer Scale (NV-Flattening & TD Dominance)**: Both solvers converge to the same vehicle count floor. The Hybrid-DDQN advantage is defined by consistency (0% to 20% degradation rate to higher NV counts vs 30% to 70% for ALNS-Base) and TD minimization of **1.75% to 4.07%** at matched NV.
  - **400-Customer Scale (Suboptimal Graceful Degradation)**: Neither solver approaches BKS (e.g. BKS NV=4 on `r2_4_1`, solvers land at 8.10–8.80). However, Hybrid-DDQN exhibits a small, statistically significant vehicle count edge of 0.70–0.80 vehicles over ALNS-Base on `c2_4_1` (Wilcoxon $p=0.0078$) and `r2_4_1` (Wilcoxon $p=0.0156$). On `rc2_4_1`, the 0.30-vehicle gap is not statistically significant (Wilcoxon $p=0.3750$).
    - `c2_4_1` (BKS NV=10): ALNS-Base = `[13, 13, 13, 13, 13, 13, 13, 13, 13, 13]` (Mean: 13.00) vs. Hybrid-DDQN = `[13, 12, 12, 12, 12, 13, 12, 12, 12, 12]` (Mean: 12.20, Wilcoxon $p=0.0078$).
    - `rc2_4_1` (BKS NV=10): ALNS-Base = `[12, 13, 13, 13, 13, 12, 13, 13, 13, 13]` (Mean: 12.80) vs. Hybrid-DDQN = `[12, 13, 13, 13, 13, 13, 12, 12, 12, 12]` (Mean: 12.50, Wilcoxon $p=0.3750$, not significant).
    - `r2_4_1` (BKS NV=4): ALNS-Base = `[9, 9, 9, 9, 9, 9, 8, 8, 9, 9]` (Mean: 8.80) vs. Hybrid-DDQN = `[8, 8, 8, 8, 8, 9, 8, 8, 8, 8]` (Mean: 8.10, Wilcoxon $p=0.0156$).
* **Scale-Aware Computational Cost**: Hybrid-DDQN is a quality-maximizing strategy that trades computational budget for routing quality, rather than a search accelerator. It runs $1.5\times$ to $4\times$ slower on Solomon-100, $1.3\times$ to $4.6\times$ slower on Homberger-200, and $2\times$ to $100\times$ slower on Homberger-400 (where ALNS-Base early-stops prematurely). The DQN constructive decoder has a pathological case on Homberger-400 `r2_4_1`, which should be avoided or run with simplified constraints.

## Style Guidelines & Best Practices

1. **Academic Integrity**: Never report cross-seeded or sequential warm-started results in publication tables as standalone solver performance. Standalone solver results must be generated under strict cold-starts. Cooperative refinement via shared archives must be explicitly framed as a multi-stage solver pipeline.
2. **Fair TD Gaps**: Always exclude TD comparisons when vehicle counts are not matched (e.g. ALNS-Base at $NV=15$ vs BKS $NV=14$ on Solomon `RC101`), as extra vehicle capacity artificially distorts travel distance. Highlight these as inflated vehicle counts using appropriate markers (e.g., `†`).
3. **Budget Consistency**: Confirm that worker processes receive matching max iterations (`alns_iterations` and `hybrid_iterations`) via CLI argument overrides during parallel spawns. Avoid recreating `Config` objects in worker scripts using partial dictionary unpacks that cause parameters to default silently.
