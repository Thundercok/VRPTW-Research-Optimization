# VRPTW Research Audit

Current evidence from `benchmark_clean.csv`, `benchmark_transfer.csv`, and `hybrid-rl-alns-for-vrptw.log`:

- `DDQN-ALNS` is genuinely promising on `RC1`.
- On the current `RC1` runs, it beats legacy `ALNS` on gap in `7/8` instances, wins vehicle count in `5/8`, and is faster in `6/8`.
- The current zero-shot transfer story on `RC2` is not strong yet.
- On `RC2`, `DDQN-ALNS` has mean gap delta `-0.16` points versus `ALNS`, wins vehicle count in `0/8`, and the log's Wilcoxon output is non-significant there.

Main risks in the original notebook:

- The published `ALNS` baseline was weaker than the proposed method because it did not receive the same route-pool recombination, local search, and fixed-NV polish stack.
- The transfer pipeline used naive weight averaging across independently trained controllers, which is a weak and unstable form of transfer.
- The notebook banner/log metadata claimed `iter=3000, n_runs=8`, but the actual default config in the source was `2000` and `4`.

What was changed in `hybrid-rl-alns-for-vrptw.ipynb`:

- Added `ALNS+`, a fair non-RL baseline that uses the same enhanced search stack through `PlateauHybridSolver(..., frozen=True)`.
- Switched transfer training from naive weight averaging to sequential curriculum fine-tuning across source instances.
- Updated statistical comparison hooks so `DDQN-ALNS` can be compared against `ALNS+` as well as legacy `ALNS`.
- Updated benchmark cell defaults to run `['ALNS', 'ALNS+', 'DDQN-ALNS']`.
- Fixed version/config metadata strings so exported logs and plots match the actual source defaults.

Highest-value next experiments:

1. Rerun Phase 1 with `ALNS`, `ALNS+`, and `DDQN-ALNS`, then treat `DDQN-ALNS vs ALNS+` as the real fairness test.
2. Rerun transfer with the new sequential curriculum and compare it directly against the old weight-averaging checkpoint.
3. Add a family-holdout protocol beyond `RC1 -> RC2` so the transfer claim is not tied to one split.
4. Promote per-instance win counts and paired confidence intervals in the write-up, not only mean gap.
