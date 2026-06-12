import torch
import torch.nn as nn
import torch.nn.functional as F
from .core import Inst, Plan

class GNNLayer(nn.Module):
    """
    Graph Neural Network layer that updates node features and edge features jointly.
    Useful for edge-prediction routing tasks.
    """
    def __init__(self, hidden_dim: int):
        super().__init__()
        self.node_mlp = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim)
        )
        self.edge_mlp = nn.Sequential(
            nn.Linear(hidden_dim * 3, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim)
        )
        
    def forward(self, h_nodes: torch.Tensor, h_edges: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        # h_nodes: (B, N, hidden_dim)
        # h_edges: (B, N, N, hidden_dim)
        B, N, H = h_nodes.shape
        
        # 1. Update edges based on adjacent nodes
        # For edge (i, j), aggregate h_i and h_j
        h_nodes_i = h_nodes.unsqueeze(2).expand(B, N, N, H)
        h_nodes_j = h_nodes.unsqueeze(1).expand(B, N, N, H)
        edge_in = torch.cat([h_edges, h_nodes_i, h_nodes_j], dim=-1)
        h_edges_new = h_edges + self.edge_mlp(edge_in)
        
        # 2. Update nodes based on edge-weighted message passing
        # Message from j to i is edge_ij + h_j
        messages = h_edges_new + h_nodes_j
        # Simple mean/max aggregation over neighbors j
        agg_msg = messages.mean(dim=2)  # (B, N, H)
        
        node_in = torch.cat([h_nodes, agg_msg], dim=-1)
        h_nodes_new = h_nodes + self.node_mlp(node_in)
        
        return h_nodes_new, h_edges_new


class GNNEdgePredictor(nn.Module):
    """
    Graph Neural Network for predicting edge probabilities in VRPTW.
    """
    def __init__(self, node_dim: int = 6, edge_dim: int = 1, hidden_dim: int = 64, num_layers: int = 3):
        super().__init__()
        self.node_embed = nn.Linear(node_dim, hidden_dim)
        self.edge_embed = nn.Linear(edge_dim, hidden_dim)
        
        self.layers = nn.ModuleList([GNNLayer(hidden_dim) for _ in range(num_layers)])
        
        self.edge_predictor = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1)
        )
        
    def forward(self, x_nodes: torch.Tensor, x_edges: torch.Tensor) -> torch.Tensor:
        # x_nodes: (B, N, node_dim)
        # x_edges: (B, N, N, edge_dim)
        h_nodes = self.node_embed(x_nodes)
        h_edges = self.edge_embed(x_edges)
        
        for layer in self.layers:
            h_nodes, h_edges = layer(h_nodes, h_edges)
            
        # Predict edge logits
        logits = self.edge_predictor(h_edges).squeeze(-1)  # (B, N, N)
        return logits


def get_gnn_features(inst: Inst) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Extracts and normalizes VRPTW instance features into PyTorch tensors.
    """
    n_nodes = inst.n + 1
    # 1. Node features: x, y, demand, ready_time, due_time, service_time
    coords = inst.coords
    demands = inst.demands
    ready = inst.ready_times
    due = inst.due_times
    service = inst.service_times
    
    # Coordinate normalization to [0, 1]
    min_coords = coords.min(axis=0)
    max_coords = coords.max(axis=0)
    coords_range = max_coords - min_coords
    coords_range[coords_range == 0] = 1.0
    norm_coords = (coords - min_coords) / coords_range
    
    # Other normalization
    norm_demands = demands / max(inst.capacity, 1.0)
    max_time = max(due[0], 1.0)  # depot due time
    norm_ready = ready / max_time
    norm_due = due / max_time
    norm_service = service / max_time
    
    node_feats = torch.zeros((n_nodes, 6), dtype=torch.float32)
    node_feats[:, 0:2] = torch.tensor(norm_coords, dtype=torch.float32)
    node_feats[:, 2] = torch.tensor(norm_demands, dtype=torch.float32)
    node_feats[:, 3] = torch.tensor(norm_ready, dtype=torch.float32)
    node_feats[:, 4] = torch.tensor(norm_due, dtype=torch.float32)
    node_feats[:, 5] = torch.tensor(norm_service, dtype=torch.float32)
    
    # 2. Edge features: normalized pairwise distances
    max_dist = max(inst.dist.max(), 1.0)
    norm_dist = inst.dist / max_dist
    edge_feats = torch.tensor(norm_dist, dtype=torch.float32).unsqueeze(-1)  # (N, N, 1)
    
    # Add batch dimension: (1, N, node_dim), (1, N, N, edge_dim)
    return node_feats.unsqueeze(0), edge_feats.unsqueeze(0)


def plan_to_adj_matrix(plan: Plan) -> torch.Tensor:
    """
    Converts a plan (list of routes) into an adjacency matrix of shape (N+1, N+1).
    BKS/Elite solutions are encoded as targets.
    """
    n_nodes = plan.inst.n + 1
    adj = torch.zeros((n_nodes, n_nodes), dtype=torch.float32)
    for r in plan.routes:
        if not r:
            continue
        # depot -> first node
        adj[0, r[0]] = 1.0
        # consecutive customer node sequences
        for i in range(len(r) - 1):
            adj[r[i], r[i+1]] = 1.0
        # last node -> depot
        adj[r[-1], 0] = 1.0
    return adj
