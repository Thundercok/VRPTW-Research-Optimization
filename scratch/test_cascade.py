import sys
sys.path.insert(0, "src")
from vrptw import Config, load_datasets, HybridDDQNSolver, HybridFixedSolver, HybridRuleSolver

datasets = load_datasets("data/Solomon")
inst = None
for g, insts in datasets.items():
    for i in insts:
        if i.name == "RC101":
            inst = i
            break
if not inst:
    print("RC101 not found")
    sys.exit(1)

cfg = Config(
    alns_iterations=5,
    hybrid_iterations=5,
    early_stop_patience=5,
    polish_iterations=5,
    n_runs=3,
)

print("--- Testing HybridDDQNSolver cascading ---")
solver = HybridDDQNSolver(inst, cfg)
plan, histories = solver.solve_multi_run(n_runs=3, base_seed=42)
print(f"Cascade Success! Best NV: {plan.nv}, cost: {plan.cost:.2f}, feasible: {plan.feasible}")
print(f"Histories counts: {[len(h) for h in histories]}")

print("\n--- Testing HybridFixedSolver cascading ---")
fixed_solver = HybridFixedSolver(inst, cfg)
plan_f, histories_f = fixed_solver.solve_multi_run(n_runs=3, base_seed=42)
print(f"Fixed Cascade Success! Best NV: {plan_f.nv}, cost: {plan_f.cost:.2f}, feasible: {plan_f.feasible}")

print("\n--- Testing HybridRuleSolver cascading ---")
rule_solver = HybridRuleSolver(inst, cfg)
plan_r, histories_r = rule_solver.solve_multi_run(n_runs=3, base_seed=42)
print(f"Rule Cascade Success! Best NV: {plan_r.nv}, cost: {plan_r.cost:.2f}, feasible: {plan_r.feasible}")
