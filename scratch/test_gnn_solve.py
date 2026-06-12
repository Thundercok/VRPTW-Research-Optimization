import sys
import os
import random
import numpy as np
import torch

sys.path.insert(0, os.path.abspath("src"))

from vrptw import Config, Inst, HybridDDQNSolver

def load_solomon(path: str) -> Inst:
    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()
    name = lines[0].strip()
    capacity = float(lines[4].strip().split()[1])
    rows = [list(map(float, ln.split())) for ln in lines[9:] if ln.strip()]
    return Inst({"name": name, "capacity": capacity, "data": np.array(rows)})

def test():
    print("Testing SOTA GNN edge predictor integration...")
    inst_path = "data/Solomon/RC101.txt"
    if not os.path.exists(inst_path):
        inst_path = "docs/data/Solomon/RC101.txt"
    if not os.path.exists(inst_path):
        print(f"Error: Solomon data not found at {inst_path}")
        return
        
    inst = load_solomon(inst_path)
    cfg = Config(
        hybrid_iterations=50,
        segment_size=10,
        gnn_guidance_strength=0.5
    )
    
    # 1. Initialize solver
    solver = HybridDDQNSolver(inst, cfg)
    
    # 2. Load trained GNN edge predictor
    model_path = "docs/model/gnn_edge_predictor.pt"
    if not os.path.exists(model_path):
        print(f"Error: Trained model not found at {model_path}")
        return
        
    print(f"Loading GNN model from {model_path}...")
    solver.load_gnn_model(model_path)
    
    # Verify GNN is loaded
    assert solver.gnn_model is not None, "GNN model should not be None"
    
    # 3. Solve instance
    print("Running solve with GNN heatmap guidance...")
    best_plan, history = solver.solve(seed=42)
    
    print("SUCCESS: GNN-biased solver completed solve loop successfully!")
    print(f"Result: NV={best_plan.nv}, cost={best_plan.cost:.2f}")

if __name__ == "__main__":
    test()
