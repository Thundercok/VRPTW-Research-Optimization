#!/usr/bin/env python
# coding: utf-8

# CHANGELOG v10.0 
# 
# [CFG-1..6] All v9.6 config changes retained
# [NEW-1] RoutePool: feasible route store + MILP/greedy set-partition recombination
# [NEW-2] _fixed_nv_polish: 450-iter post-search intensification at fixed NV
# [NEW-3] MODE route_reduce (MODE_ROUTE_REDUCE=4): eliminates short/light routes
# [NEW-4] op_route_eliminate: 6th destroy operator â†’ N_D=6, destroy_bias length=6
# [NEW-5] accept_with_nv_ceiling: SA acceptance with hard NV ceiling
# [NEW-6] recombine_after_main_search + recombine_after_polish passes
# [NEW-7] local_search: 2-opt intra-route + best-relocate inter-route
# [NEW-8] scipy.milp set-partition (optional; falls back to greedy cover)
# [NEW-9] _fleet_fill, RouteRecord, _route_cost_list, _route_load helpers
# [NEW-10] ALNS+ fair baseline: PlateauHybridSolver frozen in default mode
# [NEW-11] Transfer training switched from weight averaging to sequential curriculum fine-tuning
# [NEW-12] Controller upgraded to true dueling DDQN with Huber loss
# [NEW-13] RL acts earlier than route_reduce and can trigger inline refine/recombine moves
# [NEW-14] Controller state now includes fleet_fill and route_pool saturation
# [NEW-15] Added MODE_POOL_RECOMBINE so RL can exploit route memory before full route reduction
# [NEW-16] Inline recombination is capped to once per segment for cleaner credit assignment
# [NEW-17] Transfer-weight loading is shape-safe across controller revisions
# [VER] version â†’ v9.8
# 

# In[1]:


# â”€â”€ Cell 1 : Install, Imports & Config â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# !pip install numba safetensors scipy -q

import glob, math, os, random, time, json, shutil
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from numba import njit
from scipy import stats

try:
    from scipy.optimize import Bounds, LinearConstraint, milp as _scipy_milp
    milp = _scipy_milp
    MILP_OK = True
except Exception:
    Bounds = LinearConstraint = milp = None
    MILP_OK = False

try:
    from safetensors.torch import save_file, load_file
    SAFETENSORS_OK = True
except ImportError:
    SAFETENSORS_OK = False
    print("\u26a0\ufe0f  safetensors not available \u2014 transfer learning save/load disabled")

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f'\u2705 Device : {DEVICE}')

BKS: Dict[str, Dict[str, float]] = {
    "RC101": {"nv": 14, "td": 1696.94}, "RC102": {"nv": 12, "td": 1554.75},
    "RC103": {"nv": 11, "td": 1261.67}, "RC104": {"nv": 10, "td": 1135.48},
    "RC105": {"nv": 13, "td": 1629.44}, "RC106": {"nv": 11, "td": 1424.73},
    "RC107": {"nv": 11, "td": 1230.48}, "RC108": {"nv": 10, "td": 1139.82},
    "RC201": {"nv": 4,  "td": 1406.94}, "RC202": {"nv": 3,  "td": 1365.64},
    "RC203": {"nv": 3,  "td": 1049.62}, "RC204": {"nv": 3,  "td": 798.46},
    "RC205": {"nv": 4,  "td": 1297.65}, "RC206": {"nv": 3,  "td": 1146.32},
    "RC207": {"nv": 3,  "td": 1061.14}, "RC208": {"nv": 3,  "td": 828.14},
}

def default_data_path() -> str:
    candidates = [
        "./data/Solomon", 
        "/kaggle/input/vrptw-benchmark-datasets/data/Solomon",
        "/kaggle/input/datasets/senju14/vrptw-benchmark-datasets/data/Solomon",
        "/content/vrptw-benchmark/data/Solomon",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]

def default_output_dir() -> str:
    return "/kaggle/working" if os.path.exists("/kaggle/working") else "/content"

@dataclass
class Config:
    data_path:   str   = default_data_path()
    output_dir:  str   = default_output_dir()

    alns_iterations:   int   = 2000
    destroy_ratio_min: float = 0.10
    destroy_ratio_max: float = 0.40
    temp_control:      float = 0.05
    temp_decay:        float = 0.99975
    sigma1:            int   = 33
    sigma2:            int   = 9
    sigma3:            int   = 3
    weight_decay:      float = 0.10
    segment_size:      int   = 50
    early_stop_patience: int = 600
    hybrid_iterations: int   = 2000
    n_runs: int = 4
    seed:   int = 42

    ctrl_state_dim:   int   = 12
    ctrl_hidden:      int   = 96
    ctrl_lr:          float = 3e-4
    ctrl_gamma:       float = 0.95
    ctrl_buffer:      int   = 8000
    ctrl_batch:       int   = 64
    ctrl_target_freq: int   = 100
    ctrl_eps_start:   float = 0.40
    ctrl_eps_end:     float = 0.02
    ctrl_eps_decay:   float = 0.9997
    ctrl_start:                     int = 24
    plateau_start:                  int = 72
    post_improve_intensify_segments: int = 3
    nv_increase_penalty: float = 15.0
    rl_recombine_min_routes: int = 24

    # [NEW-1] RoutePool / set-partition recombination
    route_pool_limit:            int   = 480
    route_pool_max_per_customer: int   = 18
    sp_time_limit:               float = 4.0
    sp_vehicle_penalty_scale:    float = 100.0

    # [NEW-2] Polish phase
    polish_iterations: int   = 200
    polish_patience:   int   = 80
    polish_ls_passes:  int   = 2

    # [NEW-6] Recombination passestrain it
    recombine_after_main_search: bool = True
    recombine_after_polish:      bool = True

    # DQN ablation
    dqn_state_dim:      int   = 13
    dqn_hidden:         int   = 128
    dqn_lr:             float = 1e-3
    dqn_gamma:          float = 0.99
    dqn_buffer:         int   = 8192
    dqn_batch:          int   = 64
    dqn_eps_start:      float = 1.0
    dqn_eps_end:        float = 0.05
    dqn_eps_decay:      float = 0.995
    dqn_target_freq:    int   = 20
    dqn_train_freq:     int   = 5
    dqn_vehicle_penalty:float = 5.0
    transfer_epochs:   int   = 2
    transfer_shuffle:  bool  = True

@dataclass(frozen=True)
class ModeSpec:
    name:             str
    destroy_scale:    float
    temp_boost:       float
    temp_decay_scale: float
    destroy_bias:     Tuple[float, ...]
    repair_bias:      Tuple[float, ...]
    ls_passes:        int
    use_recombine:    bool

# [v10] 6 modes. destroy_bias is length-6 to match N_D=6.
MODES: Tuple[ModeSpec, ...] = (
    ModeSpec("default",      1.00, 1.00,  1.000,
             (1.0, 1.0, 1.0, 1.0, 1.0, 0.8), (1.0, 1.0, 1.0, 1.0), 0, False),
    ModeSpec("intensify",    0.70, 0.98,  0.995,
             (0.8, 1.3, 1.2, 0.5, 1.0, 0.7), (1.3, 1.2, 0.8, 1.0), 1, False),
    ModeSpec("diversify",    1.35, 1.08,  1.002,
             (1.3, 0.9, 1.3, 1.4, 1.0, 0.7), (0.9, 1.0, 1.3, 1.0), 0, False),
    ModeSpec("tw_rescue",    1.10, 1.05,  1.000,
             (0.7, 0.9, 1.1, 0.8, 1.8, 0.4), (0.8, 1.0, 1.2, 1.8), 1, False),
    ModeSpec("pool_recombine", 0.90, 1.01,  0.997,
             (0.7, 1.2, 0.9, 1.1, 0.8, 1.8), (0.7, 1.1, 1.5, 0.9), 1, True),
    ModeSpec("route_reduce", 0.95, 1.02,  0.998,
             (0.6, 1.0, 0.9, 1.7, 0.6, 2.2), (0.8, 1.2, 1.5, 1.0), 1, True),
)

MODE_DEFAULT, MODE_INTENSIFY, MODE_DIVERSIFY = 0, 1, 2
MODE_TW_RESCUE, MODE_POOL_RECOMBINE, MODE_ROUTE_REDUCE = 3, 4, 5
CFG = Config()
OUTPUT_DIR = CFG.output_dir
print(f'\u2705 Config ready \u2014 v10.0 (alns_iter={CFG.alns_iterations}, hybrid_iter={CFG.hybrid_iterations}, n_runs={CFG.n_runs}, ctrl_start={CFG.ctrl_start}, route_reduce_start={CFG.plateau_start}, patience={CFG.early_stop_patience}, modes={len(MODES)}, MILP_OK={MILP_OK})')


# In[2]:


# â”€â”€ Cell 3 & 4: Data & Solution Model â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class Inst:
    def __init__(self, raw: Dict):
        self.name     = raw["name"]
        data          = raw["data"]
        self.capacity = raw["capacity"]
        self.coords        = data[:, 1:3]
        self.demands       = data[:, 3]
        self.ready_times   = data[:, 4]
        self.due_times     = data[:, 5]
        self.service_times = data[:, 6]
        self.horizon       = self.due_times[0]
        self.n             = len(data) - 1
        diff           = self.coords[:, None, :] - self.coords[None, :, :]
        self.dist      = np.sqrt((diff ** 2).sum(axis=2))
        self.max_dist  = self.dist.max()
        self.tw_width  = self.due_times - self.ready_times
        self.max_tw_width   = self.tw_width[1:].max() + 1e-9
        self.tw_tight_frac  = sum(
            1 for i in range(1, self.n + 1)
            if self.tw_width[i] < 0.2 * self.horizon
        ) / self.n
 
 
def load_datasets(base_path: str) -> Dict[str, List[Inst]]:
    datasets: Dict[str, List[Inst]] = {}
    for group in ("rc1", "rc2"):
        files  = sorted(glob.glob(os.path.join(base_path, f"{group}*.txt")))
        insts: List[Inst] = []
        for path in files:
            with open(path) as handle:
                lines = handle.readlines()
            name     = lines[0].strip()
            capacity = float(lines[4].strip().split()[1])
            rows     = [list(map(float, l.split())) for l in lines[9:] if l.strip()]
            insts.append(Inst({"name": name, "capacity": capacity,
                               "data": np.array(rows)}))
        datasets[group] = insts
    return datasets
 
 
@njit(cache=True)
def _route_cost(route: np.ndarray, dist: np.ndarray) -> float:
    cost = dist[0, route[0]]
    for i in range(len(route) - 1):
        cost += dist[route[i], route[i + 1]]
    return cost + dist[route[-1], 0]
 
 
@njit(cache=True)
def _route_ok(route: np.ndarray, demands: np.ndarray, capacity: float,
              ready: np.ndarray, due: np.ndarray, service: np.ndarray,
              dist: np.ndarray) -> bool:
    load = 0.0
    for node in route:
        load += demands[node]
    if load > capacity:
        return False
    current_time = 0.0
    prev = 0
    for node in route:
        current_time += dist[prev, node]
        if current_time < ready[node]:
            current_time = ready[node]
        if current_time > due[node]:
            return False
        current_time += service[node]
        prev = node
    return True
 
 
class Plan:
    __slots__ = ("routes", "inst", "_cost", "_ok", "algo")
 
    def __init__(self, routes: List[List[int]], inst: Inst, algo: str = ""):
        self.routes = [r for r in routes if r]
        self.inst   = inst
        self._cost: Optional[float] = None
        self._ok:   Optional[bool]  = None
        self.algo   = algo
 
    @property
    def cost(self) -> float:
        if self._cost is None:
            self._cost = sum(
                _route_cost(np.array(r, np.int64), self.inst.dist)
                for r in self.routes
            )
        return self._cost
 
    @property
    def feasible(self) -> bool:
        if self._ok is None:
            self._ok = all(
                _route_ok(np.array(r, np.int64), self.inst.demands,
                          self.inst.capacity, self.inst.ready_times,
                          self.inst.due_times, self.inst.service_times,
                          self.inst.dist)
                for r in self.routes
            )
        return self._ok
 
    @property
    def nv(self) -> int:
        return len(self.routes)
 
    def dominates(self, other: "Plan") -> bool:
        return self.nv < other.nv or (self.nv == other.nv and self.cost < other.cost)
 
    def copy(self) -> "Plan":
        return Plan([r[:] for r in self.routes], self.inst, self.algo)
 
    def invalidate(self) -> None:
        self._cost = None
        self._ok   = None
 
    def gap(self) -> Tuple[Optional[float], Optional[int]]:
        bks = BKS.get(self.inst.name)
        if not bks:
            return None, None
        return (self.cost - bks["td"]) / bks["td"] * 100, self.nv - bks["nv"]
 
    @property
    def on_time_rate(self) -> float:
        on_time = 0
        total   = 0
        for route in self.routes:
            current_time, prev = 0.0, 0
            for node in route:
                current_time += self.inst.dist[prev, node]
                current_time  = max(current_time, self.inst.ready_times[node])
                total        += 1
                if current_time <= self.inst.due_times[node]:
                    on_time += 1
                current_time += self.inst.service_times[node]
                prev = node
        return on_time / max(total, 1)
 
 
DATASETS = load_datasets(CFG.data_path)
RC1, RC2  = DATASETS.get("rc1", []), DATASETS.get("rc2", [])
print('âœ… Data & Solution model ready.')
 


# In[3]:


# â”€â”€ Cell 5: ALNS Operators â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _invalidate(plan: Plan) -> Plan:
    plan.invalidate()
    return plan
 
 
def _check_route(route: List[int], inst: Inst) -> bool:
    return bool(_route_ok(
        np.array(route, np.int64), inst.demands, inst.capacity,
        inst.ready_times, inst.due_times, inst.service_times, inst.dist,
    ))
 
 
def _best_insert_position(node: int, route: List[int],
                          inst: Inst) -> Tuple[float, Optional[int]]:
    best_cost, best_pos = float("inf"), None
    for pos in range(len(route) + 1):
        prev  = route[pos - 1] if pos > 0 else 0
        nxt   = route[pos]     if pos < len(route) else 0
        delta = inst.dist[prev, node] + inst.dist[node, nxt] - inst.dist[prev, nxt]
        if delta < best_cost and _check_route(route[:pos] + [node] + route[pos:], inst):
            best_cost, best_pos = delta, pos
    return best_cost, best_pos
 
 
def _insert_customer(plan: Plan, node: int, inst: Inst) -> None:
    best_cost, best_route, best_pos = float("inf"), None, None
    for ri, route in enumerate(plan.routes):
        delta, pos = _best_insert_position(node, route, inst)
        if pos is not None and delta < best_cost:
            best_cost, best_route, best_pos = delta, ri, pos
    if best_route is not None:
        plan.routes[best_route].insert(best_pos, node)
    else:
        plan.routes.append([node])
    plan.invalidate()
 
 
def op_random(plan: Plan, size: int) -> Tuple[Plan, List[int]]:
    nodes   = [n for r in plan.routes for n in r]
    removed = random.sample(nodes, min(size, len(nodes)))
    rs      = set(removed)
    plan.routes = [[n for n in r if n not in rs] for r in plan.routes]
    plan.routes = [r for r in plan.routes if r]
    return _invalidate(plan), removed
 
 
