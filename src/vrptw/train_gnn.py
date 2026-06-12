import os
import json
import random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from .config import Config, default_data_path
from .core import Inst, Plan
from .generators import load_datasets
from .gnn import GNNEdgePredictor, get_gnn_features, plan_to_adj_matrix

def find_elite_plans():
    """
    Scans results directories for elite JSON plans and returns a dictionary
    mapping instance_name (uppercase) -> path_to_json.
    """
    plans = {}
    search_dirs = [
        "results/ultimate-publication-suite",
        "results/ultimate-publication-suite-legacy",
        "elite_plans",
        "scratch"
    ]
    for d in search_dirs:
        if not os.path.exists(d):
            continue
        for root, _, files in os.walk(d):
            for f in files:
                if f.endswith(".json") and not f.startswith("package"):
                    name = os.path.splitext(f)[0].upper()
                    plans[name] = os.path.join(root, f)
    return plans

def train_gnn(epochs: int = 150, lr: float = 1e-3, save_path: str = "docs/model/gnn_edge_predictor.pt"):
    print("==========================================================================")
    print("  TRAINING SOTA GNN EDGE PREDICTOR")
    print("==========================================================================")
    
    # 1. Load instances
    data_path = default_data_path()
    print(f"Loading datasets from {data_path}...")
    datasets = load_datasets(data_path)
    
    # Flatten datasets into a single dictionary mapping name (uppercase) -> Inst
    insts = {}
    for group in datasets.values():
        for inst in group:
            insts[inst.name.upper()] = inst
            
    # Also load Homberger-200 instances manually
    homberger_dir = os.path.join("data", "Gehring_Homberger", "homberger_200_customer_instances")
    if os.path.exists(homberger_dir):
        for f in os.listdir(homberger_dir):
            if f.endswith((".TXT", ".txt")):
                try:
                    inst = Inst(os.path.join(homberger_dir, f))
                    insts[inst.name.upper()] = inst
                except Exception:
                    pass
                    
    # 2. Find matching elite plans
    elite_plan_paths = find_elite_plans()
    print(f"Found {len(elite_plan_paths)} elite plans in results directories.")
    
    # Build dataset
    training_data = []
    for name, path in elite_plan_paths.items():
        if name not in insts:
            continue
        inst = insts[name]
        try:
            with open(path) as f:
                data = json.load(f)
            plan = Plan(data["routes"], inst, data.get("algo", ""))
            if plan.feasible:
                training_data.append((inst, plan))
        except Exception as e:
            print(f"Error loading plan {path}: {e}")
            
    print(f"Successfully compiled {len(training_data)} matching training pairs.")
    if not training_data:
        print("Error: No valid training pairs found! Cannot train.")
        return
        
    # 3. Model setup
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    model = GNNEdgePredictor(node_dim=6, edge_dim=1, hidden_dim=64, num_layers=3).to(device)
    optimizer = optim.Adam(model.parameters(), lr=lr)
    
    # 4. Training loop
    model.train()
    for epoch in range(1, epochs + 1):
        random.shuffle(training_data)
        epoch_loss = 0.0
        
        for inst, plan in training_data:
            node_feats, edge_feats = get_gnn_features(inst)
            targets = plan_to_adj_matrix(plan).to(device)  # (N+1, N+1)
            
            optimizer.zero_grad()
            logits = model(node_feats.to(device), edge_feats.to(device))[0]  # (N+1, N+1)
            
            # Weighted BCE loss calculation
            # Positive edges are sparse (approx 1 in N), so we weigh positive samples by N
            n_nodes = inst.n + 1
            pos_weight = torch.tensor([n_nodes], dtype=torch.float32, device=device)
            loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
            
            loss = loss_fn(logits, targets)
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()
            
        avg_loss = epoch_loss / len(training_data)
        if epoch % 10 == 0 or epoch == 1:
            print(f"Epoch {epoch:3d}/{epochs} | Avg Loss: {avg_loss:.5f}")
            
    # 5. Save model
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    torch.save(model.state_dict(), save_path)
    print(f"Model saved successfully to {save_path}")
    print("==========================================================================")

if __name__ == "__main__":
    import sys
    epochs = 150
    if len(sys.argv) > 1:
        epochs = int(sys.argv[1])
    train_gnn(epochs=epochs)
