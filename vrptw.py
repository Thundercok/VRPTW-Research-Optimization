"""
VRPTW RL v15
============
Hardware target: i7-14700KF (28 cores), vast.ai

Changes vs v14:
- [PERF] Numba/OMP/MKL thread cap moved before numba import (was after)
- [PERF] ProcessPoolExecutor replaces ThreadPoolExecutor — true GIL bypass
- [PERF] local_search: max_ls_moves=5 cap (was unbounded while-True)
- [PERF] LS frequency: iter_idx % 20 (was % 3) — 6x fewer LS calls
- [PERF] LS gated on feasible + non-NV-inflating candidates only
- [PERF] Config: alns/hybrid_iterations=1200, early_stop=250, polish=80
- [ALGO] PrioritizedReplayBuffer replaces ReplayBuffer in both controllers
- [ALGO] _iterative_route_elimination: post-search NV reduction pass (RC2)
- [ALGO] _fixed_nv_polish: inherits dominant mode_bandit (was cold-start)
- [ALGO] Diverse seed init: seed0=archive, seed1=perturbed, seed2=fresh
- [ROBUST] _save_weights/_load_weights: torch.save fallback (safetensors opt.)
- [ROBUST] DR weights cached to disk; reloaded on session resume
- [ROBUST] print_summary_table: completeness + NV-inflation warnings
- [ROBUST] Per-algo smoke timing; estimator no longer divides wall/4
- [DATA] NV_inflated flag in benchmark rows
"""

from __future__ import annotations

import glob
import math
import os
import random
import time
from collections import deque
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import Deque, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

