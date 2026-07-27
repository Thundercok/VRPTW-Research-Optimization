Four cleanup agents (reuse, simplification, efficiency, altitude) reviewed the branch diff (main → working tree, ~20 code files). After deduping, I applied the high-confidence, behavior-preserving fixes:

1. insert_dynamic_customer now reuses the batched insertion kernel — src/vrptw/solvers.py:342
Flagged by all four agents. It re-implemented cheapest-feasible insertion by rebuilding a full Plan for every (route, position) candidate — O(R·m) plan copies + evaluations for one customer, despite this same diff introducing _insert_into_cheapest_route (one Numba call). Replaced with a plan.copy() + _insert_into_cheapest_route(...). Behavior-equivalent for a feasible plan (minimizing insertion delta = minimizing resulting total distance; feasibility identical since only the target route changes; invalidate() clears the _route_arrays cache so no stale state). This is REST-API-facing code (ops.py:905), so the win matters per call.

2. Deleted four dead functions orphaned by the refactor — src/vrptw/heuristics.py
_best_insert_position_pruned_numba, _best_insert_position_biased_numba, _best_insert_position_biased, and _insert_customer_biased — all left unreachable after op_greedy/op_tw_greedy/_best_relocate were rewired to the new kernels. The diff had even edited two of them (wasted work). Grep confirmed zero references repo-wide before deleting.

3. Removed the global ITERS mutable-global data flow — scripts/ab_compare.py
main() mutated module-level ITERS, which run()/make_cfg() read implicitly. Threaded iters through as an explicit parameter; ITERS = 400 now serves only as the argparse default.

4. Dropped a dead assignment — src/vrptw/solvers.py:1506
sub2_deadline was set to None then unconditionally overwritten before use in that branch.

All three touched Python files byte-compile cleanly and no dangling references to the deleted symbols remain.

Skipped (with reason)

- Deleting cpp_hooks.py, the GAT layer (gnn.py), and multi_depots/vehicle_capacities placeholders — flagged as dead by three agents, but this is intended roadmap scaffolding on a branch literally named Add-GAT, referenced in docs/roadmap_implementation_comparison.md. Deleting it would revert in-progress feature work, not clean it up. (The agents' note that get_gat_embeddings builds untrained modules per call is a correctness concern — out of scope for /simplify; worth a look via /code-review if that path ever gets wired in.)
- Efficiency micro-opts (partial column refresh in operators.py, incremental centroid_sqdist in local_search.py) — real but marginal, and they'd add indexing complexity/risk to hot Numba-backed paths the diff already carefully tuned. Rated minor by the efficiency agent.
- Larger altitude refactors (unifying the time-budget derivation onto Config, collapsing the ~15 scattered _out_of_time() tail guards, thread-pinning at the resolved-worker layer) — legitimate, but each is a structural change to tuned anytime/threading logic beyond a cleanup pass; better as their own focused change.
- Low-value reuse nits (test/script Solomon-parse duplication, GES step-1, inline gap-to-BKS) — ab_compare.py's self-contained parse is deliberately version-agnostic for git stash comparisons; the rest are awkward or trivial.