def op_worst(plan: Plan, size: int) -> Tuple[Plan, List[int]]:
    inst  = plan.inst
    gains: List[Tuple[float, int]] = []
    for route in plan.routes:
        for idx, node in enumerate(route):
            prev = route[idx - 1] if idx > 0 else 0
            nxt  = route[idx + 1] if idx < len(route) - 1 else 0
            gains.append((
                inst.dist[prev, node] + inst.dist[node, nxt] - inst.dist[prev, nxt],
                node,
            ))
    gains.sort(reverse=True)
    removed = [n for _, n in gains[:size]]
    rs      = set(removed)
    plan.routes = [[n for n in r if n not in rs] for r in plan.routes]
    plan.routes = [r for r in plan.routes if r]
    return _invalidate(plan), removed
 
 
def op_shaw(plan: Plan, size: int) -> Tuple[Plan, List[int]]:
    inst  = plan.inst
    nodes = [n for r in plan.routes for n in r]
    if not nodes:
        return plan, []
    seed    = random.choice(nodes)
    removed = [seed]
    rs      = {seed}
    max_dist = inst.max_dist + 1e-9
    max_tw   = max(inst.due_times - inst.ready_times) + 1e-9
    while len(removed) < size:
        candidates = [
            (n,
             0.5 * inst.dist[seed, n] / max_dist
             + 0.4 * abs(inst.ready_times[seed] - inst.ready_times[n]) / max_tw
             + 0.1 * abs(inst.demands[seed] - inst.demands[n]) / inst.capacity)
            for n in nodes if n not in rs
        ]
        if not candidates:
            break
        nxt = min(candidates, key=lambda x: x[1])[0]
        removed.append(nxt)
        rs.add(nxt)
    plan.routes = [[n for n in r if n not in rs] for r in plan.routes]
    plan.routes = [r for r in plan.routes if r]
    return _invalidate(plan), removed
 
 
def op_route(plan: Plan, size: int) -> Tuple[Plan, List[int]]:
    if len(plan.routes) <= 1:
        return op_random(plan, size)
    removed: List[int] = []
    route_ids: set     = set()
    for idx, route in sorted(enumerate(plan.routes), key=lambda x: len(x[1])):
        if len(removed) + len(route) <= size * 1.5:
            removed.extend(route)
            route_ids.add(idx)
        if len(removed) >= size:
            break
    plan.routes = [r for idx, r in enumerate(plan.routes) if idx not in route_ids] or [[]]
    return _invalidate(plan), removed
 
 
def op_tw_urgent(plan: Plan, size: int) -> Tuple[Plan, List[int]]:
    inst  = plan.inst
    nodes = [n for r in plan.routes for n in r]
    if not nodes:
        return plan, []
    removed = sorted(nodes, key=lambda n: inst.due_times[n] - inst.ready_times[n])[:size]
    rs      = set(removed)
    plan.routes = [[n for n in r if n not in rs] for r in plan.routes]
    plan.routes = [r for r in plan.routes if r]
    return _invalidate(plan), removed
 
 
def op_greedy(plan: Plan, removed: List[int]) -> Plan:
    inst = plan.inst
    for node in sorted(removed, key=lambda n: inst.due_times[n]):
        _insert_customer(plan, node, inst)
    return Plan(plan.routes, inst, plan.algo)
 
 
def _regret(plan: Plan, removed: List[int], k: int) -> Plan:
    inst      = plan.inst
    remaining = removed[:]
    while remaining:
        best_regret, chosen, choice = -float("inf"), None, None
        for node in remaining:
            options = sorted(
                (delta, ri, pos)
                for ri, route in enumerate(plan.routes)
                for delta, pos in [_best_insert_position(node, route, inst)]
                if pos is not None
            )
            if not options:
                continue
            if len(options) >= k:
                regret = sum(options[i][0] - options[0][0] for i in range(1, k))
            elif len(options) >= 2:
                regret = options[1][0] - options[0][0]
            else:
                regret = float("inf")
            if regret > best_regret:
                best_regret, chosen, choice = regret, node, options[0]
        if chosen is not None and choice is not None:
            _, ri, pos = choice
            plan.routes[ri].insert(pos, chosen)
            plan.invalidate()
            remaining.remove(chosen)
        else:
            for node in remaining:
                plan.routes.append([node])
            break
    return Plan(plan.routes, inst, plan.algo)
 
 
def op_regret_2(plan: Plan, removed: List[int]) -> Plan:
    return _regret(plan, removed, 2)
 
 
def op_regret_3(plan: Plan, removed: List[int]) -> Plan:
    return _regret(plan, removed, 3)
 
 
def op_tw_greedy(plan: Plan, removed: List[int]) -> Plan:
    inst = plan.inst
    for node in sorted(removed, key=lambda n: inst.due_times[n] - inst.ready_times[n]):
        _insert_customer(plan, node, inst)
    return Plan(plan.routes, inst, plan.algo)
 
 