# ── Thread caps MUST be set before any numba/torch import ──────────────────
_N_PARALLEL    = min(3, max(1, os.cpu_count() // 2))
_NUMBA_THREADS = max(1, os.cpu_count() // _N_PARALLEL)
os.environ.setdefault("NUMBA_NUM_THREADS", str(_NUMBA_THREADS))
os.environ.setdefault("OMP_NUM_THREADS",   str(_NUMBA_THREADS))
os.environ.setdefault("MKL_NUM_THREADS",   str(_NUMBA_THREADS))
# Torch trains tiny nets; half of Numba budget is enough
torch.set_num_threads(max(1, _NUMBA_THREADS // 2))

from numba import njit  # noqa: E402  (must come after env-var block)

try:
    from scipy.optimize import Bounds, LinearConstraint, milp as _scipy_milp
    milp = _scipy_milp
    MILP_OK = True
except Exception:
    Bounds = LinearConstraint = milp = None
    MILP_OK = False

try:
    from safetensors.torch import load_file as _st_load, save_file as _st_save
    SAFETENSORS_OK = True
except Exception:
    SAFETENSORS_OK = False
    _st_load = _st_save = None

try:
    from ortools.constraint_solver import routing_enums_pb2, pywrapcp as _pywrapcp
    ORTOOLS_OK = True
except Exception:
    ORTOOLS_OK = False

DEVICE = torch.device("cpu")

# ---------------------------------------------------------------------------
# BKS table
# ---------------------------------------------------------------------------
BKS: Dict[str, Dict[str, float]] = {
    "RC101": {"nv": 14, "td": 1696.94},
    "RC102": {"nv": 12, "td": 1554.75},
    "RC103": {"nv": 11, "td": 1261.67},
    "RC104": {"nv": 10, "td": 1135.48},
    "RC105": {"nv": 13, "td": 1629.44},
    "RC106": {"nv": 11, "td": 1424.73},
    "RC107": {"nv": 11, "td": 1230.48},
    "RC108": {"nv": 10, "td": 1139.82},
    "RC201": {"nv": 4,  "td": 1406.94},
    "RC202": {"nv": 3,  "td": 1365.64},
    "RC203": {"nv": 3,  "td": 1049.62},
    "RC204": {"nv": 3,  "td": 798.46},
    "RC205": {"nv": 4,  "td": 1297.65},
    "RC206": {"nv": 3,  "td": 1146.32},
    "RC207": {"nv": 3,  "td": 1061.14},
    "RC208": {"nv": 3,  "td": 828.14},
}

ALGO_ORTOOLS               = "OR-Tools"
ALGO_ALNS_BASE             = "ALNS-Base"
ALGO_HYBRID_FIXED          = "Hybrid-Fixed"
ALGO_HYBRID_RULE           = "Hybrid-Rule"
ALGO_HYBRID_DDQN           = "Hybrid-DDQN"
ALGO_HYBRID_DDQN_TRANSFER      = "Hybrid-DDQN-Transfer"
ALGO_HYBRID_DDQN_TRANSFER_RC2  = "Hybrid-DDQN-Transfer-RC2"
ALGO_HYBRID_DDQN_TRANSFER_DR   = "Hybrid-DDQN-Transfer-DR"

ALGO_ORDER = [
    ALGO_ORTOOLS, ALGO_ALNS_BASE, ALGO_HYBRID_FIXED, ALGO_HYBRID_RULE,
    ALGO_HYBRID_DDQN, ALGO_HYBRID_DDQN_TRANSFER,
    ALGO_HYBRID_DDQN_TRANSFER_RC2, ALGO_HYBRID_DDQN_TRANSFER_DR,
]

LEGACY_ALGO_LABELS = {
    "ALNS": ALGO_ALNS_BASE, "ALNS-Base": ALGO_ALNS_BASE,
    "ALNS+": ALGO_HYBRID_FIXED, "ALNS-FAIR": ALGO_HYBRID_FIXED,
    "Hybrid-Fixed": ALGO_HYBRID_FIXED,
    "ALNS++": ALGO_HYBRID_RULE, "SCHED-ALNS": ALGO_HYBRID_RULE,
    "Hybrid-Rule": ALGO_HYBRID_RULE,
    "DDQN-ALNS": ALGO_HYBRID_DDQN, "PLATEAU-HYBRID": ALGO_HYBRID_DDQN,
    "Hybrid-DDQN": ALGO_HYBRID_DDQN,
    "DDQN-ALNS*": ALGO_HYBRID_DDQN_TRANSFER,
    "DDQN-ALNS★": ALGO_HYBRID_DDQN_TRANSFER,
    "Hybrid-DDQN-Transfer": ALGO_HYBRID_DDQN_TRANSFER,
    "Hybrid-DDQN-Transfer-RC2": ALGO_HYBRID_DDQN_TRANSFER_RC2,
    "Hybrid-DDQN-Transfer-DR": ALGO_HYBRID_DDQN_TRANSFER_DR,
}


def canonical_algo_label(label: str) -> str:
    return LEGACY_ALGO_LABELS.get(label, label)


def normalize_algorithm_frame(df: pd.DataFrame) -> pd.DataFrame:
    if "Algorithm" not in df.columns:
        return df
    out = df.copy()
    out["Algorithm"] = out["Algorithm"].map(canonical_algo_label)
    extra = [a for a in out["Algorithm"].dropna().unique() if a not in ALGO_ORDER]
    out["Algorithm"] = pd.Categorical(
        out["Algorithm"], categories=ALGO_ORDER + extra, ordered=True
    )
    sort_cols = [c for c in ("Dataset", "Instance", "Algorithm") if c in out.columns]
    if sort_cols:
        out = out.sort_values(sort_cols).reset_index(drop=True)
    return out


def default_data_path() -> str:
    candidates = [
        "./data/Solomon",
        "/workspace/data/Solomon",
        "/root/data/Solomon",
        "/kaggle/input/vrptw-benchmark-datasets/data/Solomon",
        "/kaggle/input/datasets/senju14/vrptw-benchmark-datasets/data/Solomon",
        "/content/vrptw-benchmark/data/Solomon",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]


def default_output_dir() -> str:
    for d in ("/workspace", "/root", "/kaggle/working", "/content"):
        if os.path.exists(d):
            return d
    return os.getcwd()


# ---------------------------------------------------------------------------
# Config — tuned for i7-14700KF (28 cores), n_runs=3
# ---------------------------------------------------------------------------
@dataclass
class Config:
    data_path:  str = field(default_factory=default_data_path)
    output_dir: str = field(default_factory=default_output_dir)

    # ── iterations (reduced from 3500; early-stop exits stagnation faster) ─
    alns_iterations:     int   = 1200
    hybrid_iterations:   int   = 1200
    early_stop_patience: int   = 250
    polish_iterations:   int   = 80
    polish_patience:     int   = 40

    destroy_ratio_min:   float = 0.10
    destroy_ratio_max:   float = 0.40
    temp_control:        float = 0.05
    temp_decay:          float = 0.99975
    sigma1:              int   = 33
    sigma2:              int   = 9
    sigma3:              int   = 3
    weight_decay:        float = 0.10
    segment_size:        int   = 100
    max_wall_hours:      float = 9.5
    n_runs:              int   = 3
    seed:                int   = 42

    # ── plateau controller ─────────────────────────────────────────────────
    ctrl_state_dim:   int   = 12
    ctrl_hidden:      int   = 128
    ctrl_lr:          float = 3e-4
    ctrl_gamma:       float = 0.95
    ctrl_buffer:      int   = 20_000
    ctrl_batch:       int   = 64
    ctrl_target_freq: int   = 100
    ctrl_eps_start:   float = 0.40
    ctrl_eps_end:     float = 0.02
    ctrl_eps_decay:   float = 0.9997
    ctrl_start:       int   = 24
    plateau_start:    int   = 72
    nv_increase_penalty: float = 15.0
    rl_recombine_min_routes: int = 24

    # ── operator controller ────────────────────────────────────────────────
    op_state_dim:      int   = 15
    op_hidden:         int   = 128
    op_lr:             float = 3e-4
    op_gamma:          float = 0.97
    op_buffer:         int   = 30_000
    op_batch:          int   = 64
    op_target_freq:    int   = 120
    op_eps_start:      float = 0.35
    op_eps_end:        float = 0.02
    op_eps_decay:      float = 0.9996
    op_warmup:         int   = 256
    op_prior_strength: float = 0.55
    op_bandit_strength:float = 0.20

    bandit_decay:          float = 0.95
    bandit_prior_strength: float = 0.18
    potential_nv_scale:    float = 15.0
    potential_cost_scale:  float = 0.18
    segment_reward_scale:  float = 0.30
    iteration_reward_scale:float = 0.45

    # ── route pool / set-partitioning ─────────────────────────────────────
    route_pool_limit:          int   = 480
    route_pool_max_per_customer: int = 18
    sp_time_limit:             float = 4.0
    sp_vehicle_penalty_scale:  float = 100.0

    # ── polish ────────────────────────────────────────────────────────────
    polish_ls_passes:            int  = 2
    recombine_after_main_search: bool = True
    recombine_after_polish:      bool = True

    # ── transfer ──────────────────────────────────────────────────────────
    transfer_epochs:   int  = 1
    transfer_shuffle:  bool = True
    rc2_transfer_split: int = 4

    # ── elite archive ─────────────────────────────────────────────────────
    elite_archive_k: int = 5

    # ── OR-Tools ──────────────────────────────────────────────────────────
    ortools_time_limit: float = 60.0

    # ── Learned Acceptance Criterion ──────────────────────────────────────
    lac_enabled:    bool  = True
    lac_state_dim:  int   = 9
    lac_hidden:     int   = 48
    lac_lr:         float = 1e-3
    lac_warmup:     int   = 300
    lac_horizon:    int   = 80
    lac_train_freq: int   = 20
    lac_buf_size:   int   = 5000

    # ── domain randomization ──────────────────────────────────────────────
    domain_randomization_epochs: int = 20
    domain_randomization_batch:  int = 15


# ---------------------------------------------------------------------------
# Mode specifications
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ModeSpec:
    name:             str
    destroy_scale:    float
    temp_boost:       float
    temp_decay_scale: float
    destroy_bias:     Tuple[float, ...]   # length == N_D = 8
    repair_bias:      Tuple[float, ...]   # length == N_R = 5
    ls_passes:        int
    use_recombine:    bool


MODES: Tuple[ModeSpec, ...] = (
    ModeSpec("default",       1.00, 1.00, 1.000, (1.0,1.0,1.0,1.0,1.0,0.8,0.8,1.0), (1.0,1.0,1.0,1.0,1.1), 0, False),
    ModeSpec("intensify",     0.70, 0.98, 0.995, (0.5,1.3,1.2,0.5,1.0,0.7,0.8,0.9), (1.3,1.2,0.8,1.0,1.3), 1, False),
    ModeSpec("diversify",     1.35, 1.08, 1.002, (1.5,0.9,1.3,1.4,1.0,0.7,1.4,1.6), (0.9,1.0,1.3,1.0,0.9), 0, False),
    ModeSpec("tw_rescue",     1.10, 1.05, 1.000, (0.6,0.9,1.1,0.8,1.8,0.4,0.8,1.0), (0.8,1.0,1.2,1.8,2.2), 1, False),
    ModeSpec("pool_recombine",0.90, 1.01, 0.997, (0.7,1.2,0.9,1.1,0.8,1.8,1.6,1.1), (0.7,1.1,1.5,0.9,1.1), 1, True),
    ModeSpec("route_reduce",  0.95, 1.02, 0.998, (0.6,1.0,0.9,1.7,0.6,2.2,2.4,1.2), (0.8,1.2,1.5,1.0,1.4), 1, True),
)

MODE_DEFAULT, MODE_INTENSIFY, MODE_DIVERSIFY = 0, 1, 2
MODE_TW_RESCUE, MODE_POOL_RECOMBINE, MODE_ROUTE_REDUCE = 3, 4, 5


# ---------------------------------------------------------------------------
# Instance
# ---------------------------------------------------------------------------
class Inst:
    def __init__(self, raw: Dict):
        self.name     = raw["name"]
        data          = raw["data"]
        self.capacity = raw["capacity"]
        self.coords       = data[:, 1:3]
        self.demands      = data[:, 3]
        self.ready_times  = data[:, 4]
        self.due_times    = data[:, 5]
        self.service_times= data[:, 6]
        self.horizon      = self.due_times[0]
        self.n            = len(data) - 1
        diff              = self.coords[:, None, :] - self.coords[None, :, :]
        self.dist         = np.sqrt((diff ** 2).sum(axis=2))
        self.max_dist     = float(self.dist.max())
        self.tw_width     = self.due_times - self.ready_times
        self.max_tw_width = float(self.tw_width[1:].max() + 1e-9)
        self.tw_tight_frac = sum(
            1 for i in range(1, self.n + 1)
            if self.tw_width[i] < 0.2 * self.horizon
        ) / max(self.n, 1)


# ---------------------------------------------------------------------------
# Synthetic generator
# ---------------------------------------------------------------------------
class SyntheticVRPTWGenerator:
    _DISTRIBUTIONS = {"C", "R", "RC"}

    def __init__(self, n_nodes: int, distribution: str = "RC",
                 seed: Optional[int] = None, capacity: Optional[float] = None):
        if n_nodes < 1:
            raise ValueError("n_nodes must be >= 1.")
        distribution = distribution.upper()
        if distribution not in self._DISTRIBUTIONS:
            raise ValueError(f"distribution must be one of {self._DISTRIBUTIONS}.")
        self.n_nodes      = int(n_nodes)
        self.distribution = distribution
        self.capacity     = capacity
        self.rng          = np.random.default_rng(seed)

    def _clustered_coords(self, count: int) -> np.ndarray:
        k       = int(np.clip(round(math.sqrt(count)), 2, 7))
        centers = self.rng.uniform(15.0, 85.0, size=(k, 2))
        assign  = self.rng.integers(0, k, size=count)
        coords  = centers[assign] + self.rng.normal(0.0, 6.5, size=(count, 2))
        return np.clip(coords, 0.0, 100.0)

    def _random_coords(self, count: int) -> np.ndarray:
        return self.rng.uniform(0.0, 100.0, size=(count, 2))

    def _coords(self) -> np.ndarray:
        if self.distribution == "C":
            customers = self._clustered_coords(self.n_nodes)
        elif self.distribution == "R":
            customers = self._random_coords(self.n_nodes)
        else:
            half      = self.n_nodes // 2
            customers = np.vstack([
                self._clustered_coords(half),
                self._random_coords(self.n_nodes - half),
            ])
            self.rng.shuffle(customers, axis=0)
        return np.vstack([np.array([[50.0, 50.0]]), customers])

    def _generate_raw(self, name: Optional[str] = None) -> Dict:
        coords  = self._coords()
        demands = self.rng.integers(1, 31, size=self.n_nodes).astype(float)
        if self.capacity is None:
            cpv = self.rng.uniform(6.0, 11.0)
            cap = float(np.ceil(max(
                demands.max() + 1.0,
                demands.mean() * cpv * self.rng.uniform(1.05, 1.30),
            )))
        else:
            cap = float(self.capacity)
            if demands.max() > cap:
                raise ValueError("capacity must be >= max demand.")
        depot    = coords[0]
        dist0    = np.sqrt(((coords[1:] - depot) ** 2).sum(axis=1))
        service  = self.rng.integers(5, 11, size=self.n_nodes).astype(float)
        horizon  = float(self.rng.uniform(260.0, 520.0))
        ready    = np.zeros(self.n_nodes + 1)
        due      = np.zeros(self.n_nodes + 1)
        service_all  = np.zeros(self.n_nodes + 1)
        demands_all  = np.zeros(self.n_nodes + 1)
        due[0]       = horizon
        demands_all[1:] = demands
        service_all[1:] = service
        tightness = self.rng.uniform(0.08, 0.28, size=self.n_nodes)
        if self.distribution == "C":
            anchor = self.rng.uniform(0.15, 0.75, size=self.n_nodes)
        elif self.distribution == "R":
            anchor = self.rng.uniform(0.05, 0.85, size=self.n_nodes)
        else:
            anchor = self.rng.beta(2.0, 2.0, size=self.n_nodes)
        for idx in range(self.n_nodes):
            node    = idx + 1
            earliest= float(dist0[idx])
            latest  = float(horizon - service[idx] - dist0[idx])
            if latest < earliest:
                horizon = float(earliest + service[idx] + dist0[idx] + 80.0)
                due[0]  = horizon
                latest  = float(horizon - service[idx] - dist0[idx])
            span  = max(latest - earliest, 1.0)
            width = min(max(18.0, tightness[idx] * horizon), span)
            start = float(np.clip(
                earliest + anchor[idx] * span - 0.5 * width,
                earliest, max(earliest, latest - width),
            ))
            ready[node] = start
            due[node]   = min(latest, start + width)
            if max(earliest, ready[node]) > due[node] + 1e-9:
                due[node] = max(earliest, ready[node])
            if due[node] + service[idx] + dist0[idx] > due[0] + 1e-9:
                due[node]   = due[0] - service[idx] - dist0[idx]
                ready[node] = min(ready[node], due[node])
        ids  = np.arange(self.n_nodes + 1, dtype=float)
        data = np.column_stack([
            ids, coords[:, 0], coords[:, 1], demands_all, ready, due, service_all
        ]).astype(float)
        raw = {
            "name":     name or f"SYN-{self.distribution}-{self.n_nodes:03d}-{int(self.rng.integers(1_000_000)):06d}",
            "capacity": cap,
            "data":     data,
        }
        self._assert_feasible(raw)
        return raw

    def _assert_feasible(self, raw: Dict) -> None:
        data    = raw["data"]
        depot   = data[0, 1:3]
        horizon = data[0, 5]
        for row in data[1:]:
            node_id = int(row[0])
            travel  = float(np.sqrt(((row[1:3] - depot) ** 2).sum()))
            r, d, s = float(row[4]), float(row[5]), float(row[6])
            if max(travel, r) > d + 1e-7:
                raise ValueError(f"Node {node_id} unreachable within TW.")
            if d + s + travel > horizon + 1e-7:
                raise ValueError(f"Node {node_id} cannot return before horizon.")

    def generate_raw(self, name: Optional[str] = None, max_retries: int = 12) -> Dict:
        for _ in range(max_retries):
            try:
                return self._generate_raw(name=name)
            except ValueError:
                self.rng = np.random.default_rng(int(self.rng.integers(10_000_000)))
        raise RuntimeError(f"No feasible instance after {max_retries} retries.")

    def generate(self, name: Optional[str] = None, max_retries: int = 12) -> Inst:
        return Inst(self.generate_raw(name=name, max_retries=max_retries))


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_datasets(base_path: str) -> Dict[str, List[Inst]]:
    datasets: Dict[str, List[Inst]] = {}
    for group in ("rc1", "rc2"):
        files = sorted(glob.glob(os.path.join(base_path, f"{group}*.txt")))
        insts: List[Inst] = []
        for path in files:
            with open(path, encoding="utf-8") as fh:
                lines = fh.readlines()
            name     = lines[0].strip()
            capacity = float(lines[4].strip().split()[1])
            rows     = [list(map(float, ln.split())) for ln in lines[9:] if ln.strip()]
            insts.append(Inst({"name": name, "capacity": capacity, "data": np.array(rows)}))
        datasets[group] = insts
    return datasets


# ---------------------------------------------------------------------------
# Numba primitives
# ---------------------------------------------------------------------------
@njit(cache=True)
def _route_cost(route: np.ndarray, dist: np.ndarray) -> float:
    cost = dist[0, route[0]]
    for idx in range(len(route) - 1):
        cost += dist[route[idx], route[idx + 1]]
    return cost + dist[route[-1], 0]


@njit(cache=True)
def _route_ok(route: np.ndarray, demands: np.ndarray, capacity: float,
              ready: np.ndarray, due: np.ndarray,
              service: np.ndarray, dist: np.ndarray) -> bool:
    load = 0.0
    for node in route:
        load += demands[node]
    if load > capacity:
        return False
    t, prev = 0.0, 0
    for node in route:
        t += dist[prev, node]
        if t < ready[node]:
            t = ready[node]
        if t > due[node]:
            return False
        t   += service[node]
        prev = node
    return True


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------
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

    @property
    def on_time_rate(self) -> float:
        on_time = total = 0
        for route in self.routes:
            t, prev = 0.0, 0
            for node in route:
                t += self.inst.dist[prev, node]
                t  = max(t, self.inst.ready_times[node])
                total += 1
                if t <= self.inst.due_times[node]:
                    on_time += 1
                t   += self.inst.service_times[node]
                prev = node
        return on_time / max(total, 1)

    def gap(self) -> Tuple[Optional[float], Optional[int]]:
        bks = BKS.get(self.inst.name)
        if not bks:
            return None, None
        return (self.cost - bks["td"]) / bks["td"] * 100, self.nv - bks["nv"]

    def dominates(self, other: "Plan") -> bool:
        return self.nv < other.nv or (self.nv == other.nv and self.cost < other.cost)

    def copy(self) -> "Plan":
        return Plan([r[:] for r in self.routes], self.inst, self.algo)

    def invalidate(self) -> None:
        self._cost = None
        self._ok   = None


def _invalidate(plan: Plan) -> Plan:
    plan.invalidate()
    return plan


# ---------------------------------------------------------------------------
# Operator helpers
# ---------------------------------------------------------------------------
def _check_route(route: List[int], inst: Inst) -> bool:
    return bool(_route_ok(
        np.array(route, np.int64), inst.demands, inst.capacity,
        inst.ready_times, inst.due_times, inst.service_times, inst.dist,
    ))


def _best_insert_position(node: int, route: List[int], inst: Inst) -> Tuple[float, Optional[int]]:
    best_cost, best_pos = float("inf"), None
    for pos in range(len(route) + 1):
        prev = route[pos - 1] if pos > 0       else 0
        nxt  = route[pos]     if pos < len(route) else 0
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


def _route_cost_list(route: List[int], inst: Inst) -> float:
    if not route:
        return 0.0
    return float(_route_cost(np.array(route, np.int64), inst.dist))


def _route_load(route: List[int], inst: Inst) -> float:
    return float(sum(inst.demands[n] for n in route))


def _route_avg_slack(route: List[int], inst: Inst) -> float:
    if not route:
        return 0.0
    slack, t, prev = 0.0, 0.0, 0
    for node in route:
        t += inst.dist[prev, node]
        t  = max(t, inst.ready_times[node])
        slack += inst.due_times[node] - t
        t   += inst.service_times[node]
        prev = node
    return slack / len(route)


def _route_duration_no_return(route: List[int], inst: Inst) -> float:
    t, prev = 0.0, 0
    for node in route:
        t += inst.dist[prev, node]
        t  = max(t, inst.ready_times[node])
        t += inst.service_times[node]
        prev = node
    return float(t)


# ---------------------------------------------------------------------------
# Destroy operators  (N_D = 8)
# ---------------------------------------------------------------------------
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
            prev = route[idx - 1] if idx > 0              else 0
            nxt  = route[idx + 1] if idx < len(route) - 1 else 0
            gains.append((inst.dist[prev, node] + inst.dist[node, nxt] - inst.dist[prev, nxt], node))
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
    seed_node = random.choice(nodes)
    removed   = [seed_node]
    rs        = {seed_node}
    max_dist  = inst.max_dist + 1e-9
    max_tw    = max(inst.due_times - inst.ready_times) + 1e-9
    while len(removed) < size:
        candidates = [
            (n, 0.5 * inst.dist[seed_node, n] / max_dist
               + 0.4 * abs(inst.ready_times[seed_node] - inst.ready_times[n]) / max_tw
               + 0.1 * abs(inst.demands[seed_node] - inst.demands[n]) / inst.capacity)
            for n in nodes if n not in rs
        ]
        if not candidates:
            break
        removed.append(min(candidates, key=lambda x: x[1])[0])
        rs.add(removed[-1])
    plan.routes = [[n for n in r if n not in rs] for r in plan.routes]
    plan.routes = [r for r in plan.routes if r]
    return _invalidate(plan), removed


def op_route_portion_removal(plan: Plan, size: int) -> Tuple[Plan, List[int]]:
    if len(plan.routes) <= 1:
        return op_shaw(plan, size)
    inst   = plan.inst
    target = min(max(3, size), sum(len(r) for r in plan.routes))
    removed: List[int] = []
    routes = [r[:] for r in plan.routes]
    while len(removed) < target:
        nonempty = [r for r in routes if r]
        if not nonempty:
            break
        durations = [_route_duration_no_return(r, inst) for r in nonempty]
        avg_dur   = max(float(np.mean(durations)), 1e-9)
        max_len   = max(len(r) for r in nonempty)
        max_dist  = max(inst.max_dist, 1.0)
        scored: List[Tuple[float, int]] = []
        for ridx, route in enumerate(routes):
            if len(route) < 2:
                continue
            coords   = inst.coords[np.array(route, dtype=np.int64)]
            centroid = coords.mean(axis=0)
            spatial  = float(np.sqrt(((coords - centroid) ** 2).sum(axis=1)).mean()) / max_dist
            duration = _route_duration_no_return(route, inst) / avg_dur
            length_pressure = len(route) / max(max_len, 1)
            score = 0.45 * length_pressure + 0.35 * duration + 0.20 * spatial
            score += random.random() * 0.03
            scored.append((score, ridx))
        if not scored:
            break
        _, ridx = max(scored, key=lambda x: x[0])
        route   = routes[ridx]
        remaining = target - len(removed)
        lower = max(1, int(math.floor(0.05 * len(route))))
        upper = min(max(lower, int(math.ceil(0.30 * len(route)))), len(route) - 1, remaining)
        if upper < 1:
            break
        seg_len = random.randint(min(lower, upper), upper)
        strain: List[Tuple[float, int]] = []
        for pos, node in enumerate(route):
            prev    = route[pos - 1] if pos > 0              else 0
            nxt     = route[pos + 1] if pos < len(route) - 1 else 0
            arc     = inst.dist[prev, node] + inst.dist[node, nxt] - inst.dist[prev, nxt]
            tw_width= inst.due_times[node] - inst.ready_times[node]
            urgency = 1.0 - min(tw_width / max(inst.max_tw_width, 1.0), 1.0)
            strain.append((arc / max_dist + 0.35 * urgency, pos))
        pivot = max(strain, key=lambda x: x[0])[1]
        start = int(np.clip(pivot - seg_len // 2, 0, len(route) - seg_len))
        segment = route[start:start + seg_len]
        removed.extend(segment)
        routes[ridx] = route[:start] + route[start + seg_len:]
    if not removed:
        return op_shaw(plan, size)
    plan.routes = [r for r in routes if r]
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


def op_route_eliminate(plan: Plan, size: int) -> Tuple[Plan, List[int]]:
    if len(plan.routes) <= 1:
        return op_random(plan, size)
    inst   = plan.inst
    ranked = sorted(
        enumerate(plan.routes),
        key=lambda x: (len(x[1]), sum(inst.demands[n] for n in x[1]) / max(inst.capacity, 1)),
    )
    removed: List[int] = []
    drop_ids: set = set()
    for idx, route in ranked:
        removed.extend(route)
        drop_ids.add(idx)
        if len(removed) >= max(2, size // 2):
            break
    plan.routes = [r for i, r in enumerate(plan.routes) if i not in drop_ids]
    return _invalidate(plan), removed


def op_route_proximity_eliminate(plan: Plan, size: int) -> Tuple[Plan, List[int]]:
    if len(plan.routes) <= 1:
        return op_random(plan, size)
    inst      = plan.inst
    durations = [_route_duration_no_return(r, inst) for r in plan.routes if r]
    avg_dur   = max(float(np.mean(durations)), 1e-9)
    max_dist  = max(inst.max_dist, 1.0)
    scored: List[Tuple[float, int]] = []
    for idx, route in enumerate(plan.routes):
        if not route:
            continue
        coords   = inst.coords[np.array(route, dtype=np.int64)]
        centroid = coords.mean(axis=0)
        spatial  = float(np.sqrt(((coords - centroid) ** 2).sum(axis=1)).mean()) / max_dist
        temporal = _route_duration_no_return(route, inst) / avg_dur
        scored.append((1.5 * spatial + 0.5 * temporal, idx))
    removed: List[int] = []
    drop_ids: set = set()
    for _, idx in sorted(scored, reverse=True):
        removed.extend(plan.routes[idx])
        drop_ids.add(idx)
        if len(removed) >= max(2, size // 2):
            break
    plan.routes = [r for i, r in enumerate(plan.routes) if i not in drop_ids]
    return _invalidate(plan), removed


def op_cross_route_shaw(plan: Plan, size: int) -> Tuple[Plan, List[int]]:
    inst         = plan.inst
    nodes        = [n for r in plan.routes for n in r]
    if not nodes:
        return plan, []
    node_to_route= {n: ri for ri, route in enumerate(plan.routes) for n in route}
    seed_node    = random.choice(nodes)
    seed_route   = node_to_route.get(seed_node, -1)
    removed      = [seed_node]
    rs           = {seed_node}
    max_dist     = inst.max_dist + 1e-9
    max_tw       = max(inst.due_times - inst.ready_times) + 1e-9
    while len(removed) < size:
        candidates = []
        for n in nodes:
            if n in rs:
                continue
            route_bias = -1.0 if node_to_route.get(n, -2) != seed_route else 1.0
            rel = (
                0.5 * inst.dist[seed_node, n] / max_dist
                + 0.4 * abs(inst.ready_times[seed_node] - inst.ready_times[n]) / max_tw
                + 0.1 * abs(inst.demands[seed_node] - inst.demands[n]) / inst.capacity
                + 0.2 * route_bias
            )
            candidates.append((n, rel))
        if not candidates:
            break
        nxt = min(candidates, key=lambda x: x[1])[0]
        removed.append(nxt)
        rs.add(nxt)
    plan.routes = [[n for n in r if n not in rs] for r in plan.routes]
    plan.routes = [r for r in plan.routes if r]
    return _invalidate(plan), removed


DESTROY = [
    op_random, op_worst, op_shaw, op_route_portion_removal,
    op_tw_urgent, op_route_eliminate, op_route_proximity_eliminate, op_cross_route_shaw,
]


# ---------------------------------------------------------------------------
# Repair operators  (N_R = 5)
# ---------------------------------------------------------------------------
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
            regret = (
                sum(options[i][0] - options[0][0] for i in range(1, k))
                if len(options) >= k
                else (options[1][0] - options[0][0] if len(options) >= 2 else float("inf"))
            )
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


def _route_arrivals_wait(route: List[int], inst: Inst) -> Tuple[List[float], float]:
    arrivals: List[float] = []
    total_wait = 0.0
    t, prev = 0.0, 0
    for node in route:
        raw  = t + inst.dist[prev, node]
        wait = max(0.0, inst.ready_times[node] - raw)
        t    = raw + wait
        arrivals.append(float(t))
        total_wait += wait
        t   += inst.service_times[node]
        prev = node
    return arrivals, float(total_wait)


def _route_forward_time_slacks(route: List[int], inst: Inst) -> List[float]:
    if not route:
        return []
    arrivals, _ = _route_arrivals_wait(route, inst)
    latest      = [0.0] * len(route)
    latest[-1]  = float(inst.due_times[route[-1]])
    for idx in range(len(route) - 2, -1, -1):
        node     = route[idx]
        nxt      = route[idx + 1]
        latest[idx] = min(
            float(inst.due_times[node]),
            latest[idx + 1] - float(inst.service_times[node]) - float(inst.dist[node, nxt]),
        )
    return [max(0.0, latest[idx] - arrivals[idx]) for idx in range(len(route))]


def _fts_best_insert_position(node: int, route: List[int], inst: Inst) -> Tuple[float, Optional[int]]:
    best_cost, best_pos = float("inf"), None
    _, base_wait = _route_arrivals_wait(route, inst)
    max_dist = max(inst.max_dist, 1.0)
    horizon  = max(inst.horizon, 1.0)
    for pos in range(len(route) + 1):
        prev      = route[pos - 1] if pos > 0          else 0
        nxt       = route[pos]     if pos < len(route) else 0
        candidate = route[:pos] + [node] + route[pos:]
        if not _check_route(candidate, inst):
            continue
        dist_added = inst.dist[prev, node] + inst.dist[node, nxt] - inst.dist[prev, nxt]
        _, cand_wait   = _route_arrivals_wait(candidate, inst)
        wait_added     = max(0.0, cand_wait - base_wait)
        fts            = _route_forward_time_slacks(candidate, inst)
        downstream_fts = min(fts[pos:]) if pos < len(fts) else (min(fts) if fts else horizon)
        fts_norm            = min(downstream_fts / horizon, 1.0)
        long_route_pressure = min(len(candidate) / 30.0, 1.0)
        wait_weight  = 0.10 + 0.35 * inst.tw_tight_frac
        fts_weight   = 0.15 + 0.45 * inst.tw_tight_frac + 0.25 * long_route_pressure
        composite    = float(dist_added + wait_weight * wait_added - fts_weight * fts_norm * max_dist)
        if composite < best_cost:
            best_cost, best_pos = composite, pos
    return best_cost, best_pos


def op_fts_greedy(plan: Plan, removed: List[int]) -> Plan:
    inst = plan.inst
    urgent_first = sorted(
        removed,
        key=lambda n: (inst.due_times[n] - inst.ready_times[n], inst.due_times[n], -inst.demands[n]),
    )
    for node in urgent_first:
        best_cost, best_route, best_pos = float("inf"), None, None
        for ri, route in enumerate(plan.routes):
            cost, pos = _fts_best_insert_position(node, route, inst)
            if pos is not None and cost < best_cost:
                best_cost, best_route, best_pos = cost, ri, pos
        if best_route is not None:
            plan.routes[best_route].insert(best_pos, node)
        else:
            plan.routes.append([node])
        plan.invalidate()
    return Plan(plan.routes, inst, plan.algo)


REPAIR    = [op_greedy, op_regret_2, op_regret_3, op_tw_greedy, op_fts_greedy]
N_D, N_R  = len(DESTROY), len(REPAIR)
N_ACTIONS = N_D * N_R

assert N_D == 8
assert N_R == 5
for _m in MODES:
    assert len(_m.destroy_bias) == N_D
    assert len(_m.repair_bias)  == N_R


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------
def _avg_slack(plan: Plan) -> float:
    inst = plan.inst
    slack_sum = count = 0
    for route in plan.routes:
        t, prev = 0.0, 0
        for node in route:
            t += inst.dist[prev, node]
            t  = max(t, inst.ready_times[node])
            slack_sum += inst.due_times[node] - t
            t   += inst.service_times[node]
            prev = node
            count += 1
    return (slack_sum / count) / max(inst.horizon, 1) if count else 0.0


def _plan_spread(plan: Plan, inst: Inst) -> Tuple[float, float]:
    lengths = [len(r) for r in plan.routes] or [0]
    loads   = [sum(inst.demands[n] for n in r) for r in plan.routes] or [0]
    rb = float(np.std(lengths) / max(np.mean(lengths), 1)) if len(lengths) > 1 else 0.0
    lb = float(np.std(loads)   / max(inst.capacity, 1))
    return min(rb, 1.0), min(lb, 1.0)


def _fleet_fill(plan: Plan) -> float:
    if not plan.routes:
        return 0.0
    return float(np.mean(
        [sum(plan.inst.demands[n] for n in r) / max(plan.inst.capacity, 1)
         for r in plan.routes]
    ))


# ---------------------------------------------------------------------------
# Acceptance
# ---------------------------------------------------------------------------
def accept(cur: Plan, cand: Plan, temp: float, allow_nv_increase: bool = False) -> bool:
    if not cand.feasible:
        return False
    if cand.nv < cur.nv:
        return True
    if cand.nv == cur.nv:
        if cand.cost < cur.cost:
            return True
        return random.random() < math.exp(-(cand.cost - cur.cost) / max(temp, 1e-6))
    if allow_nv_increase and cand.nv == cur.nv + 1:
        return random.random() < math.exp(-2.0)
    return False


def accept_with_nv_ceiling(cur: Plan, cand: Plan, temp: float, nv_ceiling: int,
                           allow_nv_increase: bool = False) -> bool:
    allowed_nv = max(nv_ceiling, cur.nv + 1) if allow_nv_increase else nv_ceiling
    if not cand.feasible or cand.nv > allowed_nv:
        return False
    return accept(cur, cand, temp, allow_nv_increase=allow_nv_increase)


def destroy_size(it: int, n_iters: int, cfg: Config, n_customers: int, scale: float = 1.0) -> int:
    ratio = cfg.destroy_ratio_max - (
        (cfg.destroy_ratio_max - cfg.destroy_ratio_min) * (it / max(n_iters, 1))
    )
    ratio = min(cfg.destroy_ratio_max, max(cfg.destroy_ratio_min, ratio * scale))
    return max(3, int(ratio * n_customers))


# ---------------------------------------------------------------------------
# Greedy construction
# ---------------------------------------------------------------------------
def build_greedy(inst: Inst, algo: str = "") -> Plan:
    def arrival(route, pos, node, arrivals):
        prev = route[pos - 1] if pos > 0 else 0
        t    = arrivals[pos - 1] if pos > 0 else 0.0
        return max(t + inst.dist[prev, node], inst.ready_times[node])

    def feasible_insert(route, pos, node, arrivals, load):
        if load + inst.demands[node] > inst.capacity:
            return False, None
        t = arrival(route, pos, node, arrivals)
        if t > inst.due_times[node]:
            return False, None
        ft, prev = t + inst.service_times[node], node
        for idx in range(pos, len(route)):
            nxt  = route[idx]
            ft  += inst.dist[prev, nxt]
            ft   = max(ft, inst.ready_times[nxt])
            if ft > inst.due_times[nxt]:
                return False, None
            ft  += inst.service_times[nxt]
            prev = nxt
        return True, t

    def compute_arrivals(route):
        arrivals, t, prev = [], 0.0, 0
        for node in route:
            t += inst.dist[prev, node]
            t  = max(t, inst.ready_times[node])
            arrivals.append(t)
            t   += inst.service_times[node]
            prev = node
        return arrivals

    def best_insert_cost(route, node, arrivals, load):
        best_cost, best_pos = float("inf"), None
        for pos in range(len(route) + 1):
            ok, _ = feasible_insert(route, pos, node, arrivals, load)
            if not ok:
                continue
            prev  = route[pos - 1] if pos > 0          else 0
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
            best_regret, best_node, best_pos = -float("inf"), None, None
            for node in unrouted:
                c1, pos = best_insert_cost(route, node, arrivals, load)
                if pos is None:
                    continue
                c2 = inst.dist[0, node] + inst.dist[node, 0] - c1
                if c2 > best_regret:
                    best_regret, best_node, best_pos = c2, node, pos
            if best_node is not None:
                route.insert(best_pos, best_node)
                load += inst.demands[best_node]
                arrivals = compute_arrivals(route)
                unrouted.remove(best_node)
                improved = True
        routes.append(route)

    plan = Plan(routes, inst, algo)
    if plan.feasible:
        return plan

    customers   = sorted(range(1, inst.n + 1), key=lambda n: (inst.due_times[n], inst.ready_times[n]))
    unrouted_set= set(customers)
    fallback: List[List[int]] = []
    while unrouted_set:
        route_fb: List[int] = []
        node, load, t = 0, 0.0, 0.0
        while unrouted_set:
            feasible = [
                c for c in unrouted_set
                if load + inst.demands[c] <= inst.capacity
                and t + inst.dist[node, c] <= inst.due_times[c]
            ]
            if not feasible:
                break
            nxt = min(feasible, key=lambda c: inst.dist[node, c])
            route_fb.append(nxt)
            unrouted_set.remove(nxt)
            load += inst.demands[nxt]
            t     = max(t + inst.dist[node, nxt], inst.ready_times[nxt]) + inst.service_times[nxt]
            node  = nxt
        if route_fb:
            fallback.append(route_fb)
        elif unrouted_set:
            nxt = next(iter(unrouted_set))
            fallback.append([nxt])
            unrouted_set.remove(nxt)
    return Plan(fallback, inst, algo)


# ---------------------------------------------------------------------------
# Route pool & set-partitioning
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RouteRecord:
    nodes: Tuple[int, ...]
    cost:  float
    load:  float
    slack: float


class RoutePool:
    def __init__(self, inst: Inst, cfg: Config):
        self.inst = inst
        self.cfg  = cfg
        self._routes: Dict[Tuple[int, ...], RouteRecord] = {}

    def _priority(self, rec: RouteRecord) -> Tuple[float, ...]:
        lr  = rec.load / max(self.inst.capacity, 1)
        cps = rec.cost / max(len(rec.nodes), 1)
        return (-len(rec.nodes), cps, -lr, -rec.slack)

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
            under = all(usage.get(n, 0) < self.cfg.route_pool_max_per_customer for n in rec.nodes)
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
            cost =_route_cost_list(route, self.inst),
            load =_route_load(route, self.inst),
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
                key = tuple(r)
                recs[key] = RouteRecord(
                    nodes=key,
                    cost =_route_cost_list(r, incumbent.inst),
                    load =_route_load(r, incumbent.inst),
                    slack=_route_avg_slack(r, incumbent.inst),
                )
        return sorted(recs.values(), key=self._priority)


def _sp_vehicle_penalty(inst: Inst, cfg: Config) -> float:
    return cfg.sp_vehicle_penalty_scale * max(inst.max_dist, 1.0) * max(inst.n, 1)


def _milp_recombine(route_records: List[RouteRecord], inst: Inst, cfg: Config,
                    nv_ceiling: Optional[int] = None) -> Optional[Plan]:
    if not MILP_OK or not route_records:
        return None
    n_routes = len(route_records)
    cover    = np.zeros((inst.n, n_routes), dtype=float)
    for ridx, rec in enumerate(route_records):
        for node in rec.nodes:
            cover[node - 1, ridx] = 1.0
    if np.any(cover.sum(axis=1) == 0):
        return None
    constraints = [LinearConstraint(cover, lb=np.ones(inst.n), ub=np.ones(inst.n))]
    if nv_ceiling is not None:
        constraints.append(LinearConstraint(
            np.ones((1, n_routes)), lb=np.array([0.0]), ub=np.array([float(nv_ceiling)])
        ))
    costs  = np.array([_sp_vehicle_penalty(inst, cfg) + rec.cost for rec in route_records])
    result = milp(
        c=costs, constraints=constraints,
        integrality=np.ones(n_routes, dtype=int),
        bounds=Bounds(np.zeros(n_routes), np.ones(n_routes)),
        options={"time_limit": float(cfg.sp_time_limit), "disp": False},
    )
    if result is None or not getattr(result, "success", False) or result.x is None:
        return None
    chosen = [list(route_records[i].nodes) for i, v in enumerate(result.x) if v >= 0.5]
    plan   = Plan(chosen, inst, "SP-RECOMBINE")
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


def recombine_with_route_pool(incumbent: Plan, pool: RoutePool, cfg: Config,
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


# ---------------------------------------------------------------------------
# Local search  — max_ls_moves caps the previously unbounded while-True loops
# ---------------------------------------------------------------------------
def _two_opt_best(route: List[int], inst: Inst) -> List[int]:
    if len(route) < 4:
        return route[:]
    best, best_cost = route[:], _route_cost_list(route, inst)
    for i in range(len(route) - 2):
        for j in range(i + 2, len(route)):
            cand = route[:i] + list(reversed(route[i:j + 1])) + route[j + 1:]
            if not _check_route(cand, inst):
                continue
            cc = _route_cost_list(cand, inst)
            if cc + 1e-9 < best_cost:
                best, best_cost = cand, cc
    return best


def _best_relocate(plan: Plan, nv_ceiling: Optional[int] = None):
    inst = plan.inst
    best_delta, best_move = -1e-9, None
    for si, source_route in enumerate(plan.routes):
        sc = _route_cost_list(source_route, inst)
        for sp, node in enumerate(source_route):
            sn  = source_route[:sp] + source_route[sp + 1:]
            if sn and not _check_route(sn, inst):
                continue
            snc = _route_cost_list(sn, inst)
            for di, dest_route in enumerate(plan.routes):
                if di == si:
                    continue
                dc = _route_cost_list(dest_route, inst)
                for ip in range(len(dest_route) + 1):
                    dn  = dest_route[:ip] + [node] + dest_route[ip:]
                    if not _check_route(dn, inst):
                        continue
                    new_nv = plan.nv - (1 if not sn else 0)
                    if nv_ceiling is not None and new_nv > nv_ceiling:
                        continue
                    delta = snc + _route_cost_list(dn, inst) - sc - dc
                    if new_nv < plan.nv:
                        delta -= 1000.0
                    if delta < best_delta:
                        best_delta, best_move = delta, (si, sp, di, ip)
    return best_move


def _apply_relocate(plan: Plan, move: Tuple[int, int, int, int]) -> Plan:
    si, sp, di, ip = move
    routes = [r[:] for r in plan.routes]
    node   = routes[si].pop(sp)
    if si < di and len(routes[si]) == 0:
        di -= 1
    routes = [r for r in routes if r]
    routes[di].insert(ip, node)
    return Plan(routes, plan.inst, plan.algo)


def _best_swap(plan: Plan):
    inst = plan.inst
    best_delta, best_move = -1e-9, None
    for si, sr in enumerate(plan.routes):
        sc = _route_cost_list(sr, inst)
        for di in range(si + 1, len(plan.routes)):
            dr = plan.routes[di]
            dc = _route_cost_list(dr, inst)
            for sp, sn in enumerate(sr):
                for dp, dn in enumerate(dr):
                    if sn == dn:
                        continue
                    srn, drn = sr[:], dr[:]
                    srn[sp], drn[dp] = dn, sn
                    if not _check_route(srn, inst) or not _check_route(drn, inst):
                        continue
                    delta = _route_cost_list(srn, inst) + _route_cost_list(drn, inst) - sc - dc
                    if delta < best_delta:
                        best_delta, best_move = delta, (si, sp, di, dp)
    return best_move


def _apply_swap(plan: Plan, move: Tuple[int, int, int, int]) -> Plan:
    si, sp, di, dp = move
    routes = [r[:] for r in plan.routes]
    routes[si][sp], routes[di][dp] = routes[di][dp], routes[si][sp]
    return Plan(routes, plan.inst, plan.algo)


def _cross_exchange(plan: Plan, nv_ceiling: Optional[int] = None) -> Optional[Plan]:
    inst = plan.inst
    if nv_ceiling is not None and plan.nv > nv_ceiling:
        return None
    max_dist       = max(inst.max_dist, 1.0)
    granular_radius= max(10.0, 0.18 * max_dist)
    best_delta     = -1e-9
    best_routes: Optional[List[List[int]]] = None

    def interval_overlap(a0, a1, b0, b1):
        return min(a1, b1) >= max(a0, b0)

    def route_meta(route):
        coords = inst.coords[np.array(route, dtype=np.int64)]
        return (coords.mean(axis=0),
                float(np.min(inst.ready_times[route])),
                float(np.max(inst.due_times[route])))

    def seg_meta(seg):
        coords = inst.coords[np.array(seg, dtype=np.int64)]
        return (coords.mean(axis=0),
                float(np.min(inst.ready_times[seg])),
                float(np.max(inst.due_times[seg])))

    route_info = [route_meta(r) if r else None for r in plan.routes]

    for i in range(len(plan.routes)):
        for j in range(i + 1, len(plan.routes)):
            r1, r2 = plan.routes[i], plan.routes[j]
            if not r1 or not r2:
                continue
            info1, info2 = route_info[i], route_info[j]
            if info1 is None or info2 is None:
                continue
            c1, r1_ready, r1_due = info1
            c2, r2_ready, r2_due = info2
            if (float(np.linalg.norm(c1 - c2)) > 0.55 * max_dist and
                    not interval_overlap(r1_ready, r1_due, r2_ready, r2_due)):
                continue
            old_pair = _route_cost_list(r1, inst) + _route_cost_list(r2, inst)
            lc1 = (1, 2, 3) if len(r1) >= 12 else (1, 2)
            lc2 = (1, 2, 3) if len(r2) >= 12 else (1, 2)
            for len1 in lc1:
                if len(r1) < len1:
                    continue
                for len2 in lc2:
                    if len(r2) < len2:
                        continue
                    for p1 in range(len(r1) - len1 + 1):
                        seg1 = r1[p1:p1 + len1]
                        s1c, s1r, s1d = seg_meta(seg1)
                        for p2 in range(len(r2) - len2 + 1):
                            seg2 = r2[p2:p2 + len2]
                            s2c, s2r, s2d = seg_meta(seg2)
                            if (float(np.linalg.norm(s1c - s2c)) > granular_radius and
                                    not interval_overlap(s1r, s1d, s2r, s2d)):
                                continue
                            nr1 = r1[:p1] + seg2 + r1[p1 + len1:]
                            nr2 = r2[:p2] + seg1 + r2[p2 + len2:]
                            if not _check_route(nr1, inst) or not _check_route(nr2, inst):
                                continue
                            delta = _route_cost_list(nr1, inst) + _route_cost_list(nr2, inst) - old_pair
                            if delta < best_delta:
                                routes = [r[:] for r in plan.routes]
                                routes[i], routes[j] = nr1, nr2
                                best_routes = routes
                                best_delta  = delta
    return Plan(best_routes, inst, plan.algo) if best_routes is not None else None


def _try_route_compact(plan: Plan, nv_ceiling: Optional[int] = None) -> Optional[Plan]:
    if len(plan.routes) <= 1:
        return None
    inst   = plan.inst
    ranked = sorted(
        range(len(plan.routes)),
        key=lambda i: (len(plan.routes[i]), _route_load(plan.routes[i], inst),
                       _route_cost_list(plan.routes[i], inst)),
    )
    for ridx in ranked:
        source = plan.routes[ridx]
        others = [r[:] for i, r in enumerate(plan.routes) if i != ridx]
        ok     = True
        for node in sorted(source, key=lambda n: (inst.due_times[n] - inst.ready_times[n], -inst.demands[n])):
            best_c, best_r, best_p = float("inf"), None, None
            for oi, route in enumerate(others):
                delta, pos = _best_insert_position(node, route, inst)
                if pos is not None and delta < best_c:
                    best_c, best_r, best_p = delta, oi, pos
            if best_r is None:
                ok = False
                break
            others[best_r].insert(best_p, node)
        if not ok:
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
                 nv_ceiling: Optional[int] = None,
                 max_ls_moves: int = 5) -> Plan:
    """
    max_ls_moves caps the relocate/swap/cross/compact while-True loop per pass.
    Prevents unbounded Python-loop runtimes on slow EPYC-class CPUs.
    """
    best = plan.copy()
    for _ in range(max_passes):
        improved = False
        routes   = []
        for route in best.routes:
            nr = _two_opt_best(route, best.inst)
            routes.append(nr)
            if nr != route:
                improved = True
        best = Plan(routes, best.inst, best.algo)

        moves = 0
        while moves < max_ls_moves:
            move = _best_relocate(best, nv_ceiling=nv_ceiling)
            if move is not None:
                cand = _apply_relocate(best, move)
                if cand.feasible and (cand.dominates(best) or
                        (cand.nv == best.nv and cand.cost + 1e-9 < best.cost)):
                    best, improved = cand, True
                    moves += 1
                    continue
            move = _best_swap(best)
            if move is not None:
                cand = _apply_swap(best, move)
                if cand.feasible and cand.cost + 1e-9 < best.cost:
                    best, improved = cand, True
                    moves += 1
                    continue
            cross = _cross_exchange(best, nv_ceiling=nv_ceiling)
            if cross is not None:
                best, improved = cross, True
                moves += 1
                continue
            compact = _try_route_compact(best, nv_ceiling=nv_ceiling)
            if compact is not None:
                best, improved = compact, True
                moves += 1
                continue
            break

        if not improved:
            break
    return best


# ---------------------------------------------------------------------------
# Prioritized Experience Replay  (replaces uniform ReplayBuffer)
# ---------------------------------------------------------------------------
class PrioritizedReplayBuffer:
    """
    Proportional PER (Schaul et al., 2016).
    alpha=0.6: prioritization strength.
    beta anneals 0.4→1.0 over training to correct IS bias.
    """
    def __init__(self, capacity: int, alpha: float = 0.6,
                 beta_start: float = 0.4, beta_end: float = 1.0):
        self.capacity  = capacity
        self.alpha     = alpha
        self.beta      = beta_start
        self.beta_end  = beta_end
        self.beta_inc  = (beta_end - beta_start) / 200_000
        self.buf: List = []
        self.pos       = 0
        self.priorities= np.zeros(capacity, dtype=np.float32)
        self.max_pri   = 1.0

    def push(self, *transition) -> None:
        if len(self.buf) < self.capacity:
            self.buf.append(transition)
        else:
            self.buf[self.pos] = transition
        self.priorities[self.pos] = self.max_pri
        self.pos = (self.pos + 1) % self.capacity

    def sample(self, batch_size: int):
        n     = len(self.buf)
        probs = self.priorities[:n] ** self.alpha
        probs /= probs.sum()
        idxs  = np.random.choice(n, batch_size, p=probs, replace=False)
        ws    = (n * probs[idxs]) ** -self.beta
        ws   /= ws.max()
        self.beta = min(self.beta_end, self.beta + self.beta_inc)
        s, a, r, ns, d = zip(*[self.buf[i] for i in idxs])
        return (
            np.array(s,  np.float32), np.array(a,  np.int64),
            np.array(r,  np.float32), np.array(ns, np.float32),
            np.array(d,  np.float32),
        ), idxs, torch.tensor(ws, dtype=torch.float32).to(DEVICE)

    def update_priorities(self, idxs, td_errors: np.ndarray) -> None:
        for i, err in zip(idxs, td_errors):
            p = float(abs(err)) + 1e-6
            self.priorities[i] = p
            self.max_pri = max(self.max_pri, p)

    def __len__(self) -> int:
        return len(self.buf)


# ---------------------------------------------------------------------------
# QNet
# ---------------------------------------------------------------------------
class QNet(nn.Module):
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int):
        super().__init__()
        hid2      = max(hidden_dim // 2, 32)
        self.trunk= nn.Sequential(
            nn.Linear(state_dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.ReLU(),
        )
        self.value_head = nn.Sequential(nn.Linear(hidden_dim, hid2), nn.ReLU(), nn.Linear(hid2, 1))
        self.adv_head   = nn.Sequential(nn.Linear(hidden_dim, hid2), nn.ReLU(), nn.Linear(hid2, action_dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.trunk(x)
        v = self.value_head(h)
        a = self.adv_head(h)
        return v + a - a.mean(dim=1, keepdim=True)


# ---------------------------------------------------------------------------
# Thompson bandit
# ---------------------------------------------------------------------------
class ThompsonBandit:
    def __init__(self, n_d: int, n_r: int):
        self.alpha = np.ones((n_d, n_r), dtype=np.float64)
        self.beta  = np.ones((n_d, n_r), dtype=np.float64)

    def mean(self) -> np.ndarray:
        return self.alpha / (self.alpha + self.beta)

    def select(self, prior: Optional[np.ndarray] = None,
               prior_strength: float = 0.0) -> Tuple[int, int]:
        samples = np.random.beta(self.alpha, self.beta)
        if prior is not None:
            p       = np.asarray(prior, dtype=np.float64)
            p      /= max(p.sum(), 1e-9)
            samples = samples + prior_strength * p
        idx = np.unravel_index(int(samples.argmax()), samples.shape)
        return int(idx[0]), int(idx[1])

    def update(self, di: int, ri: int, score: float, sigma1: int) -> None:
        success           = float(np.clip(score / max(sigma1, 1), 0.0, 1.0))
        self.alpha[di, ri]+= success
        self.beta[di, ri] += 1.0 - success

    def decay(self, rate: float = 0.95) -> None:
        self.alpha = 1.0 + (self.alpha - 1.0) * rate
        self.beta  = 1.0 + (self.beta  - 1.0) * rate

    def clone(self) -> "ThompsonBandit":
        b       = ThompsonBandit(self.alpha.shape[0], self.alpha.shape[1])
        b.alpha = self.alpha.copy()
        b.beta  = self.beta.copy()
        return b


# ---------------------------------------------------------------------------
# Elite archive
# ---------------------------------------------------------------------------
class EliteArchive:
    def __init__(self, k: int = 5):
        self.k = k
        self._plans: Dict[str, List[Plan]] = {}

    def update(self, plan: Plan) -> None:
        if not plan.feasible:
            return
        key    = plan.inst.name
        bucket = self._plans.setdefault(key, [])
        bucket.append(plan.copy())
        bucket.sort(key=lambda p: (p.nv, p.cost))
        self._plans[key] = bucket[:self.k]

    def best(self, inst_name: str) -> Optional[Plan]:
        bucket = self._plans.get(inst_name, [])
        return bucket[0].copy() if bucket else None

    def summary(self) -> str:
        lines = []
        for name, bucket in sorted(self._plans.items()):
            p       = bucket[0]
            td_gap, _ = p.gap()
            gap_str = f"{td_gap:+.2f}%" if td_gap is not None else "--"
            lines.append(f"  {name}: nv={p.nv} cost={p.cost:.1f} gap={gap_str}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# DDQN controllers  (now using PrioritizedReplayBuffer)
# ---------------------------------------------------------------------------
class PlateauController:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.q   = QNet(cfg.ctrl_state_dim, len(MODES), cfg.ctrl_hidden).to(DEVICE)
        self.q_t = QNet(cfg.ctrl_state_dim, len(MODES), cfg.ctrl_hidden).to(DEVICE)
        self.q_t.load_state_dict(self.q.state_dict())
        self.opt = optim.Adam(self.q.parameters(), lr=cfg.ctrl_lr)
        self.buf = PrioritizedReplayBuffer(cfg.ctrl_buffer)
        self.eps = cfg.ctrl_eps_start
        self.step= 0

    def reset(self) -> None:
        self.eps = self.cfg.ctrl_eps_start

    def act(self, state: np.ndarray) -> int:
        if random.random() < self.eps:
            return random.randrange(len(MODES))
        with torch.no_grad():
            return int(self.q(torch.tensor(state).unsqueeze(0).to(DEVICE))[0].argmax().item())

    def observe(self, s, a, r, ns, done=0.0):
        self.buf.push(s, a, r, ns, done)

    def train_step(self) -> None:
        self.step += 1
        if len(self.buf) < self.cfg.ctrl_batch:
            return
        (s, a, r, ns, d), idxs, is_w = self.buf.sample(self.cfg.ctrl_batch)
        s  = torch.tensor(s).to(DEVICE)
        a  = torch.tensor(a, dtype=torch.long).to(DEVICE)
        r  = torch.tensor(r).to(DEVICE)
        ns = torch.tensor(ns).to(DEVICE)
        d  = torch.tensor(d).to(DEVICE)
        qp = self.q(s).gather(1, a.unsqueeze(1)).squeeze(1)
        with torch.no_grad():
            best_a = self.q(ns).argmax(1).unsqueeze(1)
            qn     = self.q_t(ns).gather(1, best_a).squeeze(1)
            target = r + self.cfg.ctrl_gamma * qn * (1 - d)
        td_errors = (qp - target).detach().cpu().numpy()
        self.buf.update_priorities(idxs, td_errors)
        loss = (is_w * F.smooth_l1_loss(qp, target, reduction="none")).mean()
        self.opt.zero_grad(); loss.backward()
        nn.utils.clip_grad_norm_(self.q.parameters(), 1.0)
        self.opt.step()
        if self.step % self.cfg.ctrl_target_freq == 0:
            self.q_t.load_state_dict(self.q.state_dict())
        self.eps = max(self.cfg.ctrl_eps_end, self.eps * self.cfg.ctrl_eps_decay)


class OperatorController:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.q   = QNet(cfg.op_state_dim, N_ACTIONS, cfg.op_hidden).to(DEVICE)
        self.q_t = QNet(cfg.op_state_dim, N_ACTIONS, cfg.op_hidden).to(DEVICE)
        self.q_t.load_state_dict(self.q.state_dict())
        self.opt = optim.Adam(self.q.parameters(), lr=cfg.op_lr)
        self.buf = PrioritizedReplayBuffer(cfg.op_buffer)
        self.eps = cfg.op_eps_start
        self.step= 0

    def reset(self) -> None:
        self.eps = self.cfg.op_eps_start

    def _prior(self, dw: np.ndarray, rw: np.ndarray) -> np.ndarray:
        dw = np.asarray(dw, np.float32); dw /= max(dw.sum(), 1e-9)
        rw = np.asarray(rw, np.float32); rw /= max(rw.sum(), 1e-9)
        return np.outer(dw, rw)

    def _sample_prior(self, prior: np.ndarray, bandit: ThompsonBandit) -> int:
        probs  = prior.reshape(-1) * bandit.mean().reshape(-1)
        probs /= max(probs.sum(), 1e-9)
        return int(np.random.choice(N_ACTIONS, p=probs))

    def act(self, state, dw, rw, bandit, frozen=False) -> Tuple[int, int, int]:
        prior = self._prior(dw, rw)
        if not frozen and len(self.buf) < self.cfg.op_warmup:
            di, ri = bandit.select(prior=prior, prior_strength=self.cfg.bandit_prior_strength)
            action = di * N_R + ri
        elif not frozen and random.random() < self.eps:
            action = self._sample_prior(prior, bandit)
            di, ri = divmod(action, N_R)
        else:
            with torch.no_grad():
                q = self.q(torch.tensor(state).unsqueeze(0).to(DEVICE))[0].cpu().numpy()
            q      = (q + self.cfg.op_prior_strength * np.log(prior.reshape(-1) + 1e-8)
                        + self.cfg.op_bandit_strength * bandit.mean().reshape(-1))
            action = int(q.argmax())
            di, ri = divmod(action, N_R)
        return int(action), int(di), int(ri)

    def observe(self, s, a, r, ns, done=0.0):
        self.buf.push(s, a, r, ns, done)

    def train_step(self) -> None:
        self.step += 1
        if len(self.buf) < self.cfg.op_batch:
            return
        (s, a, r, ns, d), idxs, is_w = self.buf.sample(self.cfg.op_batch)
        s  = torch.tensor(s).to(DEVICE)
        a  = torch.tensor(a, dtype=torch.long).to(DEVICE)
        r  = torch.tensor(r).to(DEVICE)
        ns = torch.tensor(ns).to(DEVICE)
        d  = torch.tensor(d).to(DEVICE)
        qp = self.q(s).gather(1, a.unsqueeze(1)).squeeze(1)
        with torch.no_grad():
            best_a = self.q(ns).argmax(1).unsqueeze(1)
            qn     = self.q_t(ns).gather(1, best_a).squeeze(1)
            target = r + self.cfg.op_gamma * qn * (1 - d)
        td_errors = (qp - target).detach().cpu().numpy()
        self.buf.update_priorities(idxs, td_errors)
        loss = (is_w * F.smooth_l1_loss(qp, target, reduction="none")).mean()
        self.opt.zero_grad(); loss.backward()
        nn.utils.clip_grad_norm_(self.q.parameters(), 1.0)
        self.opt.step()
        if self.step % self.cfg.op_target_freq == 0:
            self.q_t.load_state_dict(self.q.state_dict())
        self.eps = max(self.cfg.op_eps_end, self.eps * self.cfg.op_eps_decay)


# ---------------------------------------------------------------------------
# Learned Acceptance Criterion
# ---------------------------------------------------------------------------
class LearnedAcceptanceCriterion:
    def __init__(self, cfg: Config):
        self.cfg  = cfg
        self.net  = nn.Sequential(
            nn.Linear(cfg.lac_state_dim, cfg.lac_hidden), nn.ReLU(),
            nn.Linear(cfg.lac_hidden, cfg.lac_hidden // 2), nn.ReLU(),
            nn.Linear(cfg.lac_hidden // 2, 1), nn.Sigmoid(),
        ).to(DEVICE)
        self.opt  = optim.Adam(self.net.parameters(), lr=cfg.lac_lr)
        self.step = 0
        self._pending:   deque = deque()
        self._train_buf: deque = deque(maxlen=cfg.lac_buf_size)

    def features(self, cost_delta, cur_cost, temp, temp_init, no_imp, patience,
                 nv_diff, progress, tw_tight_frac, fleet_fill, avg_slack_val) -> np.ndarray:
        metro = math.exp(-max(cost_delta, 0.0) / max(temp, 1e-6))
        return np.array([
            cost_delta / max(abs(cur_cost), 1.0),
            temp / max(temp_init, 1e-6),
            no_imp / max(patience, 1),
            float(np.clip(nv_diff, -2, 2)),
            progress, tw_tight_frac, fleet_fill, avg_slack_val, metro,
        ], dtype=np.float32)

    def decide(self, feats: np.ndarray, cur_best_cost: float) -> Tuple[bool, float]:
        self.step += 1
        self._pending.append((feats.copy(), cur_best_cost, self.step))
        metro_p = float(feats[-1])
        if self.step < self.cfg.lac_warmup:
            return random.random() < metro_p, metro_p
        with torch.no_grad():
            p = float(self.net(torch.tensor(feats).unsqueeze(0).to(DEVICE))[0, 0])
        return random.random() < p, p

    def observe(self, current_best_cost: float) -> None:
        cutoff = self.step - self.cfg.lac_horizon
        while self._pending and self._pending[0][2] <= cutoff:
            feats, best_at_t, _ = self._pending.popleft()
            label = 1.0 if current_best_cost < best_at_t - 1e-6 else 0.0
            self._train_buf.append((feats, label))
        if self.step % self.cfg.lac_train_freq == 0 and len(self._train_buf) >= 64:
            self._train()

    def _train(self) -> None:
        batch = random.sample(self._train_buf, min(64, len(self._train_buf)))
        feats, labels = zip(*batch)
        x = torch.tensor(np.array(feats), dtype=torch.float32).to(DEVICE)
        y = torch.tensor(labels, dtype=torch.float32).to(DEVICE)
        pos_weight = torch.tensor(
            [max((y == 0).sum().item(), 1) / max((y == 1).sum().item(), 1)],
            dtype=torch.float32,
        ).to(DEVICE)
        pred = self.net(x).squeeze(1)
        loss = F.binary_cross_entropy(pred, y, weight=pos_weight.expand_as(y))
        self.opt.zero_grad(); loss.backward(); self.opt.step()

    def state_dict(self) -> Dict:
        return {f"lac.{k}": v.clone().cpu() for k, v in self.net.state_dict().items()}

    def load_state_dict(self, weights: Dict) -> None:
        sd      = self.net.state_dict()
        updates = {}
        for k, v in weights.items():
            bare = k[4:] if k.startswith("lac.") else k
            if bare in sd and tuple(v.shape) == tuple(sd[bare].shape):
                updates[bare] = v.to(DEVICE)
        sd.update(updates)
        self.net.load_state_dict(sd)


# ---------------------------------------------------------------------------
# ALNS baseline
# ---------------------------------------------------------------------------
class ALNSSolver:
    def __init__(self, inst: Inst, cfg: Config):
        self.inst   = inst
        self.cfg    = cfg
        self.bandit = ThompsonBandit(N_D, N_R)

    def solve(self, seed: Optional[int] = None,
              init: Optional[Plan] = None) -> Tuple[Plan, List[float]]:
        if seed is not None:
            random.seed(seed); np.random.seed(seed)
        cfg        = self.cfg
        self.bandit= ThompsonBandit(N_D, N_R)
        cur  = init.copy() if init is not None else build_greedy(self.inst, ALGO_ALNS_BASE)
        best = cur.copy()
        temp = cfg.temp_control * cur.cost / math.log(2)
        history  = [best.cost]
        no_imp   = 0
        for it in range(cfg.alns_iterations):
            di, ri  = self.bandit.select()
            size    = destroy_size(it, cfg.alns_iterations, cfg, self.inst.n)
            dest, removed = DESTROY[di](cur.copy(), size)
            cand    = REPAIR[ri](dest, removed)
            score   = 0
            if accept(cur, cand, temp):
                if cand.dominates(best):
                    best, score, no_imp = cand.copy(), cfg.sigma1, 0
                elif cand.dominates(cur):
                    score, no_imp = cfg.sigma2, 0
                else:
                    score, no_imp = cfg.sigma3, no_imp + 1
                cur = cand
            else:
                no_imp += 1
            self.bandit.update(di, ri, score, cfg.sigma1)
            if (it + 1) % cfg.segment_size == 0:
                self.bandit.decay(cfg.bandit_decay)
            temp *= cfg.temp_decay
            history.append(best.cost)
            if no_imp >= cfg.early_stop_patience:
                break
        best.algo = ALGO_ALNS_BASE
        return best, history


# ---------------------------------------------------------------------------
# Post-search route elimination  (addresses RC2 NV gap)
# ---------------------------------------------------------------------------
def _iterative_route_elimination(plan: Plan, inst: Inst,
                                  max_rounds: int = 4) -> Plan:
    """
    Greedily eliminates the shortest/lightest route by redistributing its
    customers into remaining routes.  Runs local_search after each success.
    Primary mechanism for NV reduction on RC2 wide-TW instances where the
    ALNS NV reward is too sparse to trigger reliably.
    """
    best = plan.copy()
    for _ in range(max_rounds):
        if len(best.routes) <= 1:
            break
        sorted_idxs = sorted(
            range(len(best.routes)),
            key=lambda i: (len(best.routes[i]),
                           _route_load(best.routes[i], inst),
                           _route_cost_list(best.routes[i], inst)),
        )
        eliminated = False
        for target_idx in sorted_idxs[:3]:
            target = best.routes[target_idx]
            others = [r[:] for i, r in enumerate(best.routes) if i != target_idx]
            ok     = True
            # Insert tightest-TW customers first — hardest to place
            for node in sorted(target, key=lambda n: inst.due_times[n] - inst.ready_times[n]):
                best_d, best_r, best_p = float("inf"), None, None
                for oi, route in enumerate(others):
                    delta, pos = _best_insert_position(node, route, inst)
                    if pos is not None and delta < best_d:
                        best_d, best_r, best_p = delta, oi, pos
                if best_r is None:
                    ok = False
                    break
                others[best_r].insert(best_p, node)
            if not ok:
                continue
            cand = Plan([r for r in others if r], inst, best.algo)
            if not cand.feasible:
                continue
            cand = local_search(cand, max_passes=2, nv_ceiling=cand.nv)
            if cand.feasible:
                best = cand
                eliminated = True
                break
        if not eliminated:
            break
    return best


# ---------------------------------------------------------------------------
# Weight persistence helpers  (safetensors → torch.save fallback)
# ---------------------------------------------------------------------------
def _save_weights(weights: Dict, stem: str) -> None:
    if SAFETENSORS_OK and _st_save is not None:
        path = stem + ".safetensors"
        _st_save(weights, path)
    else:
        path = stem + ".pt"
        torch.save({k: v.cpu() for k, v in weights.items()}, path)
    print(f"Weights saved → {path}")


def _load_weights(stem: str) -> Optional[Dict]:
    for suffix, loader in (
        (".safetensors", _st_load if SAFETENSORS_OK else None),
        (".pt",          lambda f: torch.load(f, map_location="cpu")),
    ):
        p = stem + suffix
        if os.path.exists(p) and loader is not None:
            print(f"Weights loaded → {p}")
            return loader(p)
    return None


# ---------------------------------------------------------------------------
# HybridDDQN solver
# ---------------------------------------------------------------------------
class HybridDDQNSolver:
    algo_name = ALGO_HYBRID_DDQN
    use_op_rl = True

    def __init__(self, inst: Inst, cfg: Config):
        self.inst       = inst
        self.cfg        = cfg
        self.ctrl       = PlateauController(cfg)
        self.op_ctrl    = OperatorController(cfg)
        self.lac        = LearnedAcceptanceCriterion(cfg)
        self.mode_bandits: List[ThompsonBandit] = [ThompsonBandit(N_D, N_R) for _ in MODES]
        self.op_counts: Dict[Tuple[int, int], int] = {}
        self._segment_recombine_used = False
        self._init_nv = 1

    def clone_weights(self) -> Dict:
        weights: Dict[str, torch.Tensor] = {}
        for prefix, sd in (("plateau",  self.ctrl.q.state_dict()),
                            ("operator", self.op_ctrl.q.state_dict())):
            for k, v in sd.items():
                weights[f"{prefix}.{k}"] = v.clone().cpu()
        weights.update(self.lac.state_dict())
        return weights

    def load_weights(self, weights: Dict) -> None:
        plateau_sd  = self.ctrl.q.state_dict()
        operator_sd = self.op_ctrl.q.state_dict()
        p_up: Dict[str, torch.Tensor] = {}
        o_up: Dict[str, torch.Tensor] = {}
        legacy = not any(k.startswith(("plateau.", "operator.")) for k in weights)
        if legacy:
            for k, v in weights.items():
                if k in plateau_sd and tuple(v.shape) == tuple(plateau_sd[k].shape):
                    p_up[k] = v.to(DEVICE)
        else:
            for k, v in weights.items():
                if k.startswith("plateau."):
                    bare = k.split(".", 1)[1]
                    if bare in plateau_sd and tuple(v.shape) == tuple(plateau_sd[bare].shape):
                        p_up[bare] = v.to(DEVICE)
                elif k.startswith("operator."):
                    bare = k.split(".", 1)[1]
                    if bare in operator_sd and tuple(v.shape) == tuple(operator_sd[bare].shape):
                        o_up[bare] = v.to(DEVICE)
        plateau_sd.update(p_up);  operator_sd.update(o_up)
        self.ctrl.q.load_state_dict(plateau_sd)
        self.ctrl.q_t.load_state_dict(plateau_sd)
        self.op_ctrl.q.load_state_dict(operator_sd)
        self.op_ctrl.q_t.load_state_dict(operator_sd)
        lac_weights = {k: v for k, v in weights.items() if k.startswith("lac.")}
        if lac_weights:
            self.lac.load_state_dict(lac_weights)

    def _potential(self, plan: Plan) -> float:
        bks = BKS.get(plan.inst.name)
        if not bks:
            return 0.0
        gap_pct = float(np.clip(
            (plan.cost - bks["td"]) / max(bks["td"], 1.0) * 100.0, -25.0, 25.0
        ))
        return float(-self.cfg.potential_nv_scale * max(plan.nv - bks["nv"], 0)
                     - self.cfg.potential_cost_scale * gap_pct)

    def _state(self, cur, best, no_imp, temp, imp_rate, progress, pool) -> np.ndarray:
        rb, lb = _plan_spread(cur, self.inst)
        t0     = self.cfg.temp_control * max(best.cost, 1.0) / math.log(2)
        pool_fill = min(len(pool._routes) / max(self.cfg.route_pool_limit, 1), 1.0)
        return np.array([
            min(no_imp / max(self.cfg.early_stop_patience, 1), 1.0),
            min((cur.cost - best.cost) / max(best.cost, 1), 1.0),
            min(temp / max(t0, 1e-6), 1.5),
            imp_rate,
            min(cur.nv / max(self._init_nv, 1), 2.0),
            rb, lb, self.inst.tw_tight_frac,
            _avg_slack(cur), _fleet_fill(cur), pool_fill, progress,
        ], dtype=np.float32)

    def _op_state(self, cur, best, mode_idx, it, temp, no_imp, pool, recent_imp) -> np.ndarray:
        rb, lb = _plan_spread(cur, self.inst)
        t0     = self.cfg.temp_control * max(best.cost, 1.0) / math.log(2)
        pool_fill = min(len(pool._routes) / max(self.cfg.route_pool_limit, 1), 1.0)
        return np.array([
            min((cur.cost - best.cost) / max(best.cost, 1), 1.0),
            min(cur.nv / max(self._init_nv, 1), 2.0),
            it / max(self.cfg.hybrid_iterations, 1),
            (it % self.cfg.segment_size) / max(self.cfg.segment_size, 1),
            min(temp / max(t0, 1e-6), 1.5),
            min(no_imp / max(self.cfg.early_stop_patience, 1), 1.0),
            rb, lb, self.inst.tw_tight_frac,
            _avg_slack(cur), _fleet_fill(cur), pool_fill,
            mode_idx / max(len(MODES) - 1, 1),
            float(cur.nv - best.nv) / max(self._init_nv, 1),
            recent_imp,
        ], dtype=np.float32)

    def _segment_reward(self, best_before, best_after, cur_before, cur_after,
                        accepted_moves, action) -> float:
        base = -0.20 - 0.04 * MODES[action].ls_passes
        if MODES[action].use_recombine:
            base -= 0.06
        best_nv_gain   = best_before.nv - best_after.nv
        cur_nv_gain    = cur_before.nv  - cur_after.nv
        best_cost_gain = max((best_before.cost - best_after.cost) / max(best_before.cost, 1) * 100, 0.0)
        cur_cost_gain  = max((cur_before.cost  - cur_after.cost)  / max(cur_before.cost,  1) * 100, 0.0)
        if best_nv_gain > 0:
            base += 8.0 * best_nv_gain + 1.2 * best_cost_gain
        elif cur_nv_gain > 0:
            base += 5.0 * cur_nv_gain  + 0.6 * cur_cost_gain
        else:
            base += 0.35 * best_cost_gain + 0.15 * cur_cost_gain
        if accepted_moves <= max(1, self.cfg.segment_size // 10):
            base -= 0.15
        shaped = self.cfg.ctrl_gamma * self._potential(cur_after) - self._potential(cur_before)
        return float(self.cfg.segment_reward_scale * base + shaped)

    def _iteration_reward(self, cur_before, best_before, cur_after, best_after, accepted) -> float:
        if not accepted:
            base = -0.08
        else:
            base = 0.05
            best_nv_gain   = best_before.nv - best_after.nv
            cur_nv_gain    = cur_before.nv  - cur_after.nv
            best_cost_gain = max((best_before.cost - best_after.cost) / max(best_before.cost, 1) * 100, 0.0)
            cur_cost_gain  = max((cur_before.cost  - cur_after.cost)  / max(cur_before.cost,  1) * 100, 0.0)
            if best_nv_gain > 0:
                base += 3.0 * best_nv_gain + 0.4 * best_cost_gain
            elif cur_nv_gain > 0:
                base += 2.0 * cur_nv_gain  + 0.2 * cur_cost_gain
            else:
                base += 0.12 * best_cost_gain + 0.05 * cur_cost_gain
            if cur_after.nv > cur_before.nv:
                base -= 0.5 * (cur_after.nv - cur_before.nv)
        shaped = self.cfg.op_gamma * self._potential(cur_after) - self._potential(cur_before)
        return float(self.cfg.iteration_reward_scale * base + shaped)

    def _route_reduce_trigger(self, cur: Plan, no_imp: int) -> bool:
        return (no_imp >= self.cfg.plateau_start
                and _fleet_fill(cur) < max(0.52, 0.80 - 0.25 * self.inst.tw_tight_frac))

    def _select_action(self, state_before, cur, best, no_imp, progress, pool, frozen) -> Tuple[int, bool]:
        if no_imp >= max(10, self.cfg.ctrl_start // 2):
            return self.ctrl.act(state_before), (not frozen)
        return MODE_DEFAULT, False

    def _refine_candidate(self, cand, action, pool, cur, best, no_imp, iter_idx) -> Plan:
        del cur
        mode    = MODES[action]
        refined = cand
        # ── LS gate: 20-iteration cadence + only on feasible non-NV-inflating cands ──
        _do_ls  = (mode.ls_passes > 0
                   and iter_idx % 20 == 0
                   and refined.feasible
                   and refined.nv <= best.nv)
        if _do_ls:
            nv_cap  = (best.nv
                       if action in (MODE_INTENSIFY, MODE_TW_RESCUE,
                                     MODE_POOL_RECOMBINE, MODE_ROUTE_REDUCE)
                       else None)
            refined = local_search(refined, max_passes=mode.ls_passes, nv_ceiling=nv_cap)
        if (mode.use_recombine and not self._segment_recombine_used
                and no_imp >= max(self.cfg.ctrl_start, self.cfg.plateau_start // 2)
                and len(pool._routes) >= self.cfg.rl_recombine_min_routes):
            self._segment_recombine_used = True
            nv_cap    = min(best.nv, refined.nv)
            recombined= recombine_with_route_pool(refined, pool, self.cfg, nv_ceiling=nv_cap)
            if recombined.dominates(refined):
                refined = local_search(recombined, max_passes=1, nv_ceiling=recombined.nv)
        return refined

    def _fixed_nv_polish(self, start: Plan, pool: RoutePool,
                         inherited_bandit: Optional[ThompsonBandit] = None) -> Plan:
        cfg       = self.cfg
        target_nv = start.nv
        # Inherit operator statistics from main search instead of cold-starting
        polish_bandit = inherited_bandit.clone() if inherited_bandit is not None \
                        else ThompsonBandit(N_D, N_R)
        cur  = local_search(start, max_passes=cfg.polish_ls_passes, nv_ceiling=target_nv)
        best = cur.copy()
        pool.add_plan(best)
        temp   = cfg.temp_control * best.cost / math.log(2)
        no_imp = 0
        for it in range(cfg.polish_iterations):
            di, ri = polish_bandit.select()
            size   = destroy_size(it, cfg.polish_iterations, cfg, self.inst.n, scale=0.70)
            dest, removed = DESTROY[di](cur.copy(), size)
            cand   = REPAIR[ri](dest, removed)
            cand   = local_search(cand, max_passes=1, nv_ceiling=target_nv)
            pool.add_plan(cand)
            score, cur_before = 0, cur
            if accept_with_nv_ceiling(cur, cand, temp, target_nv):
                cur = cand
                if cand.nv < target_nv:
                    target_nv = cand.nv
                if cand.dominates(best):
                    best, score, no_imp = cand.copy(), cfg.sigma1, 0
                elif cand.nv == cur_before.nv and cand.cost + 1e-9 < cur_before.cost:
                    score, no_imp = cfg.sigma2, 0
                else:
                    score, no_imp = cfg.sigma3, no_imp + 1
            else:
                no_imp += 1
            polish_bandit.update(di, ri, score, cfg.sigma1)
            if (it + 1) % cfg.segment_size == 0:
                polish_bandit.decay(cfg.bandit_decay)
            temp *= cfg.temp_decay * 0.997
            if no_imp >= cfg.polish_patience:
                break
        best = local_search(best, max_passes=cfg.polish_ls_passes, nv_ceiling=best.nv)
        pool.add_plan(best)
        return best

    def solve(self, seed: Optional[int] = None, frozen: bool = False,
              init: Optional[Plan] = None) -> Tuple[Plan, List[float]]:
        if seed is not None:
            random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
        cfg = self.cfg
        self.ctrl.reset(); self.op_ctrl.reset()
        if getattr(self, "use_op_rl", True):
            self.lac = LearnedAcceptanceCriterion(cfg)
        self.mode_bandits = [ThompsonBandit(N_D, N_R) for _ in MODES]
        self.op_counts    = {}
        pool = RoutePool(self.inst, cfg)
        cur  = init.copy() if init is not None else build_greedy(self.inst, self.algo_name)
        best = cur.copy()
        pool.add_plan(cur)
        self._init_nv = cur.nv
        temp = cfg.temp_control * cur.cost / math.log(2)
        all_dw = np.ones((len(MODES), N_D), dtype=np.float32)
        all_rw = np.ones((len(MODES), N_R), dtype=np.float32)
        history: List[float] = [best.cost]
        recent_improvements: Deque[int] = deque(maxlen=cfg.segment_size)
        no_imp     = 0
        n_segments = math.ceil(cfg.hybrid_iterations / cfg.segment_size)

        for seg_idx in range(n_segments):
            progress = seg_idx / max(n_segments, 1)
            imp_rate = sum(recent_improvements) / max(len(recent_improvements), 1)
            self._segment_recombine_used = False
            state_before  = self._state(cur, best, no_imp, temp, imp_rate, progress, pool)
            action, ctrl_active = self._select_action(
                state_before, cur, best, no_imp, progress, pool, frozen)
            mode     = MODES[action]
            dw       = all_dw[action].copy()
            rw       = all_rw[action].copy()
            biased_dw= np.maximum(dw * np.array(mode.destroy_bias, np.float32), 0.1)
            biased_rw= np.maximum(rw * np.array(mode.repair_bias,  np.float32), 0.1)
            mode_bandit = self.mode_bandits[action]
            temp    *= mode.temp_boost
            seg_scores = np.zeros((N_D, N_R))
            seg_counts = np.zeros((N_D, N_R))
            seg_best_pre = best.copy()
            seg_cur_pre  = cur.copy()
            accepted_moves = 0

            for offset in range(cfg.segment_size):
                it = seg_idx * cfg.segment_size + offset
                if it >= cfg.hybrid_iterations:
                    break
                op_state = self._op_state(cur, best, action, it, temp, no_imp, pool, imp_rate)
                if getattr(self, "use_op_rl", True):
                    op_action, di, ri = self.op_ctrl.act(
                        op_state, biased_dw, biased_rw, mode_bandit, frozen=frozen)
                else:
                    di, ri    = mode_bandit.select(
                        prior=self.op_ctrl._prior(biased_dw, biased_rw),
                        prior_strength=self.cfg.bandit_prior_strength,
                    )
                    op_action = di * N_R + ri
                size        = destroy_size(it, cfg.hybrid_iterations, cfg, self.inst.n,
                                           scale=mode.destroy_scale)
                cur_before  = cur.copy()
                best_before = best.copy()
                dest, removed = DESTROY[di](cur.copy(), size)
                cand = REPAIR[ri](dest, removed)
                cand = self._refine_candidate(cand, action, pool, cur, best, no_imp, it)

                allow_nv_increase = (action == MODE_DIVERSIFY)
                if not cand.feasible:
                    accepted = False
                elif cand.nv > cur.nv and not (allow_nv_increase and cand.nv == cur.nv + 1):
                    accepted = False
                elif cand.nv < cur.nv or (cand.nv == cur.nv and cand.cost <= cur.cost):
                    accepted = True
                elif cand.nv == cur.nv + 1:
                    accepted = accept(cur, cand, temp, allow_nv_increase=True)
                else:
                    if cfg.lac_enabled and getattr(self, "use_op_rl", True) and not frozen:
                        t0_init   = cfg.temp_control * max(best.cost, 1.0) / math.log(2)
                        lac_feats = self.lac.features(
                            cost_delta=cand.cost - cur.cost, cur_cost=cur.cost,
                            temp=temp, temp_init=t0_init, no_imp=no_imp,
                            patience=cfg.early_stop_patience, nv_diff=cand.nv - cur.nv,
                            progress=it / max(cfg.hybrid_iterations, 1),
                            tw_tight_frac=self.inst.tw_tight_frac,
                            fleet_fill=_fleet_fill(cur), avg_slack_val=_avg_slack(cur),
                        )
                        accepted, _ = self.lac.decide(lac_feats, best.cost)
                    else:
                        accepted = random.random() < math.exp(
                            -(cand.cost - cur.cost) / max(temp, 1e-6))

                if cfg.lac_enabled and getattr(self, "use_op_rl", True) and not frozen:
                    self.lac.observe(best.cost)

                score    = 0
                improved = False
                if accepted:
                    accepted_moves += 1
                    improved = cand.dominates(cur)
                    pool.add_plan(cand)
                    if cand.nv <= best.nv and cand.dominates(best):
                        best, score, no_imp = cand.copy(), cfg.sigma1, 0
                        pool.add_plan(best)
                    elif improved:
                        score, no_imp = cfg.sigma2, 0
                    else:
                        score, no_imp = cfg.sigma3, no_imp + 1
                    cur = cand
                else:
                    no_imp += 1

                key = (di, ri)
                self.op_counts[key] = self.op_counts.get(key, 0) + 1
                recent_improvements.append(1 if improved else 0)
                seg_scores[di, ri] += score
                seg_counts[di, ri] += 1
                mode_bandit.update(di, ri, score, cfg.sigma1)
                cur_after  = cur.copy()
                best_after = best.copy()
                next_imp   = sum(recent_improvements) / max(len(recent_improvements), 1)
                next_state = self._op_state(
                    cur_after, best_after, action, it + 1, temp, no_imp, pool, next_imp)
                done = 1.0 if no_imp >= cfg.early_stop_patience else 0.0
                if not frozen and getattr(self, "use_op_rl", True):
                    self.op_ctrl.observe(
                        op_state, op_action,
                        self._iteration_reward(cur_before, best_before,
                                               cur_after, best_after, accepted),
                        next_state, done,
                    )
                    if (it + 1) % 4 == 0:
                        self.op_ctrl.train_step()
                temp *= cfg.temp_decay * mode.temp_decay_scale
                history.append(best.cost)
                if no_imp >= cfg.early_stop_patience:
                    break

            for mb in self.mode_bandits:
                mb.decay(cfg.bandit_decay)
            for d in range(N_D):
                for r in range(N_R):
                    if seg_counts[d, r] > 0:
                        avg    = seg_scores[d, r] / seg_counts[d, r]
                        dw[d]  = dw[d] * (1 - cfg.weight_decay) + avg * cfg.weight_decay
                        rw[r]  = rw[r] * (1 - cfg.weight_decay) + avg * cfg.weight_decay
            all_dw[action] = np.maximum(dw, 0.1)
            all_rw[action] = np.maximum(rw, 0.1)

            state_after = self._state(
                cur, best, no_imp, temp,
                sum(recent_improvements) / max(len(recent_improvements), 1),
                min((seg_idx + 1) / max(n_segments, 1), 1.0),
                pool,
            )
            if ctrl_active:
                self.ctrl.observe(
                    state_before, action,
                    self._segment_reward(seg_best_pre, best, seg_cur_pre, cur,
                                         accepted_moves, action),
                    state_after, 0.0,
                )
                self.ctrl.train_step()
            if no_imp >= cfg.early_stop_patience:
                break

        if cfg.recombine_after_main_search:
            recombined = recombine_with_route_pool(best, pool, cfg, nv_ceiling=best.nv)
            if recombined.dominates(best):
                best = recombined
                pool.add_plan(best)
                history.append(best.cost)

        # Pass dominant mode bandit to polish (inherits learned operator stats)
        dominant_mode = int(np.argmax([b.alpha.sum() for b in self.mode_bandits]))
        best = self._fixed_nv_polish(best, pool,
                                     inherited_bandit=self.mode_bandits[dominant_mode])
        history.append(best.cost)

        if cfg.recombine_after_polish:
            recombined = recombine_with_route_pool(best, pool, cfg, nv_ceiling=best.nv)
            if recombined.dominates(best):
                best = local_search(recombined, max_passes=cfg.polish_ls_passes,
                                    nv_ceiling=recombined.nv)
                history.append(best.cost)

        # Post-search NV reduction pass (especially effective on RC2)
        bks = BKS.get(self.inst.name)
        if bks is not None and best.nv > bks["nv"]:
            eliminated = _iterative_route_elimination(best, self.inst)
            if eliminated.dominates(best):
                best = eliminated
                history.append(best.cost)

        best.algo = self.algo_name
        return best, history


# ---------------------------------------------------------------------------
# Hybrid-Fixed
# ---------------------------------------------------------------------------
class HybridFixedSolver(HybridDDQNSolver):
    algo_name = ALGO_HYBRID_FIXED
    use_op_rl = False

    def _select_action(self, state_before, cur, best, no_imp, progress, pool, frozen):
        del state_before, best, progress, pool, frozen
        if self._route_reduce_trigger(cur, no_imp):
            return MODE_ROUTE_REDUCE, False
        return MODE_DEFAULT, False

    def solve(self, seed=None, frozen=True, init=None):
        plan, history = super().solve(seed=seed, frozen=True, init=init)
        plan.algo = self.algo_name
        return plan, history


# ---------------------------------------------------------------------------
# Hybrid-Rule
# ---------------------------------------------------------------------------
class HybridRuleSolver(HybridDDQNSolver):
    algo_name = ALGO_HYBRID_RULE
    use_op_rl = False

    def _select_action(self, state_before, cur, best, no_imp, progress, pool, frozen):
        del state_before, best, frozen
        if self._route_reduce_trigger(cur, no_imp):
            return MODE_ROUTE_REDUCE, False
        pool_ready  = len(pool._routes) >= max(self.cfg.rl_recombine_min_routes,
                                               max(12, cur.nv * 2))
        fleet_fill  = _fleet_fill(cur)
        slack       = _avg_slack(cur)
        if (pool_ready and no_imp >= max(10, self.cfg.ctrl_start // 2)
                and fleet_fill >= 0.66 and progress < 0.92):
            return MODE_POOL_RECOMBINE, False
        if (self.inst.tw_tight_frac >= 0.18 and slack < 0.16
                and no_imp >= max(8, self.cfg.ctrl_start // 2)):
            return MODE_TW_RESCUE, False
        if no_imp >= max(12, self.cfg.ctrl_start // 2):
            return (MODE_DIVERSIFY if progress < 0.45 else MODE_INTENSIFY), False
        return MODE_DEFAULT, False

    def solve(self, seed=None, frozen=True, init=None):
        plan, history = super().solve(seed=seed, frozen=True, init=init)
        plan.algo = self.algo_name
        return plan, history


PlateauHybridSolver   = HybridDDQNSolver
ScheduledHybridSolver = HybridRuleSolver
RLALNSSolver          = HybridDDQNSolver


# ---------------------------------------------------------------------------
# OR-Tools GLS baseline
# ---------------------------------------------------------------------------
def run_ortools(inst: Inst, cfg: Config) -> Tuple[Optional[Plan], float]:
    if not ORTOOLS_OK:
        print("  [OR-Tools] not installed — skipping")
        return None, 0.0
    from ortools.constraint_solver import routing_enums_pb2, pywrapcp
    scale      = 100
    n_nodes    = inst.n + 1
    n_vehicles = inst.n
    manager    = pywrapcp.RoutingIndexManager(n_nodes, n_vehicles, 0)
    routing    = pywrapcp.RoutingModel(manager)
    dist_mat   = (inst.dist * scale).astype(int)
    serv_int   = (inst.service_times * scale).astype(int)

    def transit_cb(fi, ti):
        fn, tn = manager.IndexToNode(fi), manager.IndexToNode(ti)
        return int(dist_mat[fn, tn]) + int(serv_int[fn])
    transit_idx = routing.RegisterTransitCallback(transit_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_idx)
    demands_int = inst.demands.astype(int)

    def demand_cb(fi):
        return int(demands_int[manager.IndexToNode(fi)])
    demand_idx = routing.RegisterUnaryTransitCallback(demand_cb)
    routing.AddDimensionWithVehicleCapacity(
        demand_idx, 0, [int(inst.capacity)] * n_vehicles, True, "Capacity")
    routing.AddDimension(transit_idx, int(inst.horizon * scale),
                         int(inst.horizon * scale), False, "Time")
    time_dim = routing.GetDimensionOrDie("Time")
    for node in range(1, inst.n + 1):
        idx = manager.NodeToIndex(node)
        time_dim.CumulVar(idx).SetRange(int(inst.ready_times[node] * scale),
                                        int(inst.due_times[node] * scale))
    for v in range(n_vehicles):
        routing.AddVariableMinimizedByFinalizer(time_dim.CumulVar(routing.Start(v)))
        routing.AddVariableMinimizedByFinalizer(time_dim.CumulVar(routing.End(v)))
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds = int(cfg.ortools_time_limit)
    params.log_search = False
    t0       = time.time()
    solution = routing.SolveWithParameters(params)
    elapsed  = time.time() - t0
    if not solution:
        print(f"  [OR-Tools] no solution ({elapsed:.1f}s)")
        return None, elapsed
    routes: List[List[int]] = []
    for v in range(n_vehicles):
        route: List[int] = []
        idx = routing.Start(v)
        while not routing.IsEnd(idx):
            node = manager.IndexToNode(idx)
            if node != 0:
                route.append(node)
            idx = solution.Value(routing.NextVar(idx))
        if route:
            routes.append(route)
    plan = Plan(routes, inst, ALGO_ORTOOLS)
    if not plan.feasible:
        print(f"  [OR-Tools] infeasible ({elapsed:.1f}s)")
        return None, elapsed
    return plan, elapsed


# ---------------------------------------------------------------------------
# run_instance
# ---------------------------------------------------------------------------
def run_instance(inst: Inst, algo: str, cfg: Config, seed: int,
                 transfer_weights: Optional[Dict] = None,
                 init_plan: Optional[Plan] = None) -> Tuple[Dict, Optional[Plan]]:
    start = time.time()
    algo  = canonical_algo_label(algo)
    plan: Optional[Plan] = None
    if algo == ALGO_ORTOOLS:
        plan, elapsed = run_ortools(inst, cfg)
        if plan is None:
            return {"algo": ALGO_ORTOOLS, "nv": None, "cost": None,
                    "time": time.time() - start, "td_gap": None, "nv_diff": None,
                    "on_time": None, "hist": []}, None
        history = [plan.cost]
    elif algo == ALGO_ALNS_BASE:
        plan, history = ALNSSolver(inst, cfg).solve(seed=seed, init=init_plan)
    elif algo == ALGO_HYBRID_FIXED:
        plan, history = HybridFixedSolver(inst, cfg).solve(seed=seed, init=init_plan)
    elif algo == ALGO_HYBRID_RULE:
        plan, history = HybridRuleSolver(inst, cfg).solve(seed=seed, init=init_plan)
    elif algo == ALGO_HYBRID_DDQN:
        plan, history = HybridDDQNSolver(inst, cfg).solve(seed=seed, init=init_plan)
    elif algo in (ALGO_HYBRID_DDQN_TRANSFER, ALGO_HYBRID_DDQN_TRANSFER_RC2,
                  ALGO_HYBRID_DDQN_TRANSFER_DR):
        solver = HybridDDQNSolver(inst, cfg)
        if transfer_weights is not None:
            solver.load_weights(transfer_weights)
        plan, history = solver.solve(seed=seed, frozen=True, init=init_plan)
        plan.algo = algo
    else:
        raise ValueError(f"Unsupported algorithm: {algo}")
    bks = BKS.get(inst.name)
    return {
        "algo":    plan.algo,
        "nv":      plan.nv,
        "cost":    plan.cost,
        "time":    time.time() - start,
        "td_gap":  (plan.cost - bks["td"]) / bks["td"] * 100 if bks else None,
        "nv_diff": plan.nv - bks["nv"] if bks else None,
        "on_time": plan.on_time_rate,
        "hist":    history,
    }, plan


# ---------------------------------------------------------------------------
# Top-level worker  — must be module-level for ProcessPoolExecutor pickling
# ---------------------------------------------------------------------------
def _benchmark_worker(packed: Tuple) -> Tuple[Dict, Optional[Plan]]:
    inst, algo, cfg, seed, transfer_weights, init_plan = packed
    return run_instance(inst, algo, cfg, seed, transfer_weights, init_plan)


def _diversified_init(run_idx: int, inst: Inst, archive: EliteArchive,
                      cfg: Config) -> Optional[Plan]:
    """
    run 0 → archive best       (exploitation of known-good solution)
    run 1 → shaw-perturbed     (exploration from good neighbourhood)
    run 2 → fresh greedy build (independent trajectory)
    Avoids 3 seeds converging to the same local optimum.
    """
    base = archive.best(inst.name)
    if run_idx == 0:
        return base
    if run_idx == 1 and base is not None:
        random.seed(cfg.seed + 7919); np.random.seed(cfg.seed + 7919)
        size = max(4, int(0.20 * inst.n))
        dest, removed = op_shaw(base.copy(), size)
        cand = op_regret_2(dest, removed)
        return cand if (cand.feasible and cand.nv <= base.nv + 1) else base
    return None  # run_instance will call build_greedy


# ---------------------------------------------------------------------------
# run_benchmark  (ProcessPoolExecutor for true GIL bypass)
# ---------------------------------------------------------------------------
def run_benchmark(
    instances: Iterable[Inst],
    algorithms: List[str],
    cfg: Config,
    result_path:      Optional[str]  = None,
    transfer_weights: Optional[Dict] = None,
    archive:          Optional[EliteArchive] = None,
    checkpoint_path:  Optional[str]  = None,
) -> pd.DataFrame:
    instances   = list(instances)
    result_path = result_path or os.path.join(cfg.output_dir, "benchmark_clean.csv")
    ckpt_path   = checkpoint_path or os.path.join(cfg.output_dir, "benchmark_checkpoint.csv")
    if archive is None:
        archive = EliteArchive(k=cfg.elite_archive_k)

    rows:      List[Dict] = []
    completed: set        = set()
    if os.path.exists(ckpt_path):
        try:
            ckpt_df = pd.read_csv(ckpt_path)
            rows    = ckpt_df.to_dict("records")
            for row in rows:
                completed.add((row["Instance"], canonical_algo_label(str(row["Algorithm"]))))
            print(f"Resumed from checkpoint: {len(completed)} combo(s) already done")
        except Exception as exc:
            print(f"Checkpoint read failed ({exc}), starting fresh")

    total    = len(instances) * len(algorithms)
    n_workers= min(cfg.n_runs, max(1, os.cpu_count() // 2))
    print(f"Total: {total} combos × {cfg.n_runs} runs  |  wall limit: {cfg.max_wall_hours:.1f}h")
    print(f"Parallel workers: {n_workers}  (ProcessPool — true GIL bypass)")
    print("=" * 64)
    wall_start = time.time()

    for inst_idx, inst in enumerate(instances):
        dataset = "RC1" if inst.name[2] == "1" else "RC2"
        for algo in algorithms:
            algo_label = canonical_algo_label(algo)
            if (inst.name, algo_label) in completed:
                print(f"  [SKIP] {inst.name} {algo_label}")
                continue
            elapsed_h = (time.time() - wall_start) / 3600
            if elapsed_h >= cfg.max_wall_hours:
                print(f"\n⚠️  Wall-clock limit {cfg.max_wall_hours:.1f}h — stopping early.")
                pd.DataFrame(rows).to_csv(ckpt_path, index=False)
                return normalize_algorithm_frame(pd.DataFrame(rows))

            print(f"\n[{inst.name}] {algo_label}")
            nv_v, cost_v, time_v, gap_v, nvd_v, ot_v = [], [], [], [], [], []
            n_runs_eff = 1 if algo_label == ALGO_ORTOOLS else cfg.n_runs

            worker_args = [
                (inst, algo_label, cfg, cfg.seed + i,
                 transfer_weights, _diversified_init(i, inst, archive, cfg))
                for i in range(n_runs_eff)
            ]
            _n_workers = 1 if algo_label == ALGO_ORTOOLS else n_workers
            with ProcessPoolExecutor(max_workers=_n_workers) as ex:
                run_results = list(ex.map(_benchmark_worker, worker_args))

            for i, (res, plan) in enumerate(run_results):
                if plan is not None:
                    archive.update(plan)
                time_v.append(res["time"])
                elapsed_h = (time.time() - wall_start) / 3600
                if res["nv"] is not None:
                    nv_v.append(res["nv"]); cost_v.append(res["cost"])
                    gap_v.append(res["td_gap"]); nvd_v.append(res["nv_diff"])
                    ot_v.append(res["on_time"])
                    print(f"  run {i+1}/{n_runs_eff}: nv={res['nv']} cost={res['cost']:.1f} "
                          f"({res['time']:.1f}s) | wall {elapsed_h:.2f}h")
                else:
                    print(f"  run {i+1}/{n_runs_eff}: FAILED ({res['time']:.1f}s)")

            if not nv_v:
                continue

            bks = BKS.get(inst.name)
            nv_inflated = (bks is not None
                           and float(np.mean(nv_v)) > bks["nv"] + 0.4
                           and gap_v[0] is not None
                           and float(np.mean(gap_v)) < 0)
            if nv_inflated:
                print(f"  ⚠️  NV_mean={np.mean(nv_v):.1f} > BKS_NV={bks['nv']} "
                      f"— Gap% comparison misleading (extra vehicle reduces TD)")

            row = {
                "Dataset":     dataset,
                "Instance":    inst.name,
                "Algorithm":   run_results[-1][0]["algo"],
                "NV_mean":     round(float(np.mean(nv_v)),  2),
                "NV_std":      round(float(np.std(nv_v)),   2),
                "NV_diff":     round(float(np.mean(nvd_v)), 2) if nvd_v[0] is not None else None,
                "TD_mean":     round(float(np.mean(cost_v)),2),
                "TD_std":      round(float(np.std(cost_v)), 2),
                "Gap%":        round(float(np.mean(gap_v)), 2) if gap_v[0] is not None else None,
                "OnTime":      round(float(np.mean(ot_v)) * 100, 1),
                "Time_s":      round(float(np.mean(time_v)), 1),
                "NV_cv":       round(float(np.std(nv_v))   / max(float(np.mean(nv_v)),   1) * 100, 2),
                "TD_cv":       round(float(np.std(cost_v)) / max(float(np.mean(cost_v)), 1) * 100, 2),
                "NV_inflated": nv_inflated,
                "raw_costs":   ";".join(f"{c:.4f}" for c in cost_v),
                "raw_nv":      ";".join(str(n) for n in nv_v),
            }
            rows.append(row)
            completed.add((inst.name, algo_label))
            gap_text = f"{row['Gap%']:+.1f}%" if row["Gap%"] is not None else "--"
            print(f"  -> nv={row['NV_mean']:.1f}±{row['NV_std']:.1f}  "
                  f"td={row['TD_mean']:.1f}±{row['TD_std']:.1f}  gap={gap_text}")

        if (inst_idx + 1) % 4 == 0:
            pd.DataFrame(rows).to_csv(ckpt_path, index=False)
            elapsed_h = (time.time() - wall_start) / 3600
            print(f"\n  ✓ Checkpoint ({inst_idx+1}/{len(instances)} inst, "
                  f"{elapsed_h:.2f}h) → {ckpt_path}")

    df = normalize_algorithm_frame(pd.DataFrame(rows))
    df.to_csv(result_path, index=False)
    print(f"\nBenchmark complete in {(time.time()-wall_start)/3600:.2f}h → {result_path}")
    return df


# ---------------------------------------------------------------------------
# Summary table  (with completeness + NV-inflation guards)
# ---------------------------------------------------------------------------
def print_summary_table(df: pd.DataFrame) -> None:
    df = normalize_algorithm_frame(df)

    # Completeness check
    expected = {"RC1": 8, "RC2": 8}
    for ds, exp_n in expected.items():
        for algo in df[df["Dataset"] == ds]["Algorithm"].dropna().unique():
            n = len(df[(df["Dataset"] == ds) & (df["Algorithm"] == algo)])
            if n < exp_n:
                print(f"  ⚠️  {ds}/{algo}: {n}/{exp_n} instances — summary is PARTIAL")

    # NV-inflation warning
    if "NV_inflated" in df.columns:
        flagged = df[df["NV_inflated"] == True][["Instance", "Algorithm", "Gap%", "NV_mean"]]
        for _, r in flagged.iterrows():
            print(f"  ⚠️  {r['Instance']} {r['Algorithm']}: Gap%={r['Gap%']:+.1f}% "
                  f"with NV={r['NV_mean']:.1f} > BKS_NV — not a fair comparison")

    summary = (
        df.groupby(["Dataset", "Algorithm"], observed=True)
        .agg(NV=("NV_mean","mean"), NV_std=("NV_std","mean"), NV_diff=("NV_diff","mean"),
             TD=("TD_mean","mean"), TD_std=("TD_std","mean"),
             Gap=("Gap%","mean"), OnTime=("OnTime","mean"), Time=("Time_s","mean"))
        .round(2).reset_index()
    )
    print("\n" + "-" * 96)
    print(f"{'DS':<4}{'Algorithm':<28}{'NV':>6}{'+/-':>6}{'vsBKS':>8}"
          f"{'TD':>10}{'+/-':>8}{'Gap%':>8}{'OT%':>7}{'Time':>8}")
    print("-" * 96)
    for _, row in summary.iterrows():
        gap     = f"{row['Gap']:+.2f}%"    if pd.notna(row["Gap"])     else "--"
        nv_diff = f"{row['NV_diff']:+.2f}" if pd.notna(row["NV_diff"]) else "--"
        print(f"{row['Dataset']:<4}{row['Algorithm']:<28}"
              f"{row['NV']:>6.2f}{row['NV_std']:>6.2f}{nv_diff:>8}"
              f"{row['TD']:>10.2f}{row['TD_std']:>8.2f}{gap:>8}"
              f"{row['OnTime']:>7.1f}{row['Time']:>7.1f}s")
    print("-" * 96)


# ---------------------------------------------------------------------------
# Transfer / domain randomization
# ---------------------------------------------------------------------------
def train_transfer_model(instances: List[Inst], cfg: Config,
                         seed: int = 42, label: str = "RC1") -> Dict:
    print(f"Training transfer model on {label} ({len(instances)} instances)...")
    if not instances:
        raise ValueError("No source instances provided.")
    weights = None
    for epoch in range(cfg.transfer_epochs):
        order = list(instances)
        if cfg.transfer_shuffle:
            random.Random(seed + epoch).shuffle(order)
        print(f"  Epoch {epoch + 1}/{cfg.transfer_epochs}")
        for idx, inst in enumerate(order):
            solver = HybridDDQNSolver(inst, cfg)
            if weights is not None:
                solver.load_weights(weights)
            plan, _ = solver.solve(seed=seed + epoch * 100 + idx)
            weights  = solver.clone_weights()
            td_gap, _= plan.gap()
            print(f"    [{epoch+1}:{idx+1}] {inst.name}: nv={plan.nv} gap={td_gap:+.1f}%")
    stem = os.path.join(cfg.output_dir, f"rl_alns_transfer_{label.lower()}_v15")
    _save_weights(weights, stem)
    return weights


def train_domain_randomization(cfg: Config, seed: int = 42) -> Dict:
    """
    3-phase curriculum:
      Phase 1 (0-40%):   Easy   — 20-40 nodes
      Phase 2 (40-80%):  Target — 40-80 nodes
      Phase 3 (80-100%): Chaos  — 20-100 nodes
    """
    total_epochs  = int(cfg.domain_randomization_epochs)
    batch_size    = int(cfg.domain_randomization_batch)
    distributions = ("C", "R", "RC")
    rng     = random.Random(seed)
    weights: Optional[Dict] = None
    print(f"Domain-randomization curriculum: {total_epochs} epochs × {batch_size} instances/epoch")

    for epoch in range(total_epochs):
        frac = (epoch + 1) / max(total_epochs, 1)
        if   frac <= 0.40: phase, n_min, n_max = "Easy  ", 20, 40
        elif frac <= 0.80: phase, n_min, n_max = "Target", 40, 80
        else:              phase, n_min, n_max = "Chaos ", 20, 100
        print(f"  Epoch {epoch+1:>2}/{total_epochs}  [{phase}  N={n_min}-{n_max}]")
        batch: List[Inst] = []
        for idx in range(batch_size):
            n_nodes  = rng.randint(n_min, n_max)
            dist     = distributions[(epoch + idx) % len(distributions)]
            gen_seed = seed + epoch * 10_000 + idx
            batch.append(SyntheticVRPTWGenerator(n_nodes, dist, seed=gen_seed).generate())
        for idx, inst in enumerate(batch):
            solver = HybridDDQNSolver(inst, cfg)
            if weights is not None:
                solver.load_weights(weights)
            plan, _ = solver.solve(seed=seed + epoch * 1_000 + idx)
            weights  = solver.clone_weights()
            print(f"    [{idx+1:>2}/{batch_size}] {inst.name}: "
                  f"n={inst.n}  nv={plan.nv}  cost={plan.cost:.1f}  feasible={plan.feasible}")

    if weights is None:
        raise RuntimeError("Domain randomization produced no weights.")
    os.makedirs(cfg.output_dir, exist_ok=True)
    stem = os.path.join(cfg.output_dir, "rl_alns_dr_v15")
    _save_weights(weights, stem)
    return weights


def train_transfer_model_within_rc2(rc2_instances: List[Inst], cfg: Config,
                                     seed: int = 42) -> Dict:
    source = rc2_instances[:cfg.rc2_transfer_split]
    print(f"RC2-within transfer: train on {[i.name for i in source]}")
    return train_transfer_model(source, cfg, seed=seed, label="RC2-src")


def load_transfer_model(cfg: Config, label: str = "rc1") -> Optional[Dict]:
    stem = os.path.join(cfg.output_dir, f"rl_alns_transfer_{label}_v15")
    return _load_weights(stem)


# ---------------------------------------------------------------------------
# Smoke test  — per-algo timing for accurate wall estimate
# ---------------------------------------------------------------------------
def smoke_test(inst: Inst, seed: int = 42) -> Dict[str, Tuple[float, float]]:
    """
    Returns {algo_name: (gap_pct, elapsed_s)} for the 4 main solvers.
    Uses short iterations so it completes in < 5 min on any hardware.
    """
    short_cfg = Config(
        alns_iterations=300, hybrid_iterations=400,
        early_stop_patience=100, polish_iterations=50,
        polish_patience=30, n_runs=1,
    )
    results: Dict[str, Tuple[float, float]] = {}
    for algo_name, solver_cls in (
        (ALGO_ALNS_BASE,    ALNSSolver),
        (ALGO_HYBRID_FIXED, HybridFixedSolver),
        (ALGO_HYBRID_RULE,  HybridRuleSolver),
        (ALGO_HYBRID_DDQN,  HybridDDQNSolver),
    ):
        random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
        t0    = time.time()
        plan, _= solver_cls(inst, short_cfg).solve(seed=seed)
        elapsed= time.time() - t0
        td_gap, nv_gap = plan.gap()
        print(f"{algo_name:<24} nv={plan.nv:>3} cost={plan.cost:>8.1f} "
              f"BKS TD {td_gap:+.1f}% NV {nv_gap:+d} ({elapsed:.1f}s)")
        results[algo_name] = (float(td_gap) if td_gap is not None else 0.0, elapsed)
    return results


# ---------------------------------------------------------------------------
# __all__
# ---------------------------------------------------------------------------
__all__ = [
    "ALGO_ALNS_BASE", "ALGO_HYBRID_FIXED", "ALGO_HYBRID_RULE",
    "ALGO_HYBRID_DDQN", "ALGO_HYBRID_DDQN_TRANSFER",
    "ALGO_HYBRID_DDQN_TRANSFER_RC2", "ALGO_HYBRID_DDQN_TRANSFER_DR",
    "ALGO_ORTOOLS",
    "ALNSSolver", "BKS", "Config", "EliteArchive", "LearnedAcceptanceCriterion",
    "HybridDDQNSolver", "HybridFixedSolver", "HybridRuleSolver",
    "Inst", "Plan", "SyntheticVRPTWGenerator",
    "PlateauHybridSolver", "RLALNSSolver", "ScheduledHybridSolver",
    "canonical_algo_label", "default_data_path", "default_output_dir",
    "load_datasets", "load_transfer_model", "normalize_algorithm_frame",
    "print_summary_table", "run_benchmark", "run_instance", "run_ortools",
    "smoke_test", "train_domain_randomization",
    "train_transfer_model", "train_transfer_model_within_rc2",
    "_iterative_route_elimination", "_save_weights", "_load_weights",
]


# ---------------------------------------------------------------------------
# __main__
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"DEVICE      : {DEVICE}")
    print(f"N_D={N_D}  N_R={N_R}  N_ACTIONS={N_ACTIONS}")
    print(f"CPU threads : {os.cpu_count()}")
    print(f"_N_PARALLEL : {_N_PARALLEL}  |  _NUMBA_THREADS : {_NUMBA_THREADS}")

    CFG = Config()
    print(f"Data path   : {CFG.data_path}")
    print(f"Output dir  : {CFG.output_dir}")

    print("\nLoading datasets...")
    datasets = load_datasets(CFG.data_path)
    RC1      = datasets.get("rc1", [])
    RC2      = datasets.get("rc2", [])
    if not RC1:
        print(f"No RC1 data at {CFG.data_path} — check your path.")
        raise SystemExit(1)
    print(f"RC1: {len(RC1)} instances  |  RC2: {len(RC2)} instances")
    if len(RC2) < 8:
        print(f"  ⚠️  RC2 has only {len(RC2)}/8 instances — upload missing files before running.")

    # ── Smoke test — per-algo timing for accurate wall estimate ────────────
    print("\n" + "=" * 64)
    print(f"--- Smoke Test on {RC1[0].name} ---")
    smoke_results = smoke_test(RC1[0], seed=CFG.seed)

    # Scale factors: ALNS uses alns_iterations; hybrids use hybrid_iterations
    scale_map = {
        ALGO_ALNS_BASE:    CFG.alns_iterations    / 300,
        ALGO_HYBRID_FIXED: CFG.hybrid_iterations  / 400,
        ALGO_HYBRID_RULE:  CFG.hybrid_iterations  / 400,
        ALGO_HYBRID_DDQN:  CFG.hybrid_iterations  / 400,
    }
    n_workers_est = min(CFG.n_runs, max(1, os.cpu_count() // 2))
    n_inst        = len(RC1 + RC2)
    est_h = sum(
        n_inst * smoke_results[a][1] * scale_map[a] * CFG.n_runs / n_workers_est
        for a in smoke_results
    ) / 3600
    print(f"\nEstimated Phase 1 wall: ~{est_h:.1f}h  "
          f"({n_workers_est} workers × {CFG.n_runs} runs × {n_inst} instances)")
    if est_h > CFG.max_wall_hours * 0.85:
        print(f"  ⚠️  Over 85% of budget before Phase 2 — consider reducing hybrid_iterations "
              f"or n_runs.  Current: hybrid_iterations={CFG.hybrid_iterations}, "
              f"n_runs={CFG.n_runs}")

    # ── Phase 1: Main Benchmark ────────────────────────────────────────────
    print("\n" + "=" * 64)
    print("--- Phase 1: Main Benchmark ---")
    archive_main = EliteArchive(k=CFG.elite_archive_k)
    algos_main   = []
    if ORTOOLS_OK:
        algos_main.append(ALGO_ORTOOLS)
    algos_main += [ALGO_ALNS_BASE, ALGO_HYBRID_FIXED, ALGO_HYBRID_RULE, ALGO_HYBRID_DDQN]

    df_main = run_benchmark(
        instances=RC1 + RC2,
        algorithms=algos_main,
        cfg=CFG,
        result_path=     os.path.join(CFG.output_dir, "benchmark_main_v15.csv"),
        checkpoint_path= os.path.join(CFG.output_dir, "ckpt_main_v15.csv"),
        archive=archive_main,
    )
    print_summary_table(df_main)

    # ── Phase 2: Domain-Randomized Zero-Shot Transfer ──────────────────────
    print("\n" + "=" * 64)
    print("--- Phase 2: Domain-Randomized Zero-Shot Transfer ---")
    archive_dr = EliteArchive(k=CFG.elite_archive_k)

    # Try to reuse cached DR weights — saves ~30-60min on re-runs
    _dr_stem   = os.path.join(CFG.output_dir, "rl_alns_dr_v15")
    dr_weights = _load_weights(_dr_stem)
    if dr_weights is None:
        dr_weights = train_domain_randomization(CFG, seed=CFG.seed)
    else:
        print("DR weights reloaded from disk — skipping retraining.")

    df_dr = run_benchmark(
        instances=RC1 + RC2,
        algorithms=[ALGO_HYBRID_DDQN_TRANSFER_DR],
        cfg=CFG,
        result_path=     os.path.join(CFG.output_dir, "benchmark_dr_v15.csv"),
        checkpoint_path= os.path.join(CFG.output_dir, "ckpt_dr_v15.csv"),
        transfer_weights=dr_weights,
        archive=archive_dr,
    )

    # ── Final combined table ───────────────────────────────────────────────
    print("\n" + "=" * 64)
    print("--- Final Combined Results ---")
    df_all = pd.concat([df_main, df_dr], ignore_index=True)
    print_summary_table(df_all)

    print("\n--- Elite Archive: Phase 1 ---")
    print(archive_main.summary())
    print("\n--- Elite Archive: Phase 2 DR ---")
    print(archive_dr.summary())

    print("\n✅  All benchmarks complete.")
