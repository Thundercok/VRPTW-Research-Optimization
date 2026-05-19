from __future__ import annotations
import argparse
import sys
import os
from .benchmark import smoke_test
from .generators import SyntheticVRPTWGenerator
from .solvers import ALNSSolver, HybridFixedSolver, HybridRuleSolver, HybridDDQNSolver
from .config import Config

def cmd_smoke_test(args):
    print(f"Running synthetic smoke test (nodes={args.nodes}, distribution={args.dist})...")
    inst = SyntheticVRPTWGenerator(n_nodes=args.nodes, distribution=args.dist, seed=args.seed).generate()
    smoke_test(inst, seed=args.seed)

def cmd_solve(args):
    if not os.path.exists(args.file):
        print(f"Error: file not found: {args.file}")
        sys.exit(1)
    
    print(f"Loading instance from {args.file}...")
    # Read the instance using Solomon format
    from .core import Inst
    import numpy as np
    with open(args.file, encoding="utf-8") as fh:
        lines = fh.readlines()
    name     = lines[0].strip()
    capacity = float(lines[4].strip().split()[1])
    rows     = [list(map(float, ln.split())) for ln in lines[9:] if ln.strip()]
    inst = Inst({"name": name, "capacity": capacity, "data": np.array(rows)})
    
    print(f"Solving instance {inst.name} (capacity={inst.capacity}, customers={len(inst.demands)-1}) with {args.algo}...")
    
    cfg = Config(
        alns_iterations=args.iters,
        hybrid_iterations=args.iters,
        early_stop_patience=args.early_stop,
        polish_iterations=args.polish,
    )
    
    if args.algo == "ALNS-Base":
        solver = ALNSSolver(inst, cfg)
    elif args.algo == "Hybrid-Fixed":
        solver = HybridFixedSolver(inst, cfg)
    elif args.algo == "Hybrid-Rule":
        solver = HybridRuleSolver(inst, cfg)
    elif args.algo == "Hybrid-DDQN":
        solver = HybridDDQNSolver(inst, cfg)
    else:
        print(f"Error: Unknown algorithm: {args.algo}")
        sys.exit(1)
        
    import time
    t0 = time.time()
    plan, history = solver.solve(seed=args.seed)
    dur = time.time() - t0
    
    print("\n═══ SOLUTION FOUND ═══")
    print(f"Status:   {'Feasible' if plan.feasible else 'INFEASIBLE'}")
    print(f"Vehicles: {len(plan.routes)}")
    print(f"Distance: {plan.cost:.2f} km")
    print(f"Runtime:  {dur:.2f} seconds")
    print("\nRoutes:")
    for i, route in enumerate(plan.routes, 1):
        print(f"  Route #{i}: Depot -> {' -> '.join(map(str, route))} -> Depot")

def main():
    parser = argparse.ArgumentParser(description="VRPTW Optimization Research Suite CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Smoke-test command
    p_smoke = subparsers.add_parser("smoke-test", help="Run a quick smoke test with synthetic data")
    p_smoke.add_argument("--nodes", type=int, default=25, help="Number of customer nodes")
    p_smoke.add_argument("--dist", type=str, default="RC", choices=["C", "R", "RC"], help="Geographical distribution")
    p_smoke.add_argument("--seed", type=int, default=42, help="Random seed")
    p_smoke.set_defaults(func=cmd_smoke_test)
    
    # Solve command
    p_solve = subparsers.add_parser("solve", help="Solve a specific Solomon dataset file")
    p_solve.add_argument("file", type=str, help="Path to Solomon .txt file")
    p_solve.add_argument("--algo", type=str, default="Hybrid-DDQN", 
                         choices=["ALNS-Base", "Hybrid-Fixed", "Hybrid-Rule", "Hybrid-DDQN"],
                         help="Optimization solver to run")
    p_solve.add_argument("--iters", type=int, default=1200, help="Solver iteration limit")
    p_solve.add_argument("--early-stop", type=int, default=250, help="Early stop patience")
    p_solve.add_argument("--polish", type=int, default=80, help="Local search polishing iterations")
    p_solve.add_argument("--seed", type=int, default=42, help="Random seed")
    p_solve.set_defaults(func=cmd_solve)
    
    # Benchmark forward help command
    p_bench = subparsers.add_parser("benchmark", help="Instructions for running full benchmark suite")
    p_bench.set_defaults(func=lambda args: print("To run benchmarks, please use the runner script:\n  python3 docs/run_benchmark.py --help"))
    
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()