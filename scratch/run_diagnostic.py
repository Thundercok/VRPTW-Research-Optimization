import sys
import time
sys.path.insert(0, "src")

from vrptw import Config, load_datasets, HybridDDQNSolver, Plan

# Load dataset
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

# Configure solver
cfg = Config(
    alns_iterations=300,
    hybrid_iterations=300,
    early_stop_patience=100,
    polish_iterations=30,
    n_runs=1,
)

# Custom HybridDDQNSolver subclass to add verbose diagnostics
class DiagnosticSolver(HybridDDQNSolver):
    def _committed_nv_search(self, start: Plan, pool, target_nv: int, n_iters: int = 500) -> Plan | None:
        n_routes = len(pool._routes)
        avg_len = sum(len(r.nodes) for r in pool._routes.values()) / max(n_routes, 1)
        print(f"\n[DIAGNOSTIC] _committed_nv_search fired!")
        print(f"  Current best NV: {start.nv}, Cost: {start.cost:.2f}")
        print(f"  Target NV: {target_nv}")
        print(f"  Pool routes count: {n_routes}")
        print(f"  Average route length in pool: {avg_len:.2f}")
        
        # Run the search
        t0 = time.time()
        res = super()._committed_nv_search(start, pool, target_nv, n_iters)
        elapsed = time.time() - t0
        
        if res is not None:
            print(f"  Result: Success! Found Plan with NV: {res.nv}, Cost: {res.cost:.2f} (Time: {elapsed:.1f}s)")
        else:
            print(f"  Result: Failed (None returned) (Time: {elapsed:.1f}s)")
        return res

print("Starting diagnostic solver run on RC101...")
solver = DiagnosticSolver(inst, cfg)
best_plan, history = solver.solve(seed=42)
print(f"\nDiagnostic run finished. Final plan NV: {best_plan.nv}, cost: {best_plan.cost:.2f}, feasible: {best_plan.feasible}")
