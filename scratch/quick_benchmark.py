import sys
import os
import time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath("src"))

from vrptw import Config, Inst, HybridDDQNSolver
from vrptw.config import BKS

def load_solomon(path: str) -> Inst:
    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()
    name = lines[0].strip()
    capacity = float(lines[4].strip().split()[1])
    rows = [list(map(float, ln.split())) for ln in lines[9:] if ln.strip()]
    return Inst({"name": name, "capacity": capacity, "data": np.array(rows)})

def run_test():
    instances = ["C101", "R101", "RC101"]
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
        gnn_pruning_threshold_end=0.003
    )
    
    seeds = [42]
    rows = []
    
    print("==========================================================================")
    print("  RUNNING QUICK GNN UPGRADE VS. BASELINE COMPARISON BENCHMARK")
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
        
        # 1. Baseline Run (no GNN model loaded, so heatmap is None, falls back to standard ALNS and unbiased pool)
        base_nv_list = []
        base_td_list = []
        base_time_list = []
        for seed in seeds:
            solver = HybridDDQNSolver(inst, cfg)
            t0 = time.time()
            plan, _ = solver.solve(seed=seed, frozen=True)
            base_time_list.append(time.time() - t0)
            base_nv_list.append(plan.nv)
            base_td_list.append(plan.cost)
            
        base_nv_avg = np.mean(base_nv_list)
        base_td_avg = np.mean(base_td_list)
        base_time_avg = np.mean(base_time_list)
        
        # 2. GNN-Guided Run (loads GNN predictor -> heatmap, dynamic pruning, op_neural_shaw, biased pool)
        gnn_nv_list = []
        gnn_td_list = []
        gnn_time_list = []
        for seed in seeds:
            solver = HybridDDQNSolver(inst, cfg)
            solver.load_gnn_model(gnn_path)
            t0 = time.time()
            plan, _ = solver.solve(seed=seed, frozen=True)
            gnn_time_list.append(time.time() - t0)
            gnn_nv_list.append(plan.nv)
            gnn_td_list.append(plan.cost)
            
        gnn_nv_avg = np.mean(gnn_nv_list)
        gnn_td_avg = np.mean(gnn_td_list)
        gnn_time_avg = np.mean(gnn_time_list)
        
        print(f"  Baseline:   Avg NV={base_nv_avg:.2f}, Avg TD={base_td_avg:.2f} ({base_time_avg:.1f}s)")
        print(f"  GNN Guided: Avg NV={gnn_nv_avg:.2f}, Avg TD={gnn_td_avg:.2f} ({gnn_time_avg:.1f}s)")
        
        rows.append({
            "Instance": name,
            "BKS NV/TD": f"{bks_nv}/{bks_td:.1f}",
            "Base NV": f"{base_nv_avg:.2f}",
            "Base TD": f"{base_td_avg:.2f}",
            "GNN NV": f"{gnn_nv_avg:.2f}",
            "GNN TD": f"{gnn_td_avg:.2f}",
            "Base Time": f"{base_time_avg:.1f}s",
            "GNN Time": f"{gnn_time_avg:.1f}s",
        })
        
    df = pd.DataFrame(rows)
    print("\nBenchmark Summary Table:")
    print(df.to_string(index=False))

if __name__ == "__main__":
    run_test()
