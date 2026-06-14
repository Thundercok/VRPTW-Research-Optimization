import sys
import os
import time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath("src"))

from vrptw import Config, Inst, HybridDDQNSolver, run_ortools
from vrptw.config import BKS

def load_solomon(path: str) -> Inst:
    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()
    name = lines[0].strip()
    capacity = float(lines[4].strip().split()[1])
    rows = [list(map(float, ln.split())) for ln in lines[9:] if ln.strip()]
    return Inst({"name": name, "capacity": capacity, "data": np.array(rows)})

def run_test():
    instances = ["R101", "RC101"]
    data_dir = "data/Solomon"
    if not os.path.exists(data_dir):
        data_dir = "docs/data/Solomon"
        
    gnn_path = "docs/model/gnn_edge_predictor.pt"
    if not os.path.exists(gnn_path):
        print(f"Error: GNN model not found at {gnn_path}")
        return
        
    cfg = Config(
        hybrid_iterations=150,  # 150 iterations for quick verification
        segment_size=30,
        gnn_guidance_strength=0.45,
        gnn_pruning_threshold_start=0.05,
        gnn_pruning_threshold_end=0.003,
        ortools_time_limit=15.0
    )
    
    seeds = [42]
    rows = []
    
    print("==========================================================================")
    # Vietnamese slang reference: "Thả rạ mõm OR-Tools"
    print("  DEMOLISHING OR-TOOLS WITH OUR GNN-GUIDED HYBRID-DDQN")
    print("==========================================================================")
    
    for name in instances:
        path = os.path.join(data_dir, f"{name}.txt")
        if not os.path.exists(path):
            path = os.path.join(data_dir, f"{name}.TXT")
        if not os.path.exists(path):
            print(f"Skipping {name}: file not found.")
            continue
            
        inst = load_solomon(path)
        bks_nv = BKS[name]["nv"]
        bks_td = BKS[name]["td"]
        
        print(f"\nBenchmarking Instance {name} (BKS: NV={bks_nv}, TD={bks_td:.2f})...")
        
        # 1. OR-Tools Run
        print("Running OR-Tools (15s time limit)...")
        t0 = time.time()
        ort_plan, _ = run_ortools(inst, cfg)
        ort_time = time.time() - t0
        ort_nv = ort_plan.nv if ort_plan is not None else float('inf')
        ort_td = ort_plan.cost if ort_plan is not None else float('inf')
        print(f"  OR-Tools:   NV={ort_nv:.2f}, TD={ort_td:.2f} ({ort_time:.1f}s)")
        
        # 2. GNN-Guided Run
        print("Running GNN-Guided Hybrid-DDQN...")
        solver = HybridDDQNSolver(inst, cfg)
        solver.load_gnn_model(gnn_path)
        t0 = time.time()
        gnn_plan, _ = solver.solve(seed=42, frozen=True)
        gnn_time = time.time() - t0
        gnn_nv = gnn_plan.nv
        gnn_td = gnn_plan.cost
        print(f"  Our GNN-DDQN: NV={gnn_nv:.2f}, TD={gnn_td:.2f} ({gnn_time:.1f}s)")
        
        rows.append({
            "Instance": name,
            "BKS (NV/TD)": f"{bks_nv}/{bks_td:.1f}",
            "OR-Tools NV": f"{ort_nv:.1f}",
            "OR-Tools TD": f"{ort_td:.1f}",
            "OR-Tools Time": f"{ort_time:.1f}s",
            "Our GNN-DDQN NV": f"{gnn_nv:.1f}",
            "Our GNN-DDQN TD": f"{gnn_td:.1f}",
            "Our Time": f"{gnn_time:.1f}s"
        })
        
    df = pd.DataFrame(rows)
    print("\n==========================================================================")
    print("  COMPARISON SUMMARY")
    print("==========================================================================")
    # Output raw table format (avoid tabulate requirements)
    print(df.to_string(index=False))
    print("==========================================================================")

if __name__ == "__main__":
    run_test()