# [NEW-4] Targets smallest/lightest routes for elimination
def op_route_eliminate(plan: Plan, size: int) -> Tuple[Plan, List[int]]:
    if len(plan.routes) <= 1:
        return op_random(plan, size)
    inst   = plan.inst
    ranked = sorted(
        enumerate(plan.routes),
        key=lambda item: (
            len(item[1]),
            sum(inst.demands[n] for n in item[1]) / max(inst.capacity, 1),
        ),
    )
    removed: List[int] = []
    removed_ids: set   = set()
    for idx, route in ranked:
        removed.extend(route)
        removed_ids.add(idx)
        if len(removed) >= max(2, size // 2):
            break
    plan.routes = [r for idx, r in enumerate(plan.routes) if idx not in removed_ids]
    return _invalidate(plan), removed


# [NEW-4] N_D=6 â€” op_route_eliminate at index 5
DESTROY = [op_random, op_worst, op_shaw, op_route, op_tw_urgent, op_route_eliminate]
REPAIR  = [op_greedy, op_regret_2, op_regret_3, op_tw_greedy]
N_D, N_R = len(DESTROY), len(REPAIR)
print(f'âœ… Operators: {N_D}D Ã— {N_R}R = {N_D * N_R} combos')
 
 


# In[4]:


# â”€â”€ Cell 6: Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _roulette(weights: np.ndarray) -> int:
    return int(np.random.choice(len(weights), p=weights / weights.sum()))
 
 
def _avg_slack(plan: Plan) -> float:
    inst       = plan.inst
    slack_sum  = 0.0
    count      = 0
    for route in plan.routes:
        current_time, prev = 0.0, 0
        for node in route:
            current_time += inst.dist[prev, node]
            current_time  = max(current_time, inst.ready_times[node])
            slack_sum    += inst.due_times[node] - current_time
            current_time += inst.service_times[node]
            prev          = node
            count        += 1
    return (slack_sum / count) / max(inst.horizon, 1) if count else 0.0
 
 
def _plan_spread(plan: Plan, inst: Inst) -> Tuple[float, float]:
    lengths = [len(r) for r in plan.routes] or [0]
    loads   = [sum(inst.demands[n] for n in r) for r in plan.routes] or [0]
    rb = float(np.std(lengths) / max(np.mean(lengths), 1)) if len(lengths) > 1 else 0.0
    lb = float(np.std(loads)   / max(inst.capacity, 1))
    return min(rb, 1.0), min(lb, 1.0)
 
 
def accept(cur: Plan, cand: Plan, temp: float) -> bool:
    if not cand.feasible:
        return False
    if cand.nv < cur.nv:
        return True
    if cand.nv == cur.nv:
        if cand.cost < cur.cost:
            return True
        return random.random() < math.exp(-(cand.cost - cur.cost) / max(temp, 1e-6))
    return False
 
 
def destroy_size(it: int, n_iters: int, cfg: Config,
                 n_customers: int, scale: float = 1.0) -> int:
    ratio = cfg.destroy_ratio_max - (
        (cfg.destroy_ratio_max - cfg.destroy_ratio_min) * (it / max(n_iters, 1))
    )
    ratio = min(cfg.destroy_ratio_max, max(cfg.destroy_ratio_min, ratio * scale))
    return max(3, int(ratio * n_customers))
 
 
def build_greedy(inst: Inst, algo: str = "") -> Plan:
    """Greedy construction heuristic with feasibility fallback."""
    def arrival(route, pos, node, arrivals):
        prev = route[pos - 1] if pos > 0 else 0
        t    = arrivals[pos - 1] if pos > 0 else 0.0
        t   += inst.dist[prev, node]
        return max(t, inst.ready_times[node])
 
    def feasible_insert(route, pos, node, arrivals, load):
        if load + inst.demands[node] > inst.capacity:
            return False, None
        t = arrival(route, pos, node, arrivals)
        if t > inst.due_times[node]:
            return False, None
        ft   = t + inst.service_times[node]
        prev = node
        for idx in range(pos, len(route)):
            nn  = route[idx]
            ft += inst.dist[prev, nn]
            ft  = max(ft, inst.ready_times[nn])
            if ft > inst.due_times[nn]:
                return False, None
            ft  += inst.service_times[nn]
            prev = nn
        return True, t
 
    def compute_arrivals(route):
        arr: List[float] = []
        t, prev = 0.0, 0
        for node in route:
            t += inst.dist[prev, node]
            t  = max(t, inst.ready_times[node])
            arr.append(t)
            t   += inst.service_times[node]
            prev = node
        return arr
 
    def best_insert_cost(route, node, arrivals, load):
        best_cost, best_pos = float("inf"), None
        for pos in range(len(route) + 1):
            ok, _ = feasible_insert(route, pos, node, arrivals, load)
            if not ok:
                continue
            prev  = route[pos - 1] if pos > 0 else 0
            nxt   = route[pos]     if pos < len(route) else 0
            delta = inst.dist[prev, node] + inst.dist[node, nxt] - inst.dist[prev, nxt]
            if delta < best_cost:
                best_cost, best_pos = delta, pos
        return best_cost, best_pos
 
    unrouted = list(range(1, inst.n + 1))
    routes: List[List[int]] = []
    while unrouted:
        seed = max(unrouted, key=lambda n: inst.dist[0, n])
        if max(inst.dist[0, seed], inst.ready_times[seed]) > inst.due_times[seed]:
            seed = min(unrouted, key=lambda n: inst.due_times[n])
        route    = [seed]
        load     = inst.demands[seed]
        arrivals = [max(inst.dist[0, seed], inst.ready_times[seed])]
        unrouted.remove(seed)
        improved = True
        while improved and unrouted:
            improved = False
            best_reg, best_node, best_pos = -float("inf"), None, None
            for node in unrouted:
                c1, pos = best_insert_cost(route, node, arrivals, load)
                if pos is None:
                    continue
                c2 = inst.dist[0, node] + inst.dist[node, 0] - c1
                if c2 > best_reg:
                    best_reg, best_node, best_pos = c2, node, pos
            if best_node is not None:
                route.insert(best_pos, best_node)
                load    += inst.demands[best_node]
                arrivals = compute_arrivals(route)
                unrouted.remove(best_node)
                improved = True
        routes.append(route)
 
    plan = Plan(routes, inst, algo)
    if plan.feasible:
        return plan
 
    # Fallback: time-window sorted insertion
    customers    = sorted(range(1, inst.n + 1),
                          key=lambda n: (inst.due_times[n], inst.ready_times[n]))
    unrouted_set = set(customers)
    fallback:    List[List[int]] = []
    while unrouted_set:
        route: List[int] = []
        node = 0; load = 0.0; t = 0.0
        while unrouted_set:
            feasible = [
                c for c in unrouted_set
                if load + inst.demands[c] <= inst.capacity
                and t + inst.dist[node, c] <= inst.due_times[c]
            ]
            if not feasible:
                break
            nxt  = min(feasible, key=lambda c: inst.dist[node, c])
            route.append(nxt)
            unrouted_set.remove(nxt)
            load += inst.demands[nxt]
            t     = (max(t + inst.dist[node, nxt], inst.ready_times[nxt])
                     + inst.service_times[nxt])
            node  = nxt
        if route:
            fallback.append(route)
        elif unrouted_set:
            nxt = next(iter(unrouted_set))
            fallback.append([nxt])
            unrouted_set.remove(nxt)
    return Plan(fallback, inst, algo)
 
 
print('âœ… Helpers ready.')
 


# In[5]:


# â”€â”€ Cell 6b: RoutePool + Local Search (v9.8) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
from dataclasses import dataclass as _dc

@_dc(frozen=True)
class RouteRecord:
    nodes: Tuple[int, ...]
    cost:  float
    load:  float
    slack: float


def _route_cost_list(route: List[int], inst: Inst) -> float:
    if not route:
        return 0.0
    return float(_route_cost(np.array(route, np.int64), inst.dist))

def _route_load(route: List[int], inst: Inst) -> float:
    return float(sum(inst.demands[n] for n in route))

def _route_avg_slack(route: List[int], inst: Inst) -> float:
    if not route:
        return 0.0
    s, t, prev = 0.0, 0.0, 0
    for n in route:
        t += inst.dist[prev, n]
        t  = max(t, inst.ready_times[n])
        s += inst.due_times[n] - t
        t += inst.service_times[n]
        prev = n
    return s / len(route)

def _fleet_fill(plan: Plan) -> float:
    if not plan.routes:
        return 0.0
    return float(np.mean([
        _route_load(r, plan.inst) / max(plan.inst.capacity, 1)
        for r in plan.routes
    ]))


class RoutePool:
    def __init__(self, inst: Inst, cfg: Config):
        self.inst = inst
        self.cfg  = cfg
        self._routes: Dict[Tuple[int, ...], RouteRecord] = {}

    def _priority(self, rec: RouteRecord) -> Tuple[float, ...]:
        lr = rec.load / max(self.inst.capacity, 1)
        cp = rec.cost / max(len(rec.nodes), 1)
        return (-len(rec.nodes), cp, -lr, -rec.slack)

    def _trim(self) -> None:
        limit = self.cfg.route_pool_limit
        if len(self._routes) <= limit:
            return
        usage: Dict[int, int] = {}
        kept:  Dict[Tuple[int, ...], RouteRecord] = {}
        ranked = sorted(self._routes.values(), key=self._priority)
        for rec in ranked:
            if len(kept) >= limit:
                break
            under = all(usage.get(n, 0) < self.cfg.route_pool_max_per_customer
                        for n in rec.nodes)
            if under or len(kept) < limit // 3:
                kept[rec.nodes] = rec
                for n in rec.nodes:
                    usage[n] = usage.get(n, 0) + 1
        if len(kept) < limit:
            for rec in ranked:
                if rec.nodes not in kept:
                    kept[rec.nodes] = rec
                if len(kept) >= limit:
                    break
        self._routes = kept

    def add_route(self, route: List[int]) -> None:
        if not route or not _check_route(route, self.inst):
            return
        key = tuple(route)
        if key in self._routes:
            return
        self._routes[key] = RouteRecord(
            nodes=key,
            cost=_route_cost_list(route, self.inst),
            load=_route_load(route, self.inst),
            slack=_route_avg_slack(route, self.inst),
        )
        self._trim()

    def add_plan(self, plan: Plan) -> None:
        for r in plan.routes:
            self.add_route(r)

    def records(self, incumbent: Optional[Plan] = None) -> List[RouteRecord]:
        recs = dict(self._routes)
        if incumbent is not None:
            for r in incumbent.routes:
                k = tuple(r)
                recs[k] = RouteRecord(
                    nodes=k,
                    cost=_route_cost_list(r, self.inst),
                    load=_route_load(r, self.inst),
                    slack=_route_avg_slack(r, self.inst),
                )
        return sorted(recs.values(), key=self._priority)


def _sp_vehicle_penalty(inst: Inst, cfg: Config) -> float:
    return cfg.sp_vehicle_penalty_scale * max(inst.max_dist, 1.0) * max(inst.n, 1)


def _milp_recombine(route_records: List[RouteRecord], inst: Inst,
                    cfg: Config, nv_ceiling: Optional[int] = None) -> Optional[Plan]:
    if not MILP_OK or not route_records:
        return None
    n_r = len(route_records)
    cover = np.zeros((inst.n, n_r), dtype=float)
    for j, rec in enumerate(route_records):
        for node in rec.nodes:
            cover[node - 1, j] = 1.0
    if np.any(cover.sum(axis=1) == 0):
        return None
    constraints = [LinearConstraint(cover, lb=np.ones(inst.n), ub=np.ones(inst.n))]
    if nv_ceiling is not None:
        constraints.append(
            LinearConstraint(np.ones((1, n_r)), lb=np.array([0.0]),
                             ub=np.array([float(nv_ceiling)]))
        )
    costs = np.array([_sp_vehicle_penalty(inst, cfg) + rec.cost for rec in route_records])
    result = milp(
        c=costs, constraints=constraints,
        integrality=np.ones(n_r, dtype=int),
        bounds=Bounds(np.zeros(n_r), np.ones(n_r)),
        options={"time_limit": float(cfg.sp_time_limit), "disp": False},
    )
    if result is None or not getattr(result, "success", False) or result.x is None:
        return None
    chosen = [list(route_records[j].nodes) for j, v in enumerate(result.x) if v >= 0.5]
    plan = Plan(chosen, inst, "SP-RECOMBINE")
    return plan if plan.feasible else None


def _greedy_recombine(route_records: List[RouteRecord], incumbent: Plan,
                      nv_ceiling: Optional[int] = None) -> Plan:
    uncovered = set(range(1, incumbent.inst.n + 1))
    selected: List[List[int]] = []
    used: set = set()
    while uncovered:
        best_rec, best_score = None, -float("inf")
        for rec in route_records:
            if rec.nodes in used:
                continue
            gain = len(set(rec.nodes) & uncovered)
            if gain == 0:
                continue
            score = gain * 10.0 + len(rec.nodes) - rec.cost / max(len(rec.nodes), 1)
            if score > best_score:
                best_score, best_rec = score, rec
        if best_rec is None:
            break
        selected.append(list(best_rec.nodes))
        used.add(best_rec.nodes)
        uncovered.difference_update(best_rec.nodes)
        if nv_ceiling is not None and len(selected) > nv_ceiling:
            return incumbent.copy()
    plan = Plan(selected, incumbent.inst, "SP-GREEDY")
    for node in sorted(uncovered):
        _insert_customer(plan, node, incumbent.inst)
    return plan if plan.feasible else incumbent.copy()


def recombine_with_route_pool(incumbent: Plan, pool: RoutePool,
                               cfg: Config,
                               nv_ceiling: Optional[int] = None) -> Plan:
    pool.add_plan(incumbent)
    recs = pool.records(incumbent)
    if not recs:
        return incumbent.copy()
    candidate = _milp_recombine(recs, incumbent.inst, cfg, nv_ceiling=nv_ceiling)
    if candidate is None:
        candidate = _greedy_recombine(recs, incumbent, nv_ceiling=nv_ceiling)
    if nv_ceiling is not None and candidate.nv > nv_ceiling:
        return incumbent.copy()
    return candidate if candidate.dominates(incumbent) else incumbent.copy()


# [NEW-5] SA acceptance with hard NV ceiling
def accept_with_nv_ceiling(cur: Plan, cand: Plan, temp: float, nv_ceiling: int) -> bool:
    if not cand.feasible or cand.nv > nv_ceiling:
        return False
    if cand.nv < cur.nv:
        return True
    if cand.nv == cur.nv:
        if cand.cost < cur.cost:
            return True
        return random.random() < math.exp(-(cand.cost - cur.cost) / max(temp, 1e-6))
    return False


# [v10] 2-opt + relocate + swap + route-compaction local search
def _two_opt_best(route: List[int], inst: Inst) -> List[int]:
    if len(route) < 4:
        return route[:]
    best = route[:]
    best_cost = _route_cost_list(best, inst)
    for i in range(len(route) - 2):
        for j in range(i + 2, len(route)):
            cand = route[:i] + list(reversed(route[i:j+1])) + route[j+1:]
            if not _check_route(cand, inst):
                continue
            cc = _route_cost_list(cand, inst)
            if cc + 1e-9 < best_cost:
                best, best_cost = cand, cc
    return best


def _best_relocate(plan: Plan, nv_ceiling: Optional[int] = None):
    inst = plan.inst
    best_delta = -1e-9
    best_move  = None
    for si, sr in enumerate(plan.routes):
        sc = _route_cost_list(sr, inst)
        for np_, node in enumerate(sr):
            sr_new = sr[:np_] + sr[np_+1:]
            if sr_new and not _check_route(sr_new, inst):
                continue
            sr_new_c = _route_cost_list(sr_new, inst)
            for di, dr in enumerate(plan.routes):
                if di == si:
                    continue
                dc = _route_cost_list(dr, inst)
                for ip in range(len(dr) + 1):
                    dr_new = dr[:ip] + [node] + dr[ip:]
                    if not _check_route(dr_new, inst):
                        continue
                    new_nv = plan.nv - (1 if not sr_new else 0)
                    if nv_ceiling is not None and new_nv > nv_ceiling:
                        continue
                    delta = sr_new_c + _route_cost_list(dr_new, inst) - sc - dc
                    if new_nv < plan.nv:
                        delta -= 1000.0
                    if delta < best_delta:
                        best_delta, best_move = delta, (si, np_, di, ip)
    return best_move


def _apply_relocate(plan: Plan, move: Tuple[int, int, int, int]) -> Plan:
    si, np_, di, ip = move
    routes = [r[:] for r in plan.routes]
    node   = routes[si].pop(np_)
    if si < di and len(routes[si]) == 0:
        di -= 1
    routes = [r for r in routes if r]
    routes[di].insert(ip, node)
    return Plan(routes, plan.inst, plan.algo)


def _best_swap(plan: Plan):
    inst = plan.inst
    best_delta = -1e-9
    best_move  = None
    for si, sr in enumerate(plan.routes):
        sc = _route_cost_list(sr, inst)
        for di in range(si + 1, len(plan.routes)):
            dr = plan.routes[di]
            dc = _route_cost_list(dr, inst)
            for sp, s_node in enumerate(sr):
                for dp, d_node in enumerate(dr):
                    if s_node == d_node:
                        continue
                    sr_new = sr[:]
                    dr_new = dr[:]
                    sr_new[sp], dr_new[dp] = d_node, s_node
                    if not _check_route(sr_new, inst) or not _check_route(dr_new, inst):
                        continue
                    delta = (_route_cost_list(sr_new, inst)
                             + _route_cost_list(dr_new, inst) - sc - dc)
                    if delta < best_delta:
                        best_delta, best_move = delta, (si, sp, di, dp)
    return best_move


def _apply_swap(plan: Plan, move: Tuple[int, int, int, int]) -> Plan:
    si, sp, di, dp = move
    routes = [r[:] for r in plan.routes]
    routes[si][sp], routes[di][dp] = routes[di][dp], routes[si][sp]
    return Plan(routes, plan.inst, plan.algo)


def _try_route_compact(plan: Plan,
                       nv_ceiling: Optional[int] = None) -> Optional[Plan]:
    if len(plan.routes) <= 1:
        return None
    inst = plan.inst
    ranked = sorted(
        range(len(plan.routes)),
        key=lambda idx: (
            len(plan.routes[idx]),
            _route_load(plan.routes[idx], inst),
            _route_cost_list(plan.routes[idx], inst),
        ),
    )
    for ridx in ranked:
        source = plan.routes[ridx]
        others = [r[:] for i, r in enumerate(plan.routes) if i != ridx]
        success = True
        for node in sorted(source,
                           key=lambda n: (inst.due_times[n] - inst.ready_times[n],
                                          -inst.demands[n])):
            best_cost, best_route, best_pos = float("inf"), None, None
            for oi, route in enumerate(others):
                delta, pos = _best_insert_position(node, route, inst)
                if pos is not None and delta < best_cost:
                    best_cost, best_route, best_pos = delta, oi, pos
            if best_route is None:
                success = False
                break
            others[best_route].insert(best_pos, node)
        if not success:
            continue
        cand = Plan([r for r in others if r], inst, plan.algo)
        if not cand.feasible:
            continue
        if nv_ceiling is not None and cand.nv > nv_ceiling:
            continue
        if cand.dominates(plan) or (cand.nv == plan.nv and cand.cost + 1e-9 < plan.cost):
            return cand
    return None


def local_search(plan: Plan, max_passes: int = 1,
                 nv_ceiling: Optional[int] = None) -> Plan:
    best = plan.copy()
    for _ in range(max_passes):
        improved = False
        routes = []
        for r in best.routes:
            nr = _two_opt_best(r, best.inst)
            routes.append(nr)
            if nr != r:
                improved = True
        best = Plan(routes, best.inst, best.algo)
        while True:
            move = _best_relocate(best, nv_ceiling=nv_ceiling)
            if move is not None:
                cand = _apply_relocate(best, move)
                if cand.feasible and (cand.dominates(best)
                                      or (cand.nv == best.nv and cand.cost + 1e-9 < best.cost)):
                    best = cand
                    improved = True
                    continue
            move = _best_swap(best)
            if move is not None:
                cand = _apply_swap(best, move)
                if cand.feasible and cand.cost + 1e-9 < best.cost:
                    best = cand
                    improved = True
                    continue
            compact = _try_route_compact(best, nv_ceiling=nv_ceiling)
            if compact is not None:
                best = compact
                improved = True
                continue
            break
        if not improved:
            break
    return best


print("\u2705 RoutePool + LocalSearch ready.")


# In[6]:


# â”€â”€ Cell 7: Neural Networks â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class ReplayBuffer:
    def __init__(self, capacity: int):
        self.buf: Deque[Tuple] = deque(maxlen=capacity)
 
    def push(self, *transition) -> None:
        self.buf.append(transition)
 
    def sample(self, batch_size: int):
        s, a, r, ns, d = zip(*random.sample(self.buf, batch_size))
        return (np.array(s,  np.float32), np.array(a,  np.int64),
                np.array(r,  np.float32), np.array(ns, np.float32),
                np.array(d,  np.float32))
 
    def __len__(self) -> int:
        return len(self.buf)
 
 
class QNet(nn.Module):
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int):
        super().__init__()
        hid2 = max(hidden_dim // 2, 32)
        self.trunk = nn.Sequential(
            nn.Linear(state_dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.ReLU(),
        )
        self.value_head = nn.Sequential(
            nn.Linear(hidden_dim, hid2), nn.ReLU(),
            nn.Linear(hid2, 1),
        )
        self.adv_head = nn.Sequential(
            nn.Linear(hidden_dim, hid2), nn.ReLU(),
            nn.Linear(hid2, action_dim),
        )
 
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.trunk(x)
        v = self.value_head(h)
        a = self.adv_head(h)
        return v + a - a.mean(dim=1, keepdim=True)
 
 
print('âœ… QNet ready.')
 


# In[7]:


# â”€â”€ Cell 8: ALNS Solver â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class ALNSSolver:
    def __init__(self, inst: Inst, cfg: Config):
        self.inst = inst
        self.cfg  = cfg
 
    def solve(self, seed: Optional[int] = None,
              init: Optional[Plan] = None) -> Tuple[Plan, List[float]]:
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
        cfg  = self.cfg
        cur  = init.copy() if init else build_greedy(self.inst, "ALNS")
        best = cur.copy()
        temp = cfg.temp_control * cur.cost / math.log(2)
        dw   = np.ones(N_D)
        rw   = np.ones(N_R)
        seg_scores = np.zeros((N_D, N_R))
        seg_counts = np.zeros((N_D, N_R))
        history    = [best.cost]
        no_imp     = 0
 
        for it in range(cfg.alns_iterations):
            di   = _roulette(dw)
            ri   = _roulette(rw)
            size = destroy_size(it, cfg.alns_iterations, cfg, self.inst.n)
            dest, removed = DESTROY[di](cur.copy(), size)
            cand          = REPAIR[ri](dest, removed)
            score         = 0
            if accept(cur, cand, temp):
                if cand.dominates(best):
                    best   = cand.copy()
                    score  = cfg.sigma1
                    no_imp = 0
                elif cand.dominates(cur):
                    score  = cfg.sigma2
                    no_imp = 0
                else:
                    score   = cfg.sigma3
                    no_imp += 1
                cur = cand
            else:
                no_imp += 1
 
            seg_scores[di, ri] += score
            seg_counts[di, ri] += 1
 
            if (it + 1) % cfg.segment_size == 0:
                for d in range(N_D):
                    for r in range(N_R):
                        if seg_counts[d, r] > 0:
                            avg    = seg_scores[d, r] / seg_counts[d, r]
                            dw[d]  = dw[d] * (1 - cfg.weight_decay) + avg * cfg.weight_decay
                            rw[r]  = rw[r] * (1 - cfg.weight_decay) + avg * cfg.weight_decay
                seg_scores[:] = 0
                seg_counts[:] = 0
                dw = np.maximum(dw, 0.1)
                rw = np.maximum(rw, 0.1)
 
            temp *= cfg.temp_decay
            history.append(best.cost)
            if no_imp >= cfg.early_stop_patience:
                break
 
        best.algo = "ALNS"
        return best, history
 
 
print('âœ… ALNS ready.')
 


# In[8]:


# â”€â”€ Cell 9: DQN Solver (ablation only) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class DQNNet(nn.Module):
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, action_dim),
        )
 
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)
 
 
class DQNSolver:
    """Pure constructive RL â€” ablation study only. Not competitive."""
 
    def __init__(self, inst: Inst, cfg: Config = CFG):
        self.inst = inst
        self.cfg  = cfg
        self.q    = DQNNet(cfg.dqn_state_dim, inst.n + 1, cfg.dqn_hidden).to(DEVICE)
        self.q_t  = DQNNet(cfg.dqn_state_dim, inst.n + 1, cfg.dqn_hidden).to(DEVICE)
        self.q_t.load_state_dict(self.q.state_dict())
        self.opt  = optim.Adam(self.q.parameters(), lr=cfg.dqn_lr)
        self.buf  = ReplayBuffer(cfg.dqn_buffer)
        self.eps  = cfg.dqn_eps_start
 
    def _state(self, node, visited, load, t):
        inst = self.inst
        uv   = inst.n - len(visited)
        feas = [n for n in range(1, inst.n + 1)
                if n not in visited
                and load + inst.demands[n] <= inst.capacity
                and t + inst.dist[node, n] <= inst.due_times[n]]
        nf   = len(feas)
        if feas:
            slacks = [inst.due_times[n] - (t + inst.dist[node, n]) for n in feas]
            ms = min(slacks) / max(inst.horizon, 1)
            av = (sum(slacks) / nf) / max(inst.horizon, 1)
            uf = sum(1 for s in slacks if s < 0.1 * inst.horizon) / max(nf, 1)
            aw = (sum(inst.tw_width[n] for n in feas) / nf) / max(inst.max_tw_width, 1)
        else:
            ms = av = uf = aw = 0.0
        return np.array([
            load / inst.capacity, t / max(inst.horizon, 1),
            len(visited) / inst.n, (inst.capacity - load) / inst.capacity,
            uv / inst.n, nf / max(uv, 1),
            inst.coords[node, 0] / 100, inst.coords[node, 1] / 100,
            inst.demands[node] / inst.capacity,
            ms, av, uf, aw,
        ], dtype=np.float32)
 
    def _acts(self, node, visited, load, t):
        inst = self.inst
        acts = [0]
        for n in range(1, inst.n + 1):
            if (n not in visited
                    and load + inst.demands[n] <= inst.capacity
                    and t + inst.dist[node, n] <= inst.due_times[n]):
                acts.append(n)
        return acts
 
    def _sel(self, state, feasible):
        if random.random() < self.eps:
            return random.choice(feasible)
        with torch.no_grad():
            q = self.q(torch.tensor(state).unsqueeze(0).to(DEVICE)).cpu().numpy()[0]
        return max(feasible, key=lambda a: q[a])
 
    def _train(self):
        if len(self.buf) < self.cfg.dqn_batch:
            return
        s, a, r, ns, d = self.buf.sample(self.cfg.dqn_batch)
        s  = torch.tensor(s).to(DEVICE)
        a  = torch.tensor(a, dtype=torch.long).to(DEVICE)
        r  = torch.tensor(r).to(DEVICE)
        ns = torch.tensor(ns).to(DEVICE)
        d  = torch.tensor(d).to(DEVICE)
        qp = self.q(s).gather(1, a.unsqueeze(1)).squeeze(1)
        with torch.no_grad():
            tgt = r + self.cfg.dqn_gamma * self.q_t(ns).max(1)[0] * (1 - d)
        loss = F.mse_loss(qp, tgt)
        self.opt.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.q.parameters(), 1.0)
        self.opt.step()
 
    def _episode(self):
        inst    = self.inst
        visited: set         = set()
        routes: List[List[int]] = []
        trans:  List         = []
        while len(visited) < inst.n:
            route: List[int] = []
            node = 0; load = 0.0; t = 0.0; is_new = True
            while True:
                state = self._state(node, visited, load, t)
                feas  = self._acts(node, visited, load, t)
                if len(feas) == 1:
                    break
                action = self._sel(state, feas)
                if action == 0:
                    break
                dv  = inst.dist[node, action]
                rew = -dv / max(inst.max_dist, 1)
                if is_new and routes:
                    rew -= self.cfg.dqn_vehicle_penalty / inst.n
                is_new  = False
                load   += inst.demands[action]
                t       = max(t + dv, inst.ready_times[action]) + inst.service_times[action]
                visited.add(action)
                route.append(action)
                ns   = self._state(action, visited, load, t)
                done = float(len(visited) == inst.n)
                trans.append((state, action, rew, ns, done))
                node = action
            if route:
                routes.append(route)
        return Plan(routes, inst, "DQN"), trans
 
    def solve(self, seed: Optional[int] = None) -> Tuple[Plan, List[float]]:
        if seed is not None:
            random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
        cfg  = self.cfg
        best = None
        bc   = float("inf")
        hist: List[float] = []
        self.eps = cfg.dqn_eps_start
        n_eps    = max(50, cfg.alns_iterations // self.inst.n)
        for ep in range(n_eps):
            plan, trans = self._episode()
            if plan.feasible and trans:
                bonus    = max(0, (bc - plan.cost) / bc * 10) if bc < float("inf") else 1.0
                s, a, r, ns, d = trans[-1]
                trans[-1] = (s, a, r + bonus, ns, d)
                if plan.cost < bc:
                    bc   = plan.cost
                    best = plan.copy()
            for tr in trans:
                self.buf.push(*tr)
            if ep % cfg.dqn_train_freq == 0:
                for _ in range(min(5, len(self.buf) // max(cfg.dqn_batch, 1))):
                    self._train()
            if ep % cfg.dqn_target_freq == 0:
                self.q_t.load_state_dict(self.q.state_dict())
            self.eps = max(cfg.dqn_eps_end, self.eps * cfg.dqn_eps_decay)
            hist.append(bc if bc < float("inf") else float("nan"))
        if best is None:
            best = build_greedy(self.inst, "DQN")
        best.algo = "DQN"
        return best, hist
 
 
print('âœ… DQN solver ready.')


# In[9]:


# ── Cell 10: RLALNSSolver — Pure DDQN Operator Selection (v11) ──────────────
#
# KEY CHANGE vs v10: No roulette wheel in this solver.
# DDQN is the ONLY operator selector, firing every iteration.
# This eliminates the competing-signal problem that plagued v9.x/v10.
#
# Architecture:
#   State:   14D per-iteration vector
#   Action:  N_D × N_R = 24 operator pairs
#   Reward:  hierarchical per-iteration (dense signal)
#   Network: Dueling Double DQN + LayerNorm (same QNet as ALNS baseline)
#   Buffer:  pre-filled 300 random episodes before search begins
#   Polish:  RoutePool + 2-opt + fixed-NV intensification (unchanged)
#   Transfer: train on RC1 → frozen zero-shot on RC2

N_ACTIONS = N_D * N_R   # 24


class RLALNSSolver:
    algo_name = "DDQN-ALNS"

    def __init__(self, inst: Inst, cfg: Config):
        self.inst      = inst
        self.cfg       = cfg
        self.q         = QNet(14, N_ACTIONS, cfg.ctrl_hidden).to(DEVICE)
        self.q_t       = QNet(14, N_ACTIONS, cfg.ctrl_hidden).to(DEVICE)
        self.q_t.load_state_dict(self.q.state_dict())
        self.opt       = optim.Adam(self.q.parameters(), lr=cfg.ctrl_lr)
        self.buf       = ReplayBuffer(cfg.ctrl_buffer)
        self.eps       = cfg.ctrl_eps_start
        self.step      = 0
        self.op_counts: Dict[Tuple[int,int], int] = {}

    # ── state ────────────────────────────────────────────────────────────────
    def _state(self, cur: Plan, best: Plan, no_imp: int,
               temp: float, it: int, n_iters: int,
               imp_rate: float) -> np.ndarray:
        inst = self.inst
        rb, lb = _plan_spread(cur, inst)
        tw_tight = float(np.mean(
            (inst.due_times[1:] - inst.ready_times[1:]) < 0.2 * inst.horizon
        ))
        avg_slack = _avg_slack(cur)
        cost_gap  = (cur.cost - best.cost) / max(best.cost, 1.0)
        nv_ratio  = cur.nv / max(self._init_nv, 1)
        return np.array([
            cost_gap,                                      # 0
            nv_ratio,                                      # 1
            it / max(n_iters, 1),                          # 2  progress
            imp_rate,                                      # 3
            rb,                                            # 4  route balance
            lb,                                            # 5  load balance
            temp / max(self._t0, 1e-9),                    # 6
            no_imp / max(self.cfg.early_stop_patience, 1), # 7
            tw_tight,                                      # 8
            avg_slack,                                     # 9
            float(cur.nv - best.nv) / max(self._init_nv, 1), # 10
            float(len(self.buf)) / max(self.cfg.ctrl_buffer, 1), # 11 buf fill
            cost_gap * nv_ratio,                           # 12 interaction
            float(it % self.cfg.segment_size) / self.cfg.segment_size,  # 13
        ], dtype=np.float32)

    # ── action ───────────────────────────────────────────────────────────────
    def _act(self, state: np.ndarray) -> Tuple[int, int, int]:
        """Returns (action_idx, di, ri)."""
        if random.random() < self.eps:
            action = random.randrange(N_ACTIONS)
        else:
            with torch.no_grad():
                q_vals = self.q(
                    torch.tensor(state).unsqueeze(0).to(DEVICE)
                )[0].cpu().numpy()
            action = int(q_vals.argmax())
        di = action // N_R
        ri = action  % N_R
        return action, di, ri

    # ── reward ───────────────────────────────────────────────────────────────
    def _reward(self, cur_before: Plan, best_before: Plan,
                cand: Plan, best_after: Plan, accepted: bool) -> float:
        if not accepted:
            return -0.05
        r = 0.1  # accepted bonus
        nv_delta = best_before.nv - best_after.nv
        if nv_delta > 0:
            r += 2.0 * nv_delta          # NV reduction — primary signal
        elif best_after.cost < best_before.cost:
            r += 0.5 * (best_before.cost - best_after.cost) / max(best_before.cost, 1) * 100
        if cand.nv > cur_before.nv:
            r -= 0.5                     # soft penalty for adding a vehicle
        return float(r)

    # ── training ─────────────────────────────────────────────────────────────
    def _train(self) -> None:
        self.step += 1
        if len(self.buf) < self.cfg.ctrl_batch:
            return
        s, a, r, ns, d = self.buf.sample(self.cfg.ctrl_batch)
        s  = torch.tensor(s).to(DEVICE)
        a  = torch.tensor(a, dtype=torch.long).to(DEVICE)
        r  = torch.tensor(r).to(DEVICE)
        ns = torch.tensor(ns).to(DEVICE)
        d  = torch.tensor(d).to(DEVICE)
        qp = self.q(s).gather(1, a.unsqueeze(1)).squeeze(1)
        with torch.no_grad():
            best_a = self.q(ns).argmax(1).unsqueeze(1)
            target = r + self.cfg.ctrl_gamma * self.q_t(ns).gather(1, best_a).squeeze(1) * (1 - d)
        loss = F.smooth_l1_loss(qp, target)
        self.opt.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.q.parameters(), 1.0)
        self.opt.step()
        if self.step % self.cfg.ctrl_target_freq == 0:
            self.q_t.load_state_dict(self.q.state_dict())
        self.eps = max(self.cfg.ctrl_eps_end, self.eps * self.cfg.ctrl_eps_decay)

    # ── pre-fill buffer ──────────────────────────────────────────────────────
    def _prefill(self, n_episodes: int = 300) -> None:
        """Random operator selection to seed the replay buffer before search."""
        inst = self.inst
        cfg  = self.cfg
        for _ in range(n_episodes):
            plan = build_greedy(inst, "prefill")
            best = plan.copy()
            temp = cfg.temp_control * plan.cost / math.log(2)
            for it in range(min(50, cfg.hybrid_iterations)):
                action = random.randrange(N_ACTIONS)
                di, ri = action // N_R, action % N_R
                size   = destroy_size(it, 50, cfg, inst.n)
                dest, removed = DESTROY[di](plan.copy(), size)
                cand          = REPAIR[ri](dest, removed)
                st   = np.zeros(14, dtype=np.float32)
                nst  = np.zeros(14, dtype=np.float32)
                acc  = accept(plan, cand, temp)
                best_after = best.copy()
                if acc:
                    plan = cand
                    if cand.dominates(best):
                        best_after = cand.copy()
                r = self._reward(plan, best, cand, best_after, acc)
                self.buf.push(st, action, r, nst, 0.0)
                best = best_after
                temp *= cfg.temp_decay

    # ── weight save/load for transfer ────────────────────────────────────────
    def clone_weights(self) -> Dict:
        return {k: v.clone().cpu() for k, v in self.q.state_dict().items()}

    def load_weights(self, weights: Dict) -> None:
        self.q.load_state_dict({k: v.to(DEVICE) for k, v in weights.items()})
        self.q_t.load_state_dict(self.q.state_dict())

    # ── main solve ───────────────────────────────────────────────────────────
    def solve(self, seed: Optional[int] = None,
              frozen: bool = False) -> Tuple[Plan, List[float]]:
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
            torch.manual_seed(seed)

        cfg  = self.cfg
        self.eps = cfg.ctrl_eps_start if not frozen else 0.0
        self.step = 0
        self.op_counts = {}

        cur  = build_greedy(self.inst, self.algo_name)
        best = cur.copy()
        self._init_nv = cur.nv
        self._t0      = cfg.temp_control * cur.cost / math.log(2)
        temp          = self._t0
        pool          = RoutePool(self.inst, cfg)
        pool.add_plan(cur)

        history: List[float]       = [best.cost]
        recent_imp: Deque[int]     = deque(maxlen=cfg.segment_size)
        no_imp = 0

        # Pre-fill buffer with random transitions (only when training)
        if not frozen and len(self.buf) < 300:
            self._prefill(300)

        for it in range(cfg.hybrid_iterations):
            imp_rate = sum(recent_imp) / max(len(recent_imp), 1)
            state    = self._state(cur, best, no_imp, temp, it,
                                   cfg.hybrid_iterations, imp_rate)

            action, di, ri = self._act(state)
            size            = destroy_size(it, cfg.hybrid_iterations, cfg, self.inst.n)
            dest, removed   = DESTROY[di](cur.copy(), size)
            cand            = REPAIR[ri](dest, removed)

            best_before = best.copy()
            accepted    = accept(cur, cand, temp)
            score       = 0

            if accepted:
                pool.add_plan(cand)
                if cand.dominates(best):
                    best   = cand.copy()
                    score  = cfg.sigma1
                    no_imp = 0
                elif cand.dominates(cur):
                    score  = cfg.sigma2
                    no_imp = 0
                else:
                    score   = cfg.sigma3
                    no_imp += 1
                cur = cand
            else:
                no_imp += 1

            key = (di, ri)
            self.op_counts[key] = self.op_counts.get(key, 0) + 1
            recent_imp.append(1 if score >= cfg.sigma2 else 0)

            # RL update
            reward    = self._reward(cur, best_before, cand, best, accepted)
            next_state = self._state(cur, best, no_imp, temp,
                                     it + 1, cfg.hybrid_iterations, imp_rate)
            done = 1.0 if no_imp >= cfg.early_stop_patience else 0.0
            self.buf.push(state, action, reward, next_state, done)
            if not frozen:
                self._train()

            temp *= cfg.temp_decay
            history.append(best.cost)

            if no_imp >= cfg.early_stop_patience:
                break

        # Post-processing (unchanged — RoutePool + polish)
        best = _pool_recombine(best, pool, cfg)
        best = _fixed_nv_polish(best, self.inst, cfg, n_iters=450)
        best = _pool_recombine(best, pool, cfg)

        best.algo = self.algo_name
        return best, history


RLALNSSolver = RLALNSSolver   # alias for transfer pipeline compatibility
print(f'✅ RLALNSSolver (DDQN-ALNS v11) ready.')
print(f'   Action space: {N_D}D × {N_R}R = {N_ACTIONS} pairs (no roulette wheel)')
print(f'   State: 14D per-iteration | Reward: dense hierarchical')


class PlateauController:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.q = QNet(cfg.ctrl_state_dim, len(MODES), cfg.ctrl_hidden).to(DEVICE)
        self.q_t = QNet(cfg.ctrl_state_dim, len(MODES), cfg.ctrl_hidden).to(DEVICE)
        self.q_t.load_state_dict(self.q.state_dict())
        self.opt = optim.Adam(self.q.parameters(), lr=cfg.ctrl_lr)
        self.buf = ReplayBuffer(cfg.ctrl_buffer)
        self.eps = cfg.ctrl_eps_start
        self.step = 0

    def reset(self) -> None:
        self.eps = self.cfg.ctrl_eps_start

    def act(self, state: np.ndarray, force_default: bool = False) -> int:
        if force_default:
            return MODE_DEFAULT
        if random.random() < self.eps:
            return random.randrange(len(MODES))
        with torch.no_grad():
            q_values = self.q(torch.tensor(state).unsqueeze(0).to(DEVICE))[0]
        return int(q_values.argmax().item())

    def observe(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: float = 0.0,
    ) -> None:
        self.buf.push(state, action, reward, next_state, done)

    def train_step(self) -> None:
        self.step += 1
        if len(self.buf) < self.cfg.ctrl_batch:
            return

        s, a, r, ns, d = self.buf.sample(self.cfg.ctrl_batch)
        s = torch.tensor(s).to(DEVICE)
        a = torch.tensor(a, dtype=torch.long).to(DEVICE)
        r = torch.tensor(r).to(DEVICE)
        ns = torch.tensor(ns).to(DEVICE)
        d = torch.tensor(d).to(DEVICE)

        qp = self.q(s).gather(1, a.unsqueeze(1)).squeeze(1)
        with torch.no_grad():
            an = self.q(ns).argmax(1)
            qn = self.q_t(ns).gather(1, an.unsqueeze(1)).squeeze(1)
            target = r + self.cfg.ctrl_gamma * qn * (1 - d)

        loss = F.mse_loss(qp, target)
        self.opt.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.q.parameters(), 1.0)
        self.opt.step()

        if self.step % self.cfg.ctrl_target_freq == 0:
            self.q_t.load_state_dict(self.q.state_dict())
        self.eps = max(self.cfg.ctrl_eps_end, self.eps * self.cfg.ctrl_eps_decay)


# ── Keep PlateauHybridSolver alias for ALNS++ / ScheduledHybridSolver ─────
class PlateauHybridSolver:
    algo_name = "DDQN-ALNS"
    """
    DDQN-ALNS v10.0:
    - PlateauController selects search MODE (6 modes including pool_recombine)
    - RoutePool accumulates feasible routes across iterations
    - MILP/greedy set-partition recombination after main search + after polish
    - _fixed_nv_polish: 450-iter intensification at fixed NV target
    - controller state includes fleet_fill + route_pool saturation
    - route_reduce trigger: fires when fleet_fill < threshold at plateau
    - inline recombination is capped to once per segment for cleaner credit assignment
    """

    def __init__(self, inst: Inst, cfg: Config):
        self.inst     = inst
        self.cfg      = cfg
        self.ctrl     = PlateauController(cfg)
        self.op_counts: Dict[Tuple[int, int], int] = {}
        self._segment_recombine_used = False

    def clone_weights(self) -> Dict:
        return {k: v.clone().cpu() for k, v in self.ctrl.q.state_dict().items()}

    def load_weights(self, weights: Dict) -> None:
        cur_state = self.ctrl.q.state_dict()
        matched = {
            k: v for k, v in weights.items()
            if k in cur_state and tuple(v.shape) == tuple(cur_state[k].shape)
        }
        if not matched:
            print('\u26a0\ufe0f  transfer weights incompatible with current controller; using fresh init')
            return
        cur_state.update(matched)
        self.ctrl.q.load_state_dict(cur_state)
        self.ctrl.q_t.load_state_dict(cur_state)
        if len(matched) < len(cur_state):
            print(f'\u26a0\ufe0f  partial controller weight load: matched {len(matched)}/{len(cur_state)} tensors')

    def _state(self, cur: Plan, best: Plan, no_imp: int, temp: float,
               dw: np.ndarray, rw: np.ndarray,
               imp_rate: float, progress: float, pool: RoutePool) -> np.ndarray:
        rb, lb = _plan_spread(cur, self.inst)
        t0     = self.cfg.temp_control * best.cost / math.log(2)
        pool_fill = min(len(pool._routes) / max(self.cfg.route_pool_limit, 1), 1.0)
        fleet_fill = _fleet_fill(cur)
        return np.array([
            min(no_imp / max(self.cfg.early_stop_patience, 1), 1.0),
            min((cur.cost - best.cost) / max(best.cost, 1), 1.0),
            min(temp / max(t0, 1e-6), 1.5),
            imp_rate,
            min(cur.nv / max(self._init_nv, 1), 2.0),
            rb, lb,
            self.inst.tw_tight_frac,
            _avg_slack(cur),
            fleet_fill,
            pool_fill,
            progress,
        ], dtype=np.float32)

    def _segment_reward(self, best_before: Plan, best_after: Plan,
                        cur_before: Plan, cur_after: Plan,
                        accepted_moves: int, action: int) -> float:
        reward = -0.35 - 0.05 * MODES[action].ls_passes
        if MODES[action].use_recombine:
            reward -= 0.10
        if best_after.nv < best_before.nv:
            reward += (25.0 * (best_before.nv - best_after.nv)
                       + max((best_before.cost - best_after.cost)
                             / max(best_before.cost, 1), 0.0) * 100)
        elif best_after.nv > best_before.nv:
            reward -= self.cfg.nv_increase_penalty * (best_after.nv - best_before.nv)
        elif best_after.cost < best_before.cost:
            reward += (2.5 * (best_before.cost - best_after.cost)
                       / max(best_before.cost, 1) * 100)
        if cur_after.nv == cur_before.nv and cur_after.cost < cur_before.cost:
            reward += (0.5 * (cur_before.cost - cur_after.cost)
                       / max(cur_before.cost, 1) * 100)
        if accepted_moves <= max(1, self.cfg.segment_size // 10):
            reward -= 0.25
        return float(reward)

    def _route_reduce_trigger(self, cur: Plan, no_imp: int) -> bool:
        return (
            no_imp >= self.cfg.plateau_start
            and _fleet_fill(cur) < max(0.52, 0.80 - 0.25 * self.inst.tw_tight_frac)
        )

    def _select_action(self, state_before: np.ndarray, cur: Plan, best: Plan,
                       no_imp: int, progress: float, pool: RoutePool,
                       post_imp_lock: int,
                       frozen: bool) -> Tuple[int, bool, int]:
        if post_imp_lock > 0:
            return MODE_INTENSIFY, False, post_imp_lock - 1
        if self._route_reduce_trigger(cur, no_imp):
            return MODE_ROUTE_REDUCE, False, post_imp_lock
        if no_imp >= self.cfg.ctrl_start:
            return self.ctrl.act(state_before, force_default=frozen), (not frozen), post_imp_lock
        return MODE_DEFAULT, False, post_imp_lock

    def _refine_candidate(self, cand: Plan, action: int, pool: RoutePool,
                          cur: Plan, best: Plan, no_imp: int,
                          iter_idx: int) -> Plan:
        mode = MODES[action]
        refined = cand
        if mode.ls_passes > 0 and iter_idx % 3 == 0:
            nv_cap = best.nv if action in (MODE_INTENSIFY, MODE_TW_RESCUE, MODE_POOL_RECOMBINE, MODE_ROUTE_REDUCE) else None
            refined = local_search(refined, max_passes=mode.ls_passes, nv_ceiling=nv_cap)
        if (mode.use_recombine
                and not self._segment_recombine_used
                and no_imp >= max(self.cfg.ctrl_start, self.cfg.plateau_start // 2)
                and len(pool._routes) >= self.cfg.rl_recombine_min_routes):
            self._segment_recombine_used = True
            nv_cap = min(best.nv, refined.nv)
            recombined = recombine_with_route_pool(refined, pool, self.cfg, nv_ceiling=nv_cap)
            if recombined.dominates(refined):
                refined = local_search(recombined, max_passes=1, nv_ceiling=recombined.nv)
        return refined

    def _fixed_nv_polish(self, start: Plan, pool: RoutePool) -> Plan:
        """[NEW-2] 450-iter ALNS intensification locked to start.nv vehicles."""
        cfg       = self.cfg
        target_nv = start.nv
        cur  = local_search(start, max_passes=cfg.polish_ls_passes, nv_ceiling=target_nv)
        best = cur.copy()
        pool.add_plan(best)
        temp = cfg.temp_control * best.cost / math.log(2)
        no_imp = 0

        polish_dw = np.array([0.3, 1.4, 1.3, 0.8, 1.2, 0.9], dtype=np.float32)
        polish_rw = np.array([0.8, 1.2, 1.5, 1.2], dtype=np.float32)

        for it in range(cfg.polish_iterations):
            di   = _roulette(polish_dw)
            ri   = _roulette(polish_rw)
            size = destroy_size(it, cfg.polish_iterations, cfg,
                                self.inst.n, scale=0.70)
            dest, removed = DESTROY[di](cur.copy(), size)
            cand          = REPAIR[ri](dest, removed)
            cand          = local_search(cand, max_passes=1, nv_ceiling=target_nv)
            pool.add_plan(cand)

            cur_before = cur
            if accept_with_nv_ceiling(cur, cand, temp, target_nv):
                cur = cand
                if cand.nv < target_nv:
                    target_nv = cand.nv
                if cand.dominates(best):
                    best   = cand.copy()
                    no_imp = 0
                elif cand.nv == cur_before.nv and cand.cost + 1e-9 < cur_before.cost:
                    no_imp = 0
                else:
                    no_imp += 1
            else:
                no_imp += 1

            temp *= cfg.temp_decay * 0.997
            if no_imp >= cfg.polish_patience:
                break

        best = local_search(best, max_passes=cfg.polish_ls_passes, nv_ceiling=best.nv)
        pool.add_plan(best)
        return best

    def solve(self, seed: Optional[int] = None,
              frozen: bool = False) -> Tuple[Plan, List[float]]:
        """frozen=True: weights pre-loaded (transfer), controller does not train."""
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
            torch.manual_seed(seed)

        cfg  = self.cfg
        self.ctrl.reset()
        self.op_counts = {}
        pool = RoutePool(self.inst, cfg)

        cur  = build_greedy(self.inst, self.algo_name)
        best = cur.copy()
        pool.add_plan(cur)
        self._init_nv = cur.nv

        temp = cfg.temp_control * cur.cost / math.log(2)
        dw   = np.ones(N_D)
        rw   = np.ones(N_R)
        history: List[float]       = [best.cost]
        recent_improvements: Deque = deque(maxlen=cfg.segment_size)
        no_imp        = 0
        post_imp_lock = 0
        n_segments    = math.ceil(cfg.hybrid_iterations / cfg.segment_size)

        for seg_idx in range(n_segments):
            progress = seg_idx / max(n_segments, 1)
            imp_rate = (sum(recent_improvements) / len(recent_improvements)
                        if recent_improvements else 0.0)
            self._segment_recombine_used = False
            state_before = self._state(cur, best, no_imp, temp, dw, rw,
                                       imp_rate, progress, pool)

            action, ctrl_active, post_imp_lock = self._select_action(
                state_before, cur, best, no_imp, progress, pool,
                post_imp_lock, frozen,
            )

            mode      = MODES[action]
            biased_dw = np.maximum(dw * np.array(mode.destroy_bias, np.float32), 0.1)
            biased_rw = np.maximum(rw * np.array(mode.repair_bias,  np.float32), 0.1)
            temp     *= mode.temp_boost

            seg_scores    = np.zeros((N_D, N_R))
            seg_counts    = np.zeros((N_D, N_R))
            seg_best_pre  = best.copy()
            seg_cur_pre   = cur.copy()
            accepted_moves = 0
            best_improved  = False

            for offset in range(cfg.segment_size):
                it = seg_idx * cfg.segment_size + offset
                if it >= cfg.hybrid_iterations:
                    break

                di   = _roulette(biased_dw)
                ri   = _roulette(biased_rw)
                size = destroy_size(it, cfg.hybrid_iterations, cfg,
                                    self.inst.n, scale=mode.destroy_scale)
                dest, removed = DESTROY[di](cur.copy(), size)
                cand          = REPAIR[ri](dest, removed)
                cand          = self._refine_candidate(cand, action, pool, cur, best, no_imp, it)
                score         = 0
                improved      = False

                if accept(cur, cand, temp):
                    accepted_moves += 1
                    improved        = cand.dominates(cur)
                    pool.add_plan(cand)
                    if cand.dominates(best):
                        best          = cand.copy()
                        best_improved = True
                        pool.add_plan(best)
                        score  = cfg.sigma1
                        no_imp = 0
                    elif improved:
                        score  = cfg.sigma2
                        no_imp = 0
                    else:
                        score   = cfg.sigma3
                        no_imp += 1
                    cur = cand
                else:
                    no_imp += 1

                key = (di, ri)
                self.op_counts[key] = self.op_counts.get(key, 0) + 1
                recent_improvements.append(1 if improved else 0)
                seg_scores[di, ri] += score
                seg_counts[di, ri] += 1
                temp *= cfg.temp_decay * mode.temp_decay_scale
                history.append(best.cost)

                if no_imp >= cfg.early_stop_patience:
                    break

            for d in range(N_D):
                for r in range(N_R):
                    if seg_counts[d, r] > 0:
                        avg   = seg_scores[d, r] / seg_counts[d, r]
                        dw[d] = dw[d] * (1 - cfg.weight_decay) + avg * cfg.weight_decay
                        rw[r] = rw[r] * (1 - cfg.weight_decay) + avg * cfg.weight_decay
            dw = np.maximum(dw, 0.1)
            rw = np.maximum(rw, 0.1)

            state_after = self._state(
                cur, best, no_imp, temp, dw, rw,
                sum(recent_improvements) / len(recent_improvements)
                if recent_improvements else 0.0,
                min((seg_idx + 1) / max(n_segments, 1), 1.0),
                pool,
            )
            if ctrl_active:
                self.ctrl.observe(
                    state_before, action,
                    self._segment_reward(seg_best_pre, best,
                                         seg_cur_pre, cur, accepted_moves, action),
                    state_after, 0.0,
                )
                self.ctrl.train_step()

            if best_improved:
                post_imp_lock = cfg.post_improve_intensify_segments

            if no_imp >= cfg.early_stop_patience:
                break

        # [NEW-6] Recombine after main search
        if cfg.recombine_after_main_search:
            recombined = recombine_with_route_pool(best, pool, cfg,
                                                    nv_ceiling=best.nv)
            if recombined.dominates(best):
                best = recombined
                pool.add_plan(best)
                history.append(best.cost)

        # [NEW-2] Polish at fixed NV
        polished = self._fixed_nv_polish(best, pool)
        if polished.dominates(best):
            best = polished
        else:
            best = polished  # take polished even if not dominant (same NV, similar cost)
        history.append(best.cost)

        # [NEW-6] Recombine after polish
        if cfg.recombine_after_polish:
            recombined = recombine_with_route_pool(best, pool, cfg,
                                                    nv_ceiling=best.nv)
            if recombined.dominates(best):
                best = local_search(recombined, max_passes=cfg.polish_ls_passes,
                                    nv_ceiling=recombined.nv)
                history.append(best.cost)

        best.algo = self.algo_name
        return best, history



class ScheduledHybridSolver(PlateauHybridSolver):
    """Strong non-RL baseline with rule-based mode scheduling."""
    algo_name = "ALNS++"

    def _select_action(self, state_before: np.ndarray, cur: Plan, best: Plan,
                       no_imp: int, progress: float, pool: RoutePool,
                       post_imp_lock: int,
                       frozen: bool) -> Tuple[int, bool, int]:
        if post_imp_lock > 0:
            return MODE_INTENSIFY, False, post_imp_lock - 1
        if self._route_reduce_trigger(cur, no_imp):
            return MODE_ROUTE_REDUCE, False, post_imp_lock

        pool_ready = len(pool._routes) >= max(self.cfg.rl_recombine_min_routes,
                                             max(12, cur.nv * 2))
        fleet_fill = _fleet_fill(cur)
        slack = _avg_slack(cur)

        if (pool_ready and no_imp >= max(10, self.cfg.ctrl_start // 2)
                and fleet_fill >= 0.66 and progress < 0.92):
            return MODE_POOL_RECOMBINE, False, post_imp_lock
        if (self.inst.tw_tight_frac >= 0.18 and slack < 0.16
                and no_imp >= max(8, self.cfg.ctrl_start // 2)):
            return MODE_TW_RESCUE, False, post_imp_lock
        if no_imp >= max(12, self.cfg.ctrl_start // 2):
            if progress < 0.45:
                return MODE_DIVERSIFY, False, post_imp_lock
            return MODE_INTENSIFY, False, post_imp_lock
        return MODE_DEFAULT, False, post_imp_lock


RLALNSSolver = PlateauHybridSolver

print('✅ ScheduledHybridSolver (ALNS++) ready.')


# In[10]:


# â”€â”€ Cell 11: Benchmark Runner â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def run_instance(inst: Inst, algo: str, cfg: Config,
                 seed: int,
                 transfer_weights: Optional[Dict] = None) -> Dict:
    start = time.time()
 
    if algo == "ALNS":
        plan, history = ALNSSolver(inst, cfg).solve(seed=seed)
 
    elif algo in ("ALNS+", "ALNS-FAIR"):
        solver = PlateauHybridSolver(inst, cfg)
        plan, history = solver.solve(seed=seed, frozen=True)
        plan.algo = "ALNS+"
 
    elif algo in ("ALNS++", "SCHED-ALNS"):
        solver = ScheduledHybridSolver(inst, cfg)
        plan, history = solver.solve(seed=seed, frozen=True)
        plan.algo = "ALNS++"
 
    elif algo in ("DDQN-ALNS", "PLATEAU-HYBRID"):
        solver = RLALNSSolver(inst, cfg)
        plan, history = solver.solve(seed=seed)
 
    elif algo == "DDQN-ALNSâ˜…":
        solver = RLALNSSolver(inst, cfg)
        if transfer_weights is not None:
            solver.load_weights(transfer_weights)
        plan, history = solver.solve(seed=seed, frozen=True)
 
    elif algo == "DQN":
        plan, history = DQNSolver(inst, cfg).solve(seed=seed)
 
    else:
        raise ValueError(f"Unsupported algorithm: {algo}")
 
    bks = BKS.get(inst.name)
    return {
        "nv":      plan.nv,
        "cost":    plan.cost,
        "time":    time.time() - start,
        "td_gap":  (plan.cost - bks["td"]) / bks["td"] * 100 if bks else None,
        "nv_diff": plan.nv - bks["nv"] if bks else None,
        "on_time": plan.on_time_rate,
        "hist":    history,
    }
 
 
def run_benchmark(instances:        Iterable[Inst],
                  algorithms:       List[str],
                  cfg:              Config,
                  result_path:      Optional[str]  = None,
                  transfer_weights: Optional[Dict]  = None) -> pd.DataFrame:
    """
    [BENCH-1] Checkpoint save every 4 instances to /kaggle/working/benchmark_checkpoint.csv
    [BENCH-2] Stores per-run costs in raw_costs column for Wilcoxon per-run analysis
    """
    instances    = list(instances)
    result_path  = result_path or os.path.join(cfg.output_dir, "benchmark_clean.csv")
    ckpt_path    = os.path.join(cfg.output_dir, "benchmark_checkpoint.csv")
    rows: List[Dict] = []
 
    total = len(instances) * len(algorithms)
    print(f"Total: {total} combos Ã— {cfg.n_runs} runs\n" + "=" * 60)
    wall_start = time.time()
 
    for inst_idx, inst in enumerate(instances):
        dataset = "RC1" if inst.name[2] == "1" else "RC2"
        for algo in algorithms:
            print(f"\n[{inst.name}] {algo}")
            nv_v, cost_v, time_v, gap_v, nvd_v, ot_v = [], [], [], [], [], []
            for run_idx in range(cfg.n_runs):
                res = run_instance(inst, algo, cfg,
                                   cfg.seed + run_idx, transfer_weights)
                nv_v.append(res["nv"])
                cost_v.append(res["cost"])
                time_v.append(res["time"])
                gap_v.append(res["td_gap"])
                nvd_v.append(res["nv_diff"])
                ot_v.append(res["on_time"])
                elapsed = time.time() - wall_start
                print(f"  run {run_idx + 1}/{cfg.n_runs}: "
                      f"nv={res['nv']} cost={res['cost']:.1f} "
                      f"({res['time']:.1f}s) | wall {elapsed/3600:.2f}h")
 
            row = {
                "Dataset":   dataset,
                "Instance":  inst.name,
                "Algorithm": algo,
                "NV_mean":   round(np.mean(nv_v),   2),
                "NV_std":    round(np.std(nv_v),    2),
                "NV_diff":   round(np.mean(nvd_v),  2) if nvd_v[0] is not None else None,
                "TD_mean":   round(np.mean(cost_v), 2),
                "TD_std":    round(np.std(cost_v),  2),
                "Gap%":      round(np.mean(gap_v),  2) if gap_v[0] is not None else None,
                "OnTime":    round(np.mean(ot_v) * 100, 1),
                "Time_s":    round(np.mean(time_v), 1),
                "NV_cv":     round(np.std(nv_v)   / max(np.mean(nv_v),   1) * 100, 2),
                "TD_cv":     round(np.std(cost_v)  / max(np.mean(cost_v), 1) * 100, 2),
                # [BENCH-2] raw per-run costs, semicolon-separated
                "raw_costs": ";".join(f"{c:.4f}" for c in cost_v),
                "raw_nv":    ";".join(str(n) for n in nv_v),
            }
            rows.append(row)
            gap_text = f"{row['Gap%']:+.1f}%" if row["Gap%"] is not None else "--"
            print(f"  â†’ nv={row['NV_mean']:.1f}Â±{row['NV_std']:.1f}  "
                  f"td={row['TD_mean']:.1f}Â±{row['TD_std']:.1f}  gap={gap_text}")
 
        # [BENCH-1] checkpoint every 4 instances
        if (inst_idx + 1) % 4 == 0:
            pd.DataFrame(rows).to_csv(ckpt_path, index=False)
            elapsed = time.time() - wall_start
            print(f"\n  ðŸ’¾ Checkpoint saved ({inst_idx+1}/{len(instances)} instances, "
                  f"{elapsed/3600:.2f}h elapsed) â†’ {ckpt_path}")
 
    df = pd.DataFrame(rows)
    df.to_csv(result_path, index=False)
    total_time = time.time() - wall_start
    print(f"\nâœ… Benchmark complete in {total_time/3600:.2f}h â†’ {result_path}")
    return df
 
 
def print_summary_table(df: pd.DataFrame) -> None:
    summary = (
        df.groupby(["Dataset", "Algorithm"])
          .agg(NV=("NV_mean", "mean"), NV_std=("NV_std", "mean"),
               NV_diff=("NV_diff", "mean"), TD=("TD_mean", "mean"),
               TD_std=("TD_std", "mean"), Gap=("Gap%", "mean"),
               OnTime=("OnTime", "mean"), Time=("Time_s", "mean"))
          .round(2).reset_index()
    )
    print("\n" + "-" * 86)
    print(f"{'DS':<4}{'Algorithm':<18}{'NV':>6}{'+/-':>6}{'vsBKS':>8}"
          f"{'TD':>10}{'+/-':>8}{'Gap%':>8}{'OT%':>7}{'Time':>8}")
    print("-" * 86)
    for _, row in summary.iterrows():
        gap    = f"{row['Gap']:+.2f}%" if pd.notna(row["Gap"])    else "--"
        nv_diff = f"{row['NV_diff']:+.2f}" if pd.notna(row["NV_diff"]) else "--"
        print(f"{row['Dataset']:<4}{row['Algorithm']:<18}"
              f"{row['NV']:>6.2f}{row['NV_std']:>6.2f}{nv_diff:>8}"
              f"{row['TD']:>10.2f}{row['TD_std']:>8.2f}{gap:>8}"
              f"{row['OnTime']:>7.1f}{row['Time']:>7.1f}s")
    print("-" * 86)


print('âœ… Benchmark runner ready.')


# In[11]:


# â”€â”€ Cell 12: Transfer Learning Pipeline â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def train_transfer_model(instances: List[Inst],
                         cfg: Config = CFG,
                         seed: int   = 42) -> Dict:
    """Sequentially fine-tune controller weights across source instances."""
    print('ðŸ“š Training transfer model (sequential curriculum)...')
    if not instances:
        raise ValueError('No source instances provided for transfer training.')
 
    weights = None
    for epoch in range(cfg.transfer_epochs):
        epoch_order = list(instances)
        if cfg.transfer_shuffle:
            random.Random(seed + epoch).shuffle(epoch_order)
        print(f'  Epoch {epoch + 1}/{cfg.transfer_epochs}')
        for idx, inst in enumerate(epoch_order):
            solver = RLALNSSolver(inst, cfg)
            if weights is not None:
                solver.load_weights(weights)
            run_seed = seed + epoch * 100 + idx
            plan, _ = solver.solve(seed=run_seed)
            weights = solver.clone_weights()
            td, _ = plan.gap()
            print(f'    [{epoch + 1}:{idx + 1}] {inst.name}: nv={plan.nv}, gap={td:+.1f}%')
 
    # Save the sequentially trained controller, not a naive mean of unrelated policies.
    if SAFETENSORS_OK:
        save_path = os.path.join(cfg.output_dir, 'rl_alns_transfer.safetensors')
        save_file(weights, save_path)
        print(f'\nâœ… Transfer model saved â†’ {save_path}')
    else:
        print('âš ï¸  safetensors unavailable â€” transfer model not saved to disk')
 
    return weights
 
 
def load_transfer_model(cfg: Config = CFG) -> Optional[Dict]:
    # [FIX-1] use cfg.output_dir, not MODEL_DIR
    if not SAFETENSORS_OK:
        return None
    path = os.path.join(cfg.output_dir, 'rl_alns_transfer.safetensors')
    if os.path.exists(path):
        print(f'âœ… Transfer model loaded from {path}')
        return load_file(path)
    return None
 
 
print('âœ… Transfer learning pipeline ready.')


# In[12]:


# â”€â”€ Cell 13: Statistical Tests & Paper Tables â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def wilcoxon_test(df: pd.DataFrame, algo_a: str, algo_b: str,
                  metric: str = 'Gap%',
                  dataset: Optional[str] = None) -> Dict:
    """Per-instance-mean test (n=8). Legacy approach, kept for comparison."""
    sub = df if dataset is None else df[df['Dataset'] == dataset]
    a   = sub[sub['Algorithm'] == algo_a][metric].dropna().values
    b   = sub[sub['Algorithm'] == algo_b][metric].dropna().values
    n   = min(len(a), len(b))
    a, b = a[:n], b[:n]
    if n < 3:
        return {'stat': None, 'p': None, 'sig': False, 'n': n}
    stat, p = stats.wilcoxon(a, b, alternative='two-sided')
    return {
        'stat': round(stat, 3), 'p': round(p, 4), 'sig': p < 0.05,
        'n': n, 'better': algo_a if a.mean() < b.mean() else algo_b,
        'method': 'per_instance_mean',
    }


def wilcoxon_per_run(df: pd.DataFrame, algo_a: str, algo_b: str,
                     dataset: Optional[str] = None) -> Dict:
    """
    [STATS-1] Per-run paired test on raw costs.
    n = instances Ã— n_runs (e.g. 8 Ã— 8 = 64 per family).
    Much stronger statistical power than per-instance-mean (n=8).

    Pairing: run_k of algo_a on instance_i  vs  run_k of algo_b on instance_i.
    This is valid because same seed+k guarantees same initial solution.
    """
    sub = df if dataset is None else df[df['Dataset'] == dataset]
    a_rows = sub[sub['Algorithm'] == algo_a]
    b_rows = sub[sub['Algorithm'] == algo_b]

    costs_a, costs_b = [], []
    common_instances = set(a_rows['Instance']) & set(b_rows['Instance'])

    for inst_name in sorted(common_instances):
        ra = a_rows[a_rows['Instance'] == inst_name]
        rb = b_rows[b_rows['Instance'] == inst_name]
        if ra.empty or rb.empty:
            continue
        # raw_costs column: "c1;c2;...;cn_runs"
        if 'raw_costs' not in ra.columns:
            # fallback: use TD_mean as single observation
            costs_a.append(float(ra['TD_mean'].values[0]))
            costs_b.append(float(rb['TD_mean'].values[0]))
        else:
            ac = [float(x) for x in ra['raw_costs'].values[0].split(';')]
            bc = [float(x) for x in rb['raw_costs'].values[0].split(';')]
            n  = min(len(ac), len(bc))
            costs_a.extend(ac[:n])
            costs_b.extend(bc[:n])

    costs_a = np.array(costs_a)
    costs_b = np.array(costs_b)
    n = len(costs_a)

    if n < 6:
        return {'stat': None, 'p': None, 'sig': False, 'n': n,
                'method': 'per_run'}

    # Skip zero-difference pairs (wilcoxon requirement)
    diff = costs_a - costs_b
    nonzero = diff[diff != 0]
    if len(nonzero) < 6:
        return {'stat': None, 'p': None, 'sig': False, 'n': n,
                'method': 'per_run'}

    stat, p = stats.wilcoxon(costs_a, costs_b, alternative='two-sided')
    effect = (costs_b.mean() - costs_a.mean()) / costs_a.mean() * 100  # % improvement of a over b
    return {
        'stat':   round(stat, 3),
        'p':      round(p, 4),
        'sig':    p < 0.05,
        'n':      n,
        'better': algo_a if costs_a.mean() < costs_b.mean() else algo_b,
        'effect_pct': round(effect, 3),  # positive = algo_a is better by this %
        'method': 'per_run',
    }


def print_paper_table(df: pd.DataFrame) -> None:
    summary = (
        df.groupby(['Dataset', 'Algorithm'])
          .agg(NV=('NV_mean', 'mean'), NV_std=('NV_std', 'mean'),
               NV_d=('NV_diff', 'mean'),
               TD=('TD_mean', 'mean'), TD_std=('TD_std', 'mean'),
               Gap=('Gap%', 'mean'),
               CV_nv=('NV_cv', 'mean'), CV_td=('TD_cv', 'mean'),
               OT=('OnTime', 'mean'), Time=('Time_s', 'mean'))
          .round(2).reset_index()
    )
    hdr = (f'{"DS":<4}{"Algorithm":<14}{"NV":>6}{"Â±":>4}{"vsBKS":>8}'
           f'{"TD":>9}{"Â±":>6}{"Gap%":>7}{"CV_NV":>6}{"CV_TD":>6}'
           f'{"OT%":>6}{"Time":>7}')
    sep = 'â”€' * len(hdr)
    print('\n' + sep)
    print(hdr)
    print(sep)
    prev = ''
    for _, r in summary.iterrows():
        if r['Dataset'] != prev and prev:
            print(sep)
        prev   = r['Dataset']
        nv_d   = f"{r['NV_d']:+.1f}" if pd.notna(r['NV_d']) else 'â€”'
        gap    = f"{r['Gap']:+.1f}%" if pd.notna(r['Gap'])   else 'â€”'
        print(f"{r['Dataset']:<4}{r['Algorithm']:<14}"
              f"{r['NV']:>6.1f}{r['NV_std']:>4.1f}{nv_d:>8}"
              f"{r['TD']:>9.1f}{r['TD_std']:>6.1f}{gap:>7}"
              f"{r['CV_nv']:>6.1f}{r['CV_td']:>6.1f}"
              f"{r['OT']:>6.1f}{r['Time']:>6.1f}s")
    print(sep)
    print('CV = std/meanÃ—100%. Negative Gap%: solution beats BKS distance.')


def print_stats_table(df: pd.DataFrame) -> None:
    """[STATS-2] Print both per-instance-mean and per-run Wilcoxon results."""
    pairs = [
        ('DDQN-ALNS', 'ALNS+'),
        ('DDQN-ALNS', 'ALNS'),
        ('DDQN-ALNSâ˜…', 'ALNS+'),
        ('DDQN-ALNSâ˜…', 'ALNS'),
    ]

    # â”€â”€ Per-instance-mean (n=8 per family) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print('\nâ”€â”€ Wilcoxon signed-rank â€” per-instance-mean (n=instances) â”€â”€')
    print(f'{"Comparison":<28}{"DS":<5}{"Metric":<8}'
          f'{"W":>7}{"p":>9}{"Sig":>5}{"Better":>12}')
    print('â”€' * 70)
    for algo_a, algo_b in pairs:
        if algo_a not in df['Algorithm'].values:
            continue
        for ds in ['RC1', 'RC2']:
            for metric in ['Gap%', 'NV_mean']:
                res = wilcoxon_test(df, algo_a, algo_b, metric, ds)
                if res['stat'] is None:
                    continue
                sig = 'âœ…' if res['sig'] else 'â€”'
                print(f'  {algo_a} vs {algo_b:<8}  {ds:<5}{metric:<8}'
                      f'{res["stat"]:>7.1f}{res["p"]:>9.4f}'
                      f'{sig:>5}{res["better"]:>12}')
    print('â”€' * 70)
    print('âœ… = p < 0.05')

    # â”€â”€ Per-run (n=instancesÃ—n_runs, much stronger) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print('\nâ”€â”€ Wilcoxon signed-rank â€” per-run paired (n=instancesÃ—n_runs) â”€â”€')
    print(f'{"Comparison":<28}{"DS":<5}{"n":>5}'
          f'{"W":>9}{"p":>9}{"Sig":>5}{"Effect%":>9}{"Better":>12}')
    print('â”€' * 78)
    for algo_a, algo_b in pairs:
        if algo_a not in df['Algorithm'].values:
            continue
        for ds in ['RC1', 'RC2']:
            res = wilcoxon_per_run(df, algo_a, algo_b, ds)
            if res['stat'] is None:
                print(f'  {algo_a} vs {algo_b:<8}  {ds:<5}'
                      f'{"n=" + str(res["n"]):>5}  insufficient data')
                continue
            sig = 'âœ…' if res['sig'] else 'â€”'
            eff = f"{res['effect_pct']:+.3f}%"
            print(f'  {algo_a} vs {algo_b:<8}  {ds:<5}{res["n"]:>5}'
                  f'{res["stat"]:>9.1f}{res["p"]:>9.4f}'
                  f'{sig:>5}{eff:>9}{res["better"]:>12}')
    print('â”€' * 78)
    print('Effect% = mean cost improvement of "Better" over other.')
    print('âœ… = p < 0.05  |  per-run n =', end=' ')
    try:
        sample = df[df['Algorithm'] == 'ALNS']
        if 'raw_costs' in sample.columns:
            ex = sample.iloc[0]['raw_costs'].count(';') + 1
            print(f'{len(sample)} instances Ã— {ex} runs = {len(sample)*ex} pairs/family')
        else:
            print('(raw_costs not available)')
    except Exception:
        print('?')


print('âœ… Stats & table utilities ready.')
# v10 stats override
def print_stats_table(df: pd.DataFrame) -> None:
    """[STATS-2] Print both per-instance-mean and per-run Wilcoxon results."""
    pairs = [
        ('ALNS++', 'ALNS+'),
        ('ALNS++', 'ALNS'),
        ('DDQN-ALNS', 'ALNS++'),
        ('DDQN-ALNS', 'ALNS+'),
        ('DDQN-ALNS', 'ALNS'),
        ('DDQN-ALNS★', 'ALNS++'),
        ('DDQN-ALNS★', 'ALNS+'),
        ('DDQN-ALNS★', 'ALNS'),
    ]

    print('\n── Wilcoxon signed-rank — per-instance-mean (n=instances) ──')
    print(f'{"Comparison":<28}{"DS":<5}{"Metric":<8}'
          f'{"W":>7}{"p":>9}{"Sig":>5}{"Better":>12}')
    print('─' * 70)
    for algo_a, algo_b in pairs:
        if algo_a not in df['Algorithm'].values or algo_b not in df['Algorithm'].values:
            continue
        for ds in ['RC1', 'RC2']:
            for metric in ['Gap%', 'NV_mean']:
                res = wilcoxon_test(df, algo_a, algo_b, metric, ds)
                if res['stat'] is None:
                    continue
                sig = '✅' if res['sig'] else '—'
                print(f'  {algo_a} vs {algo_b:<8}  {ds:<5}{metric:<8}'
                      f'{res["stat"]:>7.1f}{res["p"]:>9.4f}'
                      f'{sig:>5}{res["better"]:>12}')
    print('─' * 70)
    print('✅ = p < 0.05')

    print('\n── Wilcoxon signed-rank — per-run paired (n=instances×n_runs) ──')
    print(f'{"Comparison":<28}{"DS":<5}{"n":>5}'
          f'{"W":>9}{"p":>9}{"Sig":>5}{"Effect%":>9}{"Better":>12}')
    print('─' * 78)
    for algo_a, algo_b in pairs:
        if algo_a not in df['Algorithm'].values or algo_b not in df['Algorithm'].values:
            continue
        for ds in ['RC1', 'RC2']:
            res = wilcoxon_per_run(df, algo_a, algo_b, ds)
            if res['stat'] is None:
                print(f'  {algo_a} vs {algo_b:<8}  {ds:<5}'
                      f'{"n=" + str(res["n"]):>5}  insufficient data')
                continue
            sig = '✅' if res['sig'] else '—'
            eff = f"{res['effect_pct']:+.3f}%"
            print(f'  {algo_a} vs {algo_b:<8}  {ds:<5}{res["n"]:>5}'
                  f'{res["stat"]:>9.1f}{res["p"]:>9.4f}'
                  f'{sig:>5}{eff:>9}{res["better"]:>12}')
    print('─' * 78)
    print('Effect% = mean cost improvement of "Better" over other.')
    print('✅ = p < 0.05  |  per-run n =', end=' ')
    try:
        sample = df[df['Algorithm'] == 'ALNS']
        if 'raw_costs' in sample.columns:
            ex = sample.iloc[0]['raw_costs'].count(';') + 1
            print(f'{len(sample)} instances × {ex} runs = {len(sample)*ex} pairs/family')
        else:
            print('(raw_costs not available)')
    except Exception:
        print('?')


# In[13]:


# â”€â”€ Cell 14: Visualisation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
import matplotlib
matplotlib.use('Agg')          # headless-safe on Kaggle
import matplotlib.pyplot as plt
 
COLORS = {
    'ALNS':       '#5f5fae',
    'ALNS+':      '#4c78a8',
    'DDQN-ALNS':  '#1d9e75',
    'DDQN-ALNSâ˜…': '#e67e22',
    'DQN':        '#e74c3c',
    'PLATEAU-HYBRID': '#1d9e75',   # legacy label compatibility
}
 
 
def plot_dashboard(df: pd.DataFrame) -> None:
    metrics = [
        ('Gap%',    'Distance Gap vs BKS (%)', 'â†“ lower is better'),
        ('NV_mean', 'Vehicles Used (avg)',      'â†“ lower is better'),
        ('TD_cv',   'TD Consistency (CV %)',    'â†“ lower = more stable'),
    ]
    algos = [a for a in COLORS if a in df['Algorithm'].values]
    fig, axes = plt.subplots(2, 3, figsize=(18, 8))
    for ri, ds in enumerate(['RC1', 'RC2']):
        for ci, (met, label, note) in enumerate(metrics):
            ax   = axes[ri][ci]
            sub  = df[df['Dataset'] == ds]
            insts = sub['Instance'].unique()
            x    = np.arange(len(insts))
            w    = 0.8 / max(len(algos), 1)
            for ji, algo in enumerate(algos):
                vals = [sub[sub['Instance'] == i][met].mean() for i in insts]
                ax.bar(x + ji * w, vals, w, label=algo,
                       color=COLORS.get(algo, '#888888'), alpha=0.85,
                       edgecolor='white')
            ax.set_xticks(x + w * (len(algos) - 1) / 2)
            ax.set_xticklabels([i[-3:] for i in insts], fontsize=8)
            ax.set_title(f'{ds} â€” {label}\n({note})', fontsize=9, fontweight='bold')
            ax.set_ylabel(met, fontsize=8)
            ax.grid(axis='y', alpha=0.3)
            if ri == 0 and ci == 0:
                ax.legend(fontsize=8)
    plt.suptitle('Algorithm Comparison â€” VRPTW Solomon RC Benchmarks v9.8',
                 fontsize=13, fontweight='bold')
    plt.tight_layout()
    out = os.path.join(CFG.output_dir, 'dashboard.png')
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'âœ… dashboard.png saved â†’ {out}')
 
 
def plot_convergence_grid(inst: Inst, cfg: Config, seed: int = 42) -> None:
    histories = {}
    for algo, SolverCls in [('ALNS', ALNSSolver),
                             ('DDQN-ALNS', PlateauHybridSolver)]:
        s = SolverCls(inst, cfg)
        _, hist = s.solve(seed=seed)
        histories[algo] = hist
 
    fig, ax = plt.subplots(figsize=(9, 4))
    for algo, hist in histories.items():
        ax.plot(hist, label=algo, color=COLORS.get(algo, '#888'), lw=2, alpha=0.9)
    bks = BKS.get(inst.name, {})
    if bks:
        ax.axhline(bks['td'], color='gray', ls='--', lw=1.2, label='BKS distance')
    ax.set_xlabel('Iteration')
    ax.set_ylabel('Best Cost Found')
    ax.set_title(f'Convergence â€” {inst.name}', fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.2)
    plt.tight_layout()
    out = os.path.join(CFG.output_dir, f'convergence_{inst.name}.png')
    plt.savefig(out, dpi=120, bbox_inches='tight')
    plt.close()
    print(f'âœ… Convergence plot â†’ {out}')
 
 
def plot_transfer_comparison(df: pd.DataFrame) -> None:
    """[FIX-6] Scatter: DDQN-ALNSâ˜… vs strongest available non-RL baseline on RC2."""
    rc2  = df[df['Dataset'] == 'RC2']
    baseline = 'ALNS+' if 'ALNS+' in rc2['Algorithm'].values else 'ALNS'
    alns = rc2[rc2['Algorithm'] == baseline][['Instance', 'Gap%']].set_index('Instance')
    star = rc2[rc2['Algorithm'] == 'DDQN-ALNSâ˜…'][['Instance', 'Gap%']].set_index('Instance')
    common = alns.index.intersection(star.index)
    if common.empty:
        print('âš ï¸  No DDQN-ALNSâ˜… results to plot yet.')
        return
 
    fig, ax = plt.subplots(figsize=(7, 5))
    x = alns.loc[common, 'Gap%'].values
    y = star.loc[common, 'Gap%'].values
    ax.scatter(x, y, s=80, color=COLORS['DDQN-ALNSâ˜…'], zorder=3)
    for inst, xi, yi in zip(common, x, y):
        ax.annotate(inst[-3:], (xi, yi), textcoords='offset points',
                    xytext=(4, 4), fontsize=8)
    lim = [min(x.min(), y.min()) - 1, max(x.max(), y.max()) + 1]
    ax.plot(lim, lim, 'k--', lw=1, alpha=0.5, label='y=x (same performance)')
    ax.set_xlabel(f'{baseline} Gap% (RC2)')
    ax.set_ylabel('DDQN-ALNSâ˜… Gap% (RC2, zero-shot)')
    ax.set_title(f'Transfer Learning: DDQN-ALNSâ˜… vs {baseline} on RC2', fontweight='bold')
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    plt.tight_layout()
    out = os.path.join(CFG.output_dir, 'transfer_comparison.png')
    plt.savefig(out, dpi=120, bbox_inches='tight')
    plt.close()
    print(f'âœ… Transfer comparison plot â†’ {out}')
 
 
def plot_routes(plan: Plan, save: bool = True) -> None:
    RCOLS = [
        '#E63946', '#2A9D8F', '#E9C46A', '#264653', '#F4A261',
        '#A8DADC', '#457B9D', '#6A4C93', '#F72585', '#4CC9F0',
        '#80B918', '#FF9F1C', '#8338EC', '#3A86FF', '#CBFF8C',
    ]
    inst = plan.inst
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.scatter(*inst.coords[0], s=220, c='black', marker='s', zorder=5)
    ax.annotate('DEPOT', inst.coords[0], fontsize=8,
                ha='center', va='bottom', fontweight='bold')
    for i, route in enumerate(plan.routes):
        col   = RCOLS[i % len(RCOLS)]
        stops = [0] + route + [0]
        xs    = [inst.coords[n, 0] for n in stops]
        ys    = [inst.coords[n, 1] for n in stops]
        ax.plot(xs, ys, '-o', color=col, lw=1.5, ms=4, alpha=0.8, label=f'V{i+1}')
    td, nv = plan.gap()
    g = f' | BKS: TD {td:+.1f}% NV {nv:+d}' if td is not None else ''
    ax.set_title(f'{plan.algo} â€” {inst.name}  nv={plan.nv}  cost={plan.cost:.1f}{g}',
                 fontweight='bold')
    ax.legend(fontsize=6, ncol=3)
    ax.grid(alpha=0.2)
    plt.tight_layout()
    if save:
        out = os.path.join(CFG.output_dir, f'routes_{plan.algo}_{inst.name}.png')
        plt.savefig(out, dpi=120, bbox_inches='tight')
        plt.close()
        print(f'âœ… Route plot â†’ {out}')
    else:
        plt.show()
 
 
print('âœ… Visualisation ready.')
 
 
# v10 visual override
COLORS['ALNS++'] = '#72b7b2'


def plot_dashboard(df: pd.DataFrame) -> None:
    metrics = [
        ('Gap%',    'Distance Gap vs BKS (%)', '↓ lower is better'),
        ('NV_mean', 'Vehicles Used (avg)',     '↓ lower is better'),
        ('TD_cv',   'TD Consistency (CV %)',   '↓ lower = more stable'),
    ]
    algos = [a for a in COLORS if a in df['Algorithm'].values]
    fig, axes = plt.subplots(2, 3, figsize=(18, 8))
    for ri, ds in enumerate(['RC1', 'RC2']):
        for ci, (met, label, note) in enumerate(metrics):
            ax = axes[ri][ci]
            sub = df[df['Dataset'] == ds]
            insts = sub['Instance'].unique()
            x = np.arange(len(insts))
            w = 0.8 / max(len(algos), 1)
            for ji, algo in enumerate(algos):
                vals = [sub[(sub['Algorithm'] == algo) & (sub['Instance'] == i)][met].mean()
                        for i in insts]
                ax.bar(x + ji * w, vals, w, label=algo,
                       color=COLORS.get(algo, '#888888'), alpha=0.85,
                       edgecolor='white')
            ax.set_xticks(x + w * (len(algos) - 1) / 2)
            ax.set_xticklabels([i[-3:] for i in insts], fontsize=8)
            ax.set_title(f'{ds} — {label}\n({note})', fontsize=9, fontweight='bold')
            ax.set_ylabel(met, fontsize=8)
            ax.grid(axis='y', alpha=0.3)
            if ri == 0 and ci == 0:
                ax.legend(fontsize=8)
    plt.suptitle('Algorithm Comparison — VRPTW Solomon RC Benchmarks v10.0',
                 fontsize=13, fontweight='bold')
    plt.tight_layout()
    out = os.path.join(CFG.output_dir, 'dashboard.png')
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'✅ dashboard.png saved → {out}')


def plot_convergence_grid(inst: Inst, cfg: Config, seed: int = 42) -> None:
    histories = {}
    for algo, SolverCls in [
        ('ALNS', ALNSSolver),
        ('ALNS++', ScheduledHybridSolver),
        ('DDQN-ALNS', PlateauHybridSolver),
    ]:
        s = SolverCls(inst, cfg)
        _, hist = s.solve(seed=seed)
        histories[algo] = hist

    fig, ax = plt.subplots(figsize=(9, 4))
    for algo, hist in histories.items():
        ax.plot(hist, label=algo, color=COLORS.get(algo, '#888'), lw=2, alpha=0.9)
    bks = BKS.get(inst.name, {})
    if bks:
        ax.axhline(bks['td'], color='gray', ls='--', lw=1.2, label='BKS distance')
    ax.set_xlabel('Iteration')
    ax.set_ylabel('Best Cost Found')
    ax.set_title(f'Convergence — {inst.name}', fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.2)
    plt.tight_layout()
    out = os.path.join(CFG.output_dir, f'convergence_{inst.name}.png')
    plt.savefig(out, dpi=120, bbox_inches='tight')
    plt.close()
    print(f'✅ Convergence plot → {out}')


def plot_transfer_comparison(df: pd.DataFrame) -> None:
    """Scatter: DDQN-ALNS★ vs strongest available non-RL baseline on RC2."""
    rc2 = df[df['Dataset'] == 'RC2']
    baselines = [a for a in ['ALNS++', 'ALNS+', 'ALNS'] if a in rc2['Algorithm'].values]
    if not baselines:
        print('⚠️  No non-RL baseline results to compare yet.')
        return
    baseline = min(baselines, key=lambda a: rc2[rc2['Algorithm'] == a]['Gap%'].mean())
    base = rc2[rc2['Algorithm'] == baseline][['Instance', 'Gap%']].set_index('Instance')
    star = rc2[rc2['Algorithm'] == 'DDQN-ALNS★'][['Instance', 'Gap%']].set_index('Instance')
    common = base.index.intersection(star.index)
    if common.empty:
        print('⚠️  No DDQN-ALNS★ results to plot yet.')
        return

    fig, ax = plt.subplots(figsize=(7, 5))
    x = base.loc[common, 'Gap%'].values
    y = star.loc[common, 'Gap%'].values
    ax.scatter(x, y, s=80, color=COLORS['DDQN-ALNS★'], zorder=3)
    for inst, xi, yi in zip(common, x, y):
        ax.annotate(inst[-3:], (xi, yi), textcoords='offset points',
                    xytext=(4, 4), fontsize=8)
    lim = [min(x.min(), y.min()) - 1, max(x.max(), y.max()) + 1]
    ax.plot(lim, lim, 'k--', lw=1, alpha=0.5, label='y=x (same performance)')
    ax.set_xlabel(f'{baseline} Gap% (RC2)')
    ax.set_ylabel('DDQN-ALNS★ Gap% (RC2, zero-shot)')
    ax.set_title(f'Transfer Learning: DDQN-ALNS★ vs {baseline} on RC2', fontweight='bold')
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    plt.tight_layout()
    out = os.path.join(CFG.output_dir, 'transfer_comparison.png')
    plt.savefig(out, dpi=120, bbox_inches='tight')
    plt.close()
    print(f'✅ Transfer comparison plot → {out}')


# In[ ]:


# â”€â”€ Cell 15: Smoke Test â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
smoke_cfg = Config(
    alns_iterations=400,
    hybrid_iterations=600,
    early_stop_patience=150,
    n_runs=1,
)
inst = RC1[0]
print(f'Smoke test â€” {inst.name}\n')
 
for algo, SolverCls in [('ALNS', ALNSSolver),
                         ('ALNS++', ScheduledHybridSolver),
                         ('DDQN-ALNS', RLALNSSolver)]:
    t0        = time.time()
    s         = SolverCls(inst, smoke_cfg)
    plan, _   = s.solve(seed=42)
    el        = time.time() - t0
    td, nv    = plan.gap()
    print(f'  {algo:<18} nv={plan.nv:>3}  cost={plan.cost:>8.1f}  '
          f'BKS TD {td:+.1f}% NV {nv:+d}  ({el:.1f}s)')
 
print('\nâœ“ Smoke test passed â€” v10.0')
plot_convergence_grid(RC1[0], smoke_cfg, seed=42)


# In[ ]:


# â”€â”€ Cell 16: Phase 1 â€” Main Benchmark â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Fair benchmark: legacy ALNS, frozen ALNS+, rule-based ALNS++, and DDQN-ALNS
# Expected runtime grows with the algorithm list below.
RESULT_PATH = os.path.join(CFG.output_dir, 'benchmark_clean.csv')
 
df = run_benchmark(
    instances  = RC1 + RC2,
    algorithms = ['ALNS', 'ALNS+', 'ALNS++', 'DDQN-ALNS'],
    cfg        = CFG,
    result_path= RESULT_PATH,
)
print_summary_table(df)
print_paper_table(df)
print_stats_table(df)
plot_dashboard(df)


# In[ ]:


# â”€â”€ Cell 17: Phase 2 â€” Transfer Learning â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
RESULT_TRANSFER = os.path.join(CFG.output_dir, 'benchmark_transfer.csv')
 
# Step 1: Train (or load cached)
transfer_weights = load_transfer_model(CFG)
if transfer_weights is None:
    transfer_weights = train_transfer_model(RC1, CFG, seed=CFG.seed)
 
# Step 2: Zero-shot on RC2
df_tr = run_benchmark(
    instances        = RC2,
    algorithms       = ['DDQN-ALNSâ˜…'],
    cfg              = CFG,
    result_path      = RESULT_TRANSFER,
    transfer_weights = transfer_weights,
)
 
# Step 3: Compare
df_all = pd.concat([df, df_tr], ignore_index=True)
print_paper_table(df_all[df_all['Dataset'] == 'RC2'])
 


# In[ ]:


# â”€â”€ Cell 18: Full Analysis â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
dfs = []
for p in [RESULT_PATH, RESULT_TRANSFER]:
    if os.path.exists(p):
        dfs.append(pd.read_csv(p))
df_all = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
 
if not df_all.empty:
    print('=' * 60 + '\nFULL RESULTS TABLE')
    print_paper_table(df_all)
 
    print('\n' + '=' * 60 + '\nSTATISTICAL TESTS')
    print_stats_table(df_all)
 
    print('\n' + '=' * 60 + '\nDASHBOARD')
    plot_dashboard(df_all)
 
    print('\n' + '=' * 60 + '\nTRANSFER: DDQN-ALNSâ˜… vs strongest non-RL baseline on RC2')
    plot_transfer_comparison(df_all)
else:
    print('Run cells 16 and 17 first.')
 


# In[ ]:


# â”€â”€ Cell 19: Per-Instance Tables (Appendix) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if not df_all.empty:
    for ds in ['RC1', 'RC2']:
        sub   = df_all[df_all['Dataset'] == ds]
        pivot = sub.pivot_table(
            index='Instance', columns='Algorithm',
            values=['NV_mean', 'TD_mean', 'Gap%', 'NV_cv'],
            aggfunc='mean',
        ).round(2)
        print(f'\nâ”€â”€ {ds} per-instance detail â”€â”€')
        print(pivot.to_string())


# In[ ]:


# â”€â”€ Cell 20: Route Visualisation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
inst = RC1[0]
for algo, SolverCls in [('ALNS', ALNSSolver), ('ALNS++', ScheduledHybridSolver), ('DDQN-ALNS', PlateauHybridSolver)]:
    s = SolverCls(inst, CFG)
    plan, _ = s.solve(seed=CFG.seed)
    plot_routes(plan)


# In[ ]:


# â”€â”€ Cell 21: NEXUS Demo Export â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
MAP_INSTANCE = RC1[0]
print(f"Exporting NEXUS demo for {MAP_INSTANCE.name}...")
t0 = time.time()
 
 
def _solve_export(inst: Inst, SolverCls, label: str) -> Dict:
    s         = SolverCls(inst, CFG)
    plan, hist = s.solve(seed=CFG.seed)
    routes_out = []
    for ri, route in enumerate(plan.routes):
        if not route:
            continue
        d = float(inst.dist[0, route[0]])
        for k in range(len(route) - 1):
            d += float(inst.dist[route[k], route[k + 1]])
        d += float(inst.dist[route[-1], 0])
        routes_out.append({
            "id":    ri + 1,
            "nodes": [int(n) for n in route],
            "dist":  round(d, 2),
        })
    bks_td = BKS[inst.name]["td"]
    total  = sum(r["dist"] for r in routes_out)
    gap    = round((total - bks_td) / bks_td * 100, 2)
    print(f"  {label:12s}: nv={len(routes_out)}, td={total:.1f}, gap={gap:+.1f}%")
    return {
        "algo": label, "nv": len(routes_out),
        "td": round(total, 2), "gap_pct": gap,
        "bks_nv": BKS[inst.name]["nv"], "bks_td": bks_td,
        "routes":  routes_out,
        "history": [round(float(c), 2) for c in hist] if hist else [],
    }
 
 
alns_exp   = _solve_export(MAP_INSTANCE, ALNSSolver, "ALNS")
alnspp_exp = _solve_export(MAP_INSTANCE, ScheduledHybridSolver, "ALNS++")
rla_exp    = _solve_export(MAP_INSTANCE, PlateauHybridSolver, "DDQN-ALNS")
 
# Real op_counts from last solve
_s = PlateauHybridSolver(MAP_INSTANCE, CFG)
_s.solve(seed=CFG.seed)
op_matrix = [
    [_s.op_counts.get((di, ri), 0) for ri in range(N_R)]
    for di in range(N_D)
]
 
inst = MAP_INSTANCE
nodes_exp = [
    {"id": int(i), "x": float(inst.coords[i, 0]), "y": float(inst.coords[i, 1]),
     "demand": float(inst.demands[i]), "ready": float(inst.ready_times[i]),
     "due": float(inst.due_times[i]),  "svc":   float(inst.service_times[i])}
    for i in range(inst.n + 1)
]
 
summary_exp = [
    {"instance": str(r["Instance"]), "algo": str(r["Algorithm"]),
     "nv": float(r["NV_mean"]),     "td":   float(r["TD_mean"]),
     "gap_pct": float(r["Gap%"]) if pd.notna(r.get("Gap%")) else 0.0,
     "cv_nv":   float(r["NV_cv"]), "cv_td": float(r["TD_cv"]),
     "time_s":  float(r["Time_s"])}
    for _, r in df.iterrows()
]
 
# df_tr may not exist if cell 17 was skipped
transfer_exp = []
if 'df_tr' in dir() and not df_tr.empty:
    transfer_exp = [
        {"instance": str(r["Instance"]), "algo": str(r["Algorithm"]),
         "nv":  float(r["NV_mean"]),    "td":   float(r["TD_mean"]),
         "gap_pct": float(r["Gap%"]) if pd.notna(r.get("Gap%")) else 0.0}
        for _, r in df_tr.iterrows()
    ]
 
OUT = {
    "meta": {
        "instance":    MAP_INSTANCE.name,
        "n_customers": int(MAP_INSTANCE.n),
        "capacity":    float(MAP_INSTANCE.capacity),
        "horizon":     float(MAP_INSTANCE.horizon),
        "dataset":     "Solomon RC1+RC2",
        "version":     "v10.0",
        "algo_desc": {
            "ALNS":       "Adaptive Large Neighbourhood Search (baseline)",
            "ALNS+":      "Strong non-RL baseline: same route-pool/polish stack with frozen default controller",
            "ALNS++":     "Rule-based hybrid baseline: scheduled intensify/diversify/recombine/route-reduce without RL",
            "DDQN-ALNS":  "Dueling DDQN selects search MODE and targeted inline refinements inside ALNS (proposed)",
            "DDQN-ALNSâ˜…": "Zero-shot transfer: trained on RC1, applied to RC2",
            "DQN":        "Constructive RL without metaheuristic (ablation)",
        },
    },
    "nodes":       nodes_exp,
    "alns":        alns_exp,
    "alnspp":      alnspp_exp,
    "rl_alns":     rla_exp,
    "op_matrix":   op_matrix,
    "destroy_ops": ["Random", "Worst", "Shaw", "Route", "TW-Urgent", "RouteElim"],
    "repair_ops":  ["Greedy", "Regret-2", "Regret-3", "TW-Greedy"],
    "summary":     summary_exp,
    "transfer":    transfer_exp,
}
 
out_json = os.path.join(OUTPUT_DIR, "nexus_demo.json")
with open(out_json, "w") as f:
    json.dump(OUT, f, separators=(",", ":"))
 
size_kb = os.path.getsize(out_json) / 1024
print(f"\nâœ… nexus_demo.json â†’ {out_json}  ({size_kb:.1f} KB)")
print(f"   Total export time: {time.time() - t0:.1f}s")
print("   Drop nexus_demo.json into nexus_v2.html to view")
 

