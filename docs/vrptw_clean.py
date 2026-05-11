from __future__ import annotations

import glob
import math
import os
import random
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Deque, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from numba import njit

try:
    from scipy.optimize import Bounds, LinearConstraint, milp
except Exception:  # pragma: no cover - optional dependency
    Bounds = None
    LinearConstraint = None
    milp = None


DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


BKS: Dict[str, Dict[str, float]] = {
    "RC101": {"nv": 14, "td": 1696.94},
    "RC102": {"nv": 12, "td": 1554.75},
    "RC103": {"nv": 11, "td": 1261.67},
    "RC104": {"nv": 10, "td": 1135.48},
    "RC105": {"nv": 13, "td": 1629.44},
    "RC106": {"nv": 11, "td": 1424.73},
    "RC107": {"nv": 11, "td": 1230.48},
    "RC108": {"nv": 10, "td": 1139.82},
    "RC201": {"nv": 4, "td": 1406.94},
    "RC202": {"nv": 3, "td": 1365.64},
    "RC203": {"nv": 3, "td": 1049.62},
    "RC204": {"nv": 3, "td": 798.46},
    "RC205": {"nv": 4, "td": 1297.65},
    "RC206": {"nv": 3, "td": 1146.32},
    "RC207": {"nv": 3, "td": 1061.14},
    "RC208": {"nv": 3, "td": 828.14},
}


def default_data_path() -> str:
    env = os.environ.get("VRPTW_DATA_DIR")
    if env:
        return env
    if os.path.exists("/kaggle/working"):
        return "/kaggle/input/datasets/senju14/vrptw-benchmark-datasets/data/Solomon"
    if os.path.exists("/content"):
        return "/content/vrptw-benchmark/data/Solomon"
    return str(Path(__file__).resolve().parent / "data" / "solomon")


def default_output_dir() -> str:
    env = os.environ.get("VRPTW_OUTPUT_DIR")
    if env:
        return env
    if os.path.exists("/kaggle/working"):
        return "/kaggle/working"
    if os.path.exists("/content"):
        return "/content"
    return str(Path(__file__).resolve().parent / "logs" / "local")


@dataclass
class Config:
    data_path: str = default_data_path()
    output_dir: str = default_output_dir()

    alns_iterations: int = 2000
    hybrid_iterations: int = 2000
    destroy_ratio_min: float = 0.10
    destroy_ratio_max: float = 0.40
    temp_control: float = 0.05
    temp_decay: float = 0.99975
    sigma1: int = 33
    sigma2: int = 9
    sigma3: int = 3
    weight_decay: float = 0.10
    segment_size: int = 50
    early_stop_patience: int = 400
    n_runs: int = 5
    seed: int = 42

    ctrl_state_dim: int = 10
    ctrl_hidden: int = 96
    ctrl_lr: float = 3e-4
    ctrl_gamma: float = 0.95
    ctrl_buffer: int = 4096
    ctrl_batch: int = 64
    ctrl_target_freq: int = 20
    ctrl_eps_start: float = 0.35
    ctrl_eps_end: float = 0.05
    ctrl_eps_decay: float = 0.992
    plateau_start: int = 60
    post_improve_intensify_segments: int = 2
    nv_increase_penalty: float = 20.0
    route_pool_limit: int = 480
    route_pool_max_per_customer: int = 18
    sp_time_limit: float = 4.0
    sp_vehicle_penalty_scale: float = 100.0
    polish_iterations: int = 450
    polish_patience: int = 120
    polish_ls_passes: int = 2
    recombine_after_main_search: bool = True
    recombine_after_polish: bool = True


@dataclass(frozen=True)
class ModeSpec:
    name: str
    destroy_scale: float
    temp_boost: float
    temp_decay_scale: float
    destroy_bias: Tuple[float, ...]
    repair_bias: Tuple[float, ...]


MODES: Tuple[ModeSpec, ...] = (
    ModeSpec(
        name="default",
        destroy_scale=1.0,
        temp_boost=1.0,
        temp_decay_scale=1.0,
        destroy_bias=(1.0, 1.0, 1.0, 1.0, 1.0, 0.8),
        repair_bias=(1.0, 1.0, 1.0, 1.0),
    ),
    ModeSpec(
        name="intensify",
        destroy_scale=0.70,
        temp_boost=0.98,
        temp_decay_scale=0.995,
        destroy_bias=(0.8, 1.3, 1.2, 0.5, 1.0, 0.7),
        repair_bias=(1.3, 1.2, 0.8, 1.0),
    ),
    ModeSpec(
        name="diversify",
        destroy_scale=1.20,
        temp_boost=1.08,
        temp_decay_scale=1.002,
        destroy_bias=(1.3, 0.9, 1.3, 1.1, 1.0, 0.7),
        repair_bias=(0.9, 1.0, 1.3, 1.0),
    ),
    ModeSpec(
        name="tw_rescue",
        destroy_scale=1.10,
        temp_boost=1.05,
        temp_decay_scale=1.0,
        destroy_bias=(0.7, 0.9, 1.1, 0.8, 1.8, 0.4),
        repair_bias=(0.8, 1.0, 1.2, 1.8),
    ),
    ModeSpec(
        name="route_reduce",
        destroy_scale=0.95,
        temp_boost=1.02,
        temp_decay_scale=0.998,
        destroy_bias=(0.6, 1.0, 0.9, 1.7, 0.6, 2.2),
        repair_bias=(0.8, 1.2, 1.5, 1.0),
    ),
)

MODE_DEFAULT = 0
MODE_INTENSIFY = 1
MODE_DIVERSIFY = 2
MODE_TW_RESCUE = 3
MODE_ROUTE_REDUCE = 4


class ReplayBuffer:
    def __init__(self, capacity: int):
        self.buf: Deque[Tuple[np.ndarray, int, float, np.ndarray, float]] = deque(
            maxlen=capacity
        )

    def push(self, *transition) -> None:
        self.buf.append(transition)

    def sample(self, batch_size: int):
        s, a, r, ns, d = zip(*random.sample(self.buf, batch_size))
        return (
            np.array(s, np.float32),
            np.array(a, np.int64),
            np.array(r, np.float32),
            np.array(ns, np.float32),
            np.array(d, np.float32),
        )

    def __len__(self) -> int:
        return len(self.buf)


class QNet(nn.Module):
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


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


class Inst:
    def __init__(self, raw: Dict):
        self.name = raw["name"]
        data = raw["data"]
        self.capacity = raw["capacity"]
        self.coords = data[:, 1:3]
        self.demands = data[:, 3]
        self.ready_times = data[:, 4]
        self.due_times = data[:, 5]
        self.service_times = data[:, 6]
        self.horizon = self.due_times[0]
        self.n = len(data) - 1
        diff = self.coords[:, None, :] - self.coords[None, :, :]
        self.dist = np.sqrt((diff**2).sum(axis=2))
        self.max_dist = self.dist.max()
        self.tw_width = self.due_times - self.ready_times
        self.max_tw_width = self.tw_width[1:].max() + 1e-9
        self.tw_tight_frac = sum(
            1
            for i in range(1, self.n + 1)
            if self.tw_width[i] < 0.2 * self.horizon
        ) / self.n


def load_datasets(base_path: str) -> Dict[str, List[Inst]]:
    datasets: Dict[str, List[Inst]] = {}
    for group in ("rc1", "rc2"):
        files = sorted(glob.glob(os.path.join(base_path, f"{group}*.txt")))
        insts: List[Inst] = []
        for path in files:
            with open(path) as handle:
                lines = handle.readlines()
            name = lines[0].strip()
            capacity = float(lines[4].strip().split()[1])
            rows = [
                list(map(float, line.split()))
                for line in lines[9:]
                if line.strip()
            ]
            insts.append(Inst({"name": name, "capacity": capacity, "data": np.array(rows)}))
        datasets[group] = insts
    return datasets


@njit(cache=True)
def _route_cost(route: np.ndarray, dist: np.ndarray) -> float:
    cost = dist[0, route[0]]
    for i in range(len(route) - 1):
        cost += dist[route[i], route[i + 1]]
    return cost + dist[route[-1], 0]


@njit(cache=True)
def _route_ok(
    route: np.ndarray,
    demands: np.ndarray,
    capacity: float,
    ready: np.ndarray,
    due: np.ndarray,
    service: np.ndarray,
    dist: np.ndarray,
) -> bool:
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
        self.routes = [route for route in routes if route]
        self.inst = inst
        self._cost: Optional[float] = None
        self._ok: Optional[bool] = None
        self.algo = algo

    @property
    def cost(self) -> float:
        if self._cost is None:
            self._cost = sum(
                _route_cost(np.array(route, np.int64), self.inst.dist)
                for route in self.routes
            )
        return self._cost

    @property
    def feasible(self) -> bool:
        if self._ok is None:
            inst = self.inst
            self._ok = all(
                _route_ok(
                    np.array(route, np.int64),
                    inst.demands,
                    inst.capacity,
                    inst.ready_times,
                    inst.due_times,
                    inst.service_times,
                    inst.dist,
                )
                for route in self.routes
            )
        return self._ok

    @property
    def nv(self) -> int:
        return len(self.routes)

    def dominates(self, other: "Plan") -> bool:
        return self.nv < other.nv or (self.nv == other.nv and self.cost < other.cost)

    def copy(self) -> "Plan":
        return Plan([route[:] for route in self.routes], self.inst, self.algo)

    def invalidate(self) -> None:
        self._cost = None
        self._ok = None

    def gap(self) -> Tuple[Optional[float], Optional[int]]:
        bks = BKS.get(self.inst.name)
        if not bks:
            return None, None
        td_gap = (self.cost - bks["td"]) / bks["td"] * 100
        nv_diff = self.nv - bks["nv"]
        return td_gap, nv_diff

    @property
    def on_time_rate(self) -> float:
        inst = self.inst
        on_time = 0
        total = 0
        for route in self.routes:
            current_time, prev = 0.0, 0
            for node in route:
                current_time += inst.dist[prev, node]
                current_time = max(current_time, inst.ready_times[node])
                total += 1
                if current_time <= inst.due_times[node]:
                    on_time += 1
                current_time += inst.service_times[node]
                prev = node
        return on_time / max(total, 1)


@dataclass(frozen=True)
class RouteRecord:
    nodes: Tuple[int, ...]
    cost: float
    load: float
    slack: float


def _route_cost_list(route: List[int], inst: Inst) -> float:
    if not route:
        return 0.0
    return float(_route_cost(np.array(route, np.int64), inst.dist))


def _route_load(route: List[int], inst: Inst) -> float:
    return float(sum(inst.demands[node] for node in route))


def _route_avg_slack(route: List[int], inst: Inst) -> float:
    if not route:
        return 0.0
    slack_sum = 0.0
    current_time = 0.0
    prev = 0
    for node in route:
        current_time += inst.dist[prev, node]
        current_time = max(current_time, inst.ready_times[node])
        slack_sum += inst.due_times[node] - current_time
        current_time += inst.service_times[node]
        prev = node
    return slack_sum / len(route)


def _fleet_fill(plan: Plan) -> float:
    if not plan.routes:
        return 0.0
    loads = [_route_load(route, plan.inst) / max(plan.inst.capacity, 1) for route in plan.routes]
    return float(np.mean(loads))


class RoutePool:
    def __init__(self, inst: Inst, cfg: Config):
        self.inst = inst
        self.cfg = cfg
        self._routes: Dict[Tuple[int, ...], RouteRecord] = {}

    def _priority(self, rec: RouteRecord) -> Tuple[float, ...]:
        load_ratio = rec.load / max(self.inst.capacity, 1)
        cost_per_customer = rec.cost / max(len(rec.nodes), 1)
        return (-len(rec.nodes), cost_per_customer, -load_ratio, -rec.slack)

    def _trim(self) -> None:
        limit = self.cfg.route_pool_limit
        if len(self._routes) <= limit:
            return

        usage: Dict[int, int] = {}
        kept: Dict[Tuple[int, ...], RouteRecord] = {}
        ranked = sorted(self._routes.values(), key=self._priority)

        for rec in ranked:
            if len(kept) >= limit:
                break
            under_cap = all(
                usage.get(node, 0) < self.cfg.route_pool_max_per_customer for node in rec.nodes
            )
            if under_cap or len(kept) < limit // 3:
                kept[rec.nodes] = rec
                for node in rec.nodes:
                    usage[node] = usage.get(node, 0) + 1

        if len(kept) < limit:
            for rec in ranked:
                if rec.nodes in kept:
                    continue
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
        for route in plan.routes:
            self.add_route(route)

    def records(self, incumbent: Optional[Plan] = None) -> List[RouteRecord]:
        records = dict(self._routes)
        if incumbent is not None:
            for route in incumbent.routes:
                key = tuple(route)
                records[key] = RouteRecord(
                    nodes=key,
                    cost=_route_cost_list(route, self.inst),
                    load=_route_load(route, self.inst),
                    slack=_route_avg_slack(route, self.inst),
                )
        return sorted(records.values(), key=self._priority)


def _sp_vehicle_penalty(inst: Inst, cfg: Config) -> float:
    return cfg.sp_vehicle_penalty_scale * max(inst.max_dist, 1.0) * max(inst.n, 1)


def _milp_recombine(
    route_records: List[RouteRecord],
    inst: Inst,
    cfg: Config,
    nv_ceiling: Optional[int] = None,
) -> Optional[Plan]:
    if milp is None or Bounds is None or LinearConstraint is None or not route_records:
        return None

    n_routes = len(route_records)
    cover = np.zeros((inst.n, n_routes), dtype=float)
    for j, rec in enumerate(route_records):
        for node in rec.nodes:
            cover[node - 1, j] = 1.0

    if np.any(cover.sum(axis=1) == 0):
        return None

    constraints = [LinearConstraint(cover, lb=np.ones(inst.n), ub=np.ones(inst.n))]
    if nv_ceiling is not None:
        constraints.append(
            LinearConstraint(np.ones((1, n_routes)), lb=np.array([0.0]), ub=np.array([nv_ceiling]))
        )

    costs = np.array(
        [_sp_vehicle_penalty(inst, cfg) + rec.cost for rec in route_records],
        dtype=float,
    )
    result = milp(
        c=costs,
        constraints=constraints,
        integrality=np.ones(n_routes, dtype=int),
        bounds=Bounds(np.zeros(n_routes), np.ones(n_routes)),
        options={"time_limit": float(cfg.sp_time_limit), "disp": False},
    )
    if result is None or not getattr(result, "success", False) or result.x is None:
        return None

    chosen = [list(route_records[j].nodes) for j, value in enumerate(result.x) if value >= 0.5]
    plan = Plan(chosen, inst, "SP-RECOMBINE")
    return plan if plan.feasible else None


def _greedy_recombine(
    route_records: List[RouteRecord],
    incumbent: Plan,
    nv_ceiling: Optional[int] = None,
) -> Plan:
    uncovered = set(range(1, incumbent.inst.n + 1))
    selected: List[List[int]] = []
    used: set = set()

    while uncovered:
        best_rec = None
        best_score = -float("inf")
        for rec in route_records:
            if rec.nodes in used:
                continue
            route_set = set(rec.nodes)
            if route_set & {node for route in selected for node in route}:
                continue
            gain = len(route_set & uncovered)
            if gain == 0:
                continue
            score = gain * 10.0 + len(rec.nodes) - rec.cost / max(len(rec.nodes), 1)
            if score > best_score:
                best_score = score
                best_rec = rec
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


def recombine_with_route_pool(
    incumbent: Plan,
    pool: RoutePool,
    cfg: Config,
    nv_ceiling: Optional[int] = None,
) -> Plan:
    pool.add_plan(incumbent)
    route_records = pool.records(incumbent)
    if not route_records:
        return incumbent.copy()

    candidate = _milp_recombine(route_records, incumbent.inst, cfg, nv_ceiling=nv_ceiling)
    if candidate is None:
        candidate = _greedy_recombine(route_records, incumbent, nv_ceiling=nv_ceiling)

    if nv_ceiling is not None and candidate.nv > nv_ceiling:
        return incumbent.copy()
    return candidate if candidate.dominates(incumbent) else incumbent.copy()


def _two_opt_best(route: List[int], inst: Inst) -> List[int]:
    if len(route) < 4:
        return route[:]
    best = route[:]
    best_cost = _route_cost_list(best, inst)
    for i in range(len(route) - 2):
        for j in range(i + 2, len(route)):
            cand = route[:i] + list(reversed(route[i : j + 1])) + route[j + 1 :]
            if not _check_route(cand, inst):
                continue
            cand_cost = _route_cost_list(cand, inst)
            if cand_cost + 1e-9 < best_cost:
                best = cand
                best_cost = cand_cost
    return best


def _best_relocate(plan: Plan, nv_ceiling: Optional[int] = None) -> Optional[Tuple[int, int, int, int]]:
    inst = plan.inst
    current_nv = plan.nv
    best_delta = -1e-9
    best_move: Optional[Tuple[int, int, int, int]] = None

    for src_idx, src_route in enumerate(plan.routes):
        src_cost = _route_cost_list(src_route, inst)
        for node_pos, node in enumerate(src_route):
            src_new = src_route[:node_pos] + src_route[node_pos + 1 :]
            if src_new and not _check_route(src_new, inst):
                continue
            src_new_cost = _route_cost_list(src_new, inst)

            for dst_idx, dst_route in enumerate(plan.routes):
                if dst_idx == src_idx:
                    continue
                dst_cost = _route_cost_list(dst_route, inst)
                for insert_pos in range(len(dst_route) + 1):
                    dst_new = dst_route[:insert_pos] + [node] + dst_route[insert_pos:]
                    if not _check_route(dst_new, inst):
                        continue

                    new_nv = current_nv - (1 if not src_new else 0)
                    if nv_ceiling is not None and new_nv > nv_ceiling:
                        continue

                    delta = src_new_cost + _route_cost_list(dst_new, inst) - src_cost - dst_cost
                    if new_nv < current_nv:
                        delta -= 1000.0
                    if delta < best_delta:
                        best_delta = delta
                        best_move = (src_idx, node_pos, dst_idx, insert_pos)
    return best_move


def _apply_relocate(plan: Plan, move: Tuple[int, int, int, int]) -> Plan:
    src_idx, node_pos, dst_idx, insert_pos = move
    routes = [route[:] for route in plan.routes]
    node = routes[src_idx].pop(node_pos)
    if src_idx < dst_idx and len(routes[src_idx]) == 0:
        dst_idx -= 1
    routes = [route for route in routes if route]
    routes[dst_idx].insert(insert_pos, node)
    return Plan(routes, plan.inst, plan.algo)


def local_search(plan: Plan, max_passes: int = 1, nv_ceiling: Optional[int] = None) -> Plan:
    best = plan.copy()
    inst = plan.inst
    for _ in range(max_passes):
        improved = False
        routes = []
        for route in best.routes:
            new_route = _two_opt_best(route, inst)
            routes.append(new_route)
            if new_route != route:
                improved = True
        best = Plan(routes, inst, best.algo)

        move = _best_relocate(best, nv_ceiling=nv_ceiling)
        if move is not None:
            best = _apply_relocate(best, move)
            improved = True

        if not improved:
            break
    return best


def _invalidate(plan: Plan) -> Plan:
    plan.invalidate()
    return plan


def _check_route(route: List[int], inst: Inst) -> bool:
    return bool(
        _route_ok(
            np.array(route, np.int64),
            inst.demands,
            inst.capacity,
            inst.ready_times,
            inst.due_times,
            inst.service_times,
            inst.dist,
        )
    )


def _best_insert_position(node: int, route: List[int], inst: Inst) -> Tuple[float, Optional[int]]:
    best_cost, best_pos = float("inf"), None
    for pos in range(len(route) + 1):
        prev = route[pos - 1] if pos > 0 else 0
        nxt = route[pos] if pos < len(route) else 0
        delta = inst.dist[prev, node] + inst.dist[node, nxt] - inst.dist[prev, nxt]
        if delta < best_cost and _check_route(route[:pos] + [node] + route[pos:], inst):
            best_cost, best_pos = delta, pos
    return best_cost, best_pos


def _insert_customer(plan: Plan, node: int, inst: Inst) -> None:
    best_cost, best_route, best_pos = float("inf"), None, None
    for route_idx, route in enumerate(plan.routes):
        delta, pos = _best_insert_position(node, route, inst)
        if pos is not None and delta < best_cost:
            best_cost, best_route, best_pos = delta, route_idx, pos

    if best_route is not None:
        plan.routes[best_route].insert(best_pos, node)
    else:
        plan.routes.append([node])
    plan.invalidate()


def build_greedy(inst: Inst, algo: str = "") -> Plan:
    def arrival(route: List[int], pos: int, node: int, arrivals: List[float]) -> float:
        prev = route[pos - 1] if pos > 0 else 0
        current_time = arrivals[pos - 1] if pos > 0 else 0.0
        current_time += inst.dist[prev, node]
        return max(current_time, inst.ready_times[node])

    def feasible_insert(
        route: List[int], pos: int, node: int, arrivals: List[float], load: float
    ) -> Tuple[bool, Optional[float]]:
        if load + inst.demands[node] > inst.capacity:
            return False, None
        current_time = arrival(route, pos, node, arrivals)
        if current_time > inst.due_times[node]:
            return False, None

        forward_time = current_time + inst.service_times[node]
        prev = node
        for idx in range(pos, len(route)):
            next_node = route[idx]
            forward_time += inst.dist[prev, next_node]
            forward_time = max(forward_time, inst.ready_times[next_node])
            if forward_time > inst.due_times[next_node]:
                return False, None
            forward_time += inst.service_times[next_node]
            prev = next_node
        return True, current_time

    def compute_arrivals(route: List[int]) -> List[float]:
        arrivals: List[float] = []
        current_time, prev = 0.0, 0
        for node in route:
            current_time += inst.dist[prev, node]
            current_time = max(current_time, inst.ready_times[node])
            arrivals.append(current_time)
            current_time += inst.service_times[node]
            prev = node
        return arrivals

    def best_insert_cost(
        route: List[int], node: int, arrivals: List[float], load: float
    ) -> Tuple[float, Optional[int]]:
        best_cost, best_pos = float("inf"), None
        for pos in range(len(route) + 1):
            ok, _ = feasible_insert(route, pos, node, arrivals, load)
            if not ok:
                continue
            prev = route[pos - 1] if pos > 0 else 0
            nxt = route[pos] if pos < len(route) else 0
            delta = inst.dist[prev, node] + inst.dist[node, nxt] - inst.dist[prev, nxt]
            if delta < best_cost:
                best_cost, best_pos = delta, pos
        return best_cost, best_pos

    unrouted = list(range(1, inst.n + 1))
    routes: List[List[int]] = []
    while unrouted:
        seed = max(unrouted, key=lambda node: inst.dist[0, node])
        seed_arrival = max(inst.dist[0, seed], inst.ready_times[seed])
        if seed_arrival > inst.due_times[seed]:
            seed = min(unrouted, key=lambda node: inst.due_times[node])
        route = [seed]
        load = inst.demands[seed]
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

    customers = sorted(
        range(1, inst.n + 1),
        key=lambda node: (inst.due_times[node], inst.ready_times[node]),
    )
    unrouted_set = set(customers)
    fallback_routes: List[List[int]] = []
    while unrouted_set:
        route: List[int] = []
        node = 0
        load = 0.0
        current_time = 0.0
        while unrouted_set:
            feasible_nodes = [
                cand
                for cand in unrouted_set
                if load + inst.demands[cand] <= inst.capacity
                and current_time + inst.dist[node, cand] <= inst.due_times[cand]
            ]
            if not feasible_nodes:
                break
            nxt = min(feasible_nodes, key=lambda cand: inst.dist[node, cand])
            route.append(nxt)
            unrouted_set.remove(nxt)
            load += inst.demands[nxt]
            current_time = (
                max(current_time + inst.dist[node, nxt], inst.ready_times[nxt])
                + inst.service_times[nxt]
            )
            node = nxt
        if route:
            fallback_routes.append(route)
        elif unrouted_set:
            nxt = next(iter(unrouted_set))
            fallback_routes.append([nxt])
            unrouted_set.remove(nxt)
    return Plan(fallback_routes, inst, algo)


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


def destroy_size(it: int, n_iters: int, cfg: Config, n_customers: int, scale: float = 1.0) -> int:
    ratio = cfg.destroy_ratio_max - (
        (cfg.destroy_ratio_max - cfg.destroy_ratio_min) * (it / max(n_iters, 1))
    )
    ratio = min(cfg.destroy_ratio_max, max(cfg.destroy_ratio_min, ratio * scale))
    return max(3, int(ratio * n_customers))


def op_random(plan: Plan, size: int) -> Tuple[Plan, List[int]]:
    nodes = [node for route in plan.routes for node in route]
    removed = random.sample(nodes, min(size, len(nodes)))
    removed_set = set(removed)
    plan.routes = [[node for node in route if node not in removed_set] for route in plan.routes]
    plan.routes = [route for route in plan.routes if route]
    return _invalidate(plan), removed


def op_worst(plan: Plan, size: int) -> Tuple[Plan, List[int]]:
    inst = plan.inst
    gains: List[Tuple[float, int]] = []
    for route in plan.routes:
        for idx, node in enumerate(route):
            prev = route[idx - 1] if idx > 0 else 0
            nxt = route[idx + 1] if idx < len(route) - 1 else 0
            gain = inst.dist[prev, node] + inst.dist[node, nxt] - inst.dist[prev, nxt]
            gains.append((gain, node))
    gains.sort(reverse=True)
    removed = [node for _, node in gains[:size]]
    removed_set = set(removed)
    plan.routes = [[node for node in route if node not in removed_set] for route in plan.routes]
    plan.routes = [route for route in plan.routes if route]
    return _invalidate(plan), removed


def op_shaw(plan: Plan, size: int) -> Tuple[Plan, List[int]]:
    inst = plan.inst
    nodes = [node for route in plan.routes for node in route]
    if not nodes:
        return plan, []
    seed = random.choice(nodes)
    removed = [seed]
    removed_set = {seed}
    max_dist = inst.max_dist + 1e-9
    max_tw = max(inst.due_times - inst.ready_times) + 1e-9

    while len(removed) < size:
        candidates = [
            (
                node,
                0.5 * inst.dist[seed, node] / max_dist
                + 0.4 * abs(inst.ready_times[seed] - inst.ready_times[node]) / max_tw
                + 0.1 * abs(inst.demands[seed] - inst.demands[node]) / inst.capacity,
            )
            for node in nodes
            if node not in removed_set
        ]
        if not candidates:
            break
        nxt = min(candidates, key=lambda item: item[1])[0]
        removed.append(nxt)
        removed_set.add(nxt)

    plan.routes = [[node for node in route if node not in removed_set] for route in plan.routes]
    plan.routes = [route for route in plan.routes if route]
    return _invalidate(plan), removed


def op_route(plan: Plan, size: int) -> Tuple[Plan, List[int]]:
    if len(plan.routes) <= 1:
        return op_random(plan, size)
    removed: List[int] = []
    route_ids = set()
    for idx, route in sorted(enumerate(plan.routes), key=lambda item: len(item[1])):
        if len(removed) + len(route) <= size * 1.5:
            removed.extend(route)
            route_ids.add(idx)
        if len(removed) >= size:
            break
    plan.routes = [route for idx, route in enumerate(plan.routes) if idx not in route_ids] or [[]]
    return _invalidate(plan), removed


def op_route_eliminate(plan: Plan, size: int) -> Tuple[Plan, List[int]]:
    if len(plan.routes) <= 1:
        return op_random(plan, size)

    inst = plan.inst
    ranked = sorted(
        enumerate(plan.routes),
        key=lambda item: (
            len(item[1]),
            _route_load(item[1], inst) / max(inst.capacity, 1),
            _route_cost_list(item[1], inst) / max(len(item[1]), 1),
        ),
    )

    removed: List[int] = []
    removed_ids = set()
    for idx, route in ranked:
        removed.extend(route)
        removed_ids.add(idx)
        if len(removed) >= max(2, size // 2):
            break

    plan.routes = [route for idx, route in enumerate(plan.routes) if idx not in removed_ids]
    return _invalidate(plan), removed


def op_tw_urgent(plan: Plan, size: int) -> Tuple[Plan, List[int]]:
    inst = plan.inst
    nodes = [node for route in plan.routes for node in route]
    if not nodes:
        return plan, []
    removed = sorted(nodes, key=lambda node: inst.due_times[node] - inst.ready_times[node])[:size]
    removed_set = set(removed)
    plan.routes = [[node for node in route if node not in removed_set] for route in plan.routes]
    plan.routes = [route for route in plan.routes if route]
    return _invalidate(plan), removed


def op_greedy(plan: Plan, removed: List[int]) -> Plan:
    inst = plan.inst
    for node in sorted(removed, key=lambda n: inst.due_times[n]):
        _insert_customer(plan, node, inst)
    return Plan(plan.routes, inst, plan.algo)


def _regret(plan: Plan, removed: List[int], k: int) -> Plan:
    inst = plan.inst
    remaining = removed[:]
    while remaining:
        best_regret, chosen, choice = -float("inf"), None, None
        for node in remaining:
            options = sorted(
                (delta, route_idx, pos)
                for route_idx, route in enumerate(plan.routes)
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
            _, route_idx, pos = choice
            plan.routes[route_idx].insert(pos, chosen)
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


DESTROY = [op_random, op_worst, op_shaw, op_route, op_tw_urgent, op_route_eliminate]
REPAIR = [op_greedy, op_regret_2, op_regret_3, op_tw_greedy]
N_D = len(DESTROY)
N_R = len(REPAIR)


def _roulette(weights: np.ndarray) -> int:
    return int(np.random.choice(len(weights), p=weights / weights.sum()))


def _avg_slack(plan: Plan) -> float:
    inst = plan.inst
    slack_sum = 0.0
    count = 0
    for route in plan.routes:
        current_time, prev = 0.0, 0
        for node in route:
            current_time += inst.dist[prev, node]
            current_time = max(current_time, inst.ready_times[node])
            slack_sum += inst.due_times[node] - current_time
            current_time += inst.service_times[node]
            prev = node
            count += 1
    return (slack_sum / count) / max(inst.horizon, 1) if count else 0.0


def _plan_spread(plan: Plan, inst: Inst) -> Tuple[float, float]:
    lengths = [len(route) for route in plan.routes] or [0]
    loads = [sum(inst.demands[node] for node in route) for route in plan.routes] or [0]
    route_balance = float(np.std(lengths) / max(np.mean(lengths), 1)) if len(lengths) > 1 else 0.0
    load_balance = float(np.std(loads) / max(inst.capacity, 1))
    return min(route_balance, 1.0), min(load_balance, 1.0)


class ALNSSolver:
    def __init__(self, inst: Inst, cfg: Config):
        self.inst = inst
        self.cfg = cfg

    def solve(self, seed: Optional[int] = None, init: Optional[Plan] = None) -> Tuple[Plan, List[float]]:
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        cfg = self.cfg
        cur = init.copy() if init else build_greedy(self.inst, "ALNS")
        best = cur.copy()
        temp = cfg.temp_control * cur.cost / math.log(2)
        dw = np.ones(N_D)
        rw = np.ones(N_R)
        seg_scores = np.zeros((N_D, N_R))
        seg_counts = np.zeros((N_D, N_R))
        history = [best.cost]
        no_imp = 0

        for it in range(cfg.alns_iterations):
            di = _roulette(dw)
            ri = _roulette(rw)
            size = destroy_size(it, cfg.alns_iterations, cfg, self.inst.n)
            dest, removed = DESTROY[di](cur.copy(), size)
            cand = REPAIR[ri](dest, removed)
            score = 0
            if accept(cur, cand, temp):
                if cand.dominates(best):
                    best = cand.copy()
                    score = cfg.sigma1
                    no_imp = 0
                elif cand.dominates(cur):
                    score = cfg.sigma2
                    no_imp = 0
                else:
                    score = cfg.sigma3
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
                            avg = seg_scores[d, r] / seg_counts[d, r]
                            dw[d] = dw[d] * (1 - cfg.weight_decay) + avg * cfg.weight_decay
                            rw[r] = rw[r] * (1 - cfg.weight_decay) + avg * cfg.weight_decay
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


class PlateauHybridSolver:
    def __init__(self, inst: Inst, cfg: Config):
        self.inst = inst
        self.cfg = cfg
        self.ctrl = PlateauController(cfg)

    def _state(
        self,
        cur: Plan,
        best: Plan,
        no_imp: int,
        temp: float,
        dw: np.ndarray,
        rw: np.ndarray,
        imp_rate: float,
        progress: float,
    ) -> np.ndarray:
        inst = self.inst
        route_balance, load_balance = _plan_spread(cur, inst)
        t0 = self.cfg.temp_control * best.cost / math.log(2)
        temp_norm = min(temp / max(t0, 1e-6), 1.5)
        cost_gap = min((cur.cost - best.cost) / max(best.cost, 1), 1.0)
        nv_ratio = cur.nv / max(self._init_nv, 1)
        return np.array(
            [
                min(no_imp / max(self.cfg.early_stop_patience, 1), 1.0),
                cost_gap,
                temp_norm,
                imp_rate,
                min(nv_ratio, 2.0),
                route_balance,
                load_balance,
                inst.tw_tight_frac,
                _avg_slack(cur),
                progress,
            ],
            dtype=np.float32,
        )

    def _segment_reward(
        self,
        best_before: Plan,
        best_after: Plan,
        cur_before: Plan,
        cur_after: Plan,
        accepted_moves: int,
    ) -> float:
        reward = -0.75

        if best_after.nv < best_before.nv:
            reward += 30.0 * (best_before.nv - best_after.nv)
            reward += max((best_before.cost - best_after.cost) / max(best_before.cost, 1), 0.0) * 100
        elif best_after.nv == best_before.nv and best_after.cost < best_before.cost:
            reward += 4.0 * (best_before.cost - best_after.cost) / max(best_before.cost, 1) * 100

        if cur_after.nv == cur_before.nv and cur_after.cost < cur_before.cost:
            reward += 0.75 * (cur_before.cost - cur_after.cost) / max(cur_before.cost, 1) * 100

        if cur_after.nv > cur_before.nv:
            reward -= self.cfg.nv_increase_penalty * (cur_after.nv - cur_before.nv)

        reward += 3.0 * (_fleet_fill(cur_after) - _fleet_fill(cur_before))

        if accepted_moves == 0:
            reward -= 0.75
        return float(reward)

    def _fixed_nv_polish(self, start: Plan, pool: RoutePool) -> Plan:
        cfg = self.cfg
        target_nv = start.nv
        cur = local_search(start, max_passes=cfg.polish_ls_passes, nv_ceiling=target_nv)
        best = cur.copy()
        pool.add_plan(best)
        temp = cfg.temp_control * best.cost / math.log(2)
        no_imp = 0

        polish_dw = np.array([0.3, 1.4, 1.3, 0.8, 1.2, 0.9], dtype=np.float32)
        polish_rw = np.array([0.8, 1.2, 1.5, 1.2], dtype=np.float32)

        for it in range(cfg.polish_iterations):
            di = _roulette(polish_dw)
            ri = _roulette(polish_rw)
            size = destroy_size(
                it,
                cfg.polish_iterations,
                cfg,
                self.inst.n,
                scale=0.70,
            )

            dest, removed = DESTROY[di](cur.copy(), size)
            cand = REPAIR[ri](dest, removed)
            cand = local_search(cand, max_passes=1, nv_ceiling=target_nv)
            pool.add_plan(cand)

            cur_before = cur
            if accept_with_nv_ceiling(cur, cand, temp, target_nv):
                cur = cand
                if cand.nv < target_nv:
                    target_nv = cand.nv
                if cand.dominates(best):
                    best = cand.copy()
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

    def solve(self, seed: Optional[int] = None) -> Tuple[Plan, List[float]]:
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
            torch.manual_seed(seed)

        cfg = self.cfg
        self.ctrl.reset()
        pool = RoutePool(self.inst, cfg)

        cur = build_greedy(self.inst, "PLATEAU-HYBRID")
        best = cur.copy()
        pool.add_plan(cur)
        self._init_nv = cur.nv
        temp = cfg.temp_control * cur.cost / math.log(2)
        dw = np.ones(N_D)
        rw = np.ones(N_R)
        history = [best.cost]
        no_imp = 0
        recent_improvements: Deque[int] = deque(maxlen=cfg.segment_size)
        post_improve_lock = 0

        n_segments = math.ceil(cfg.hybrid_iterations / cfg.segment_size)
        for segment_idx in range(n_segments):
            progress = segment_idx / max(n_segments, 1)
            imp_rate = sum(recent_improvements) / len(recent_improvements) if recent_improvements else 0.0
            state_before = self._state(cur, best, no_imp, temp, dw, rw, imp_rate, progress)
            route_reduce_trigger = (
                no_imp >= cfg.plateau_start
                and _fleet_fill(cur) < max(0.52, 0.80 - 0.25 * self.inst.tw_tight_frac)
            )

            if post_improve_lock > 0:
                action = MODE_INTENSIFY
                post_improve_lock -= 1
                controller_active = False
            elif route_reduce_trigger:
                action = MODE_ROUTE_REDUCE
                controller_active = False
            elif no_imp >= cfg.plateau_start:
                action = self.ctrl.act(state_before)
                controller_active = True
            else:
                action = MODE_DEFAULT
                controller_active = False

            mode = MODES[action]
            biased_dw = np.maximum(dw * np.array(mode.destroy_bias, dtype=np.float32), 0.1)
            biased_rw = np.maximum(rw * np.array(mode.repair_bias, dtype=np.float32), 0.1)
            temp *= mode.temp_boost

            seg_scores = np.zeros((N_D, N_R))
            seg_counts = np.zeros((N_D, N_R))
            segment_best_before = best.copy()
            segment_cur_before = cur.copy()
            accepted_moves = 0
            best_improved = False

            for offset in range(cfg.segment_size):
                it = segment_idx * cfg.segment_size + offset
                if it >= cfg.hybrid_iterations:
                    break

                di = _roulette(biased_dw)
                ri = _roulette(biased_rw)
                size = destroy_size(
                    it,
                    cfg.hybrid_iterations,
                    cfg,
                    self.inst.n,
                    scale=mode.destroy_scale,
                )

                dest, removed = DESTROY[di](cur.copy(), size)
                cand = REPAIR[ri](dest, removed)
                score = 0
                improved = False

                if accept(cur, cand, temp):
                    accepted_moves += 1
                    improved = cand.dominates(cur)
                    pool.add_plan(cand)
                    if cand.dominates(best):
                        best = cand.copy()
                        best_improved = True
                        pool.add_plan(best)
                        score = cfg.sigma1
                        no_imp = 0
                    elif improved:
                        score = cfg.sigma2
                        no_imp = 0
                    else:
                        score = cfg.sigma3
                        no_imp += 1
                    cur = cand
                else:
                    no_imp += 1

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
                        avg = seg_scores[d, r] / seg_counts[d, r]
                        dw[d] = dw[d] * (1 - cfg.weight_decay) + avg * cfg.weight_decay
                        rw[r] = rw[r] * (1 - cfg.weight_decay) + avg * cfg.weight_decay
            dw = np.maximum(dw, 0.1)
            rw = np.maximum(rw, 0.1)

            progress_after = min((segment_idx + 1) / max(n_segments, 1), 1.0)
            imp_rate_after = (
                sum(recent_improvements) / len(recent_improvements) if recent_improvements else 0.0
            )
            state_after = self._state(
                cur, best, no_imp, temp, dw, rw, imp_rate_after, progress_after
            )

            if controller_active:
                reward = self._segment_reward(
                    segment_best_before,
                    best,
                    segment_cur_before,
                    cur,
                    accepted_moves,
                )
                self.ctrl.observe(state_before, action, reward, state_after, 0.0)
                self.ctrl.train_step()

            if best_improved:
                post_improve_lock = cfg.post_improve_intensify_segments

            if no_imp >= cfg.early_stop_patience:
                break

        if cfg.recombine_after_main_search:
            recombined = recombine_with_route_pool(best, pool, cfg, nv_ceiling=best.nv)
            if recombined.dominates(best):
                best = recombined
                pool.add_plan(best)
                history.append(best.cost)

        polished = self._fixed_nv_polish(best, pool)
        if polished.dominates(best):
            best = polished
            history.append(best.cost)
        else:
            best = polished

        if cfg.recombine_after_polish:
            recombined = recombine_with_route_pool(best, pool, cfg, nv_ceiling=best.nv)
            if recombined.dominates(best):
                best = local_search(
                    recombined,
                    max_passes=cfg.polish_ls_passes,
                    nv_ceiling=recombined.nv,
                )
                history.append(best.cost)

        best.algo = "PLATEAU-HYBRID"
        return best, history


def run_instance(inst: Inst, algo: str, cfg: Config, seed: int) -> Dict:
    start = time.time()
    if algo == "ALNS":
        plan, history = ALNSSolver(inst, cfg).solve(seed=seed)
    elif algo in {"PLATEAU-HYBRID", "PLATEAU-HYBRID-VNEXT", "HYBRID-VNEXT"}:
        plan, history = PlateauHybridSolver(inst, cfg).solve(seed=seed)
    else:
        raise ValueError(f"Unsupported algorithm: {algo}")

    elapsed = time.time() - start
    bks = BKS.get(inst.name)
    return {
        "nv": plan.nv,
        "cost": plan.cost,
        "time": elapsed,
        "td_gap": (plan.cost - bks["td"]) / bks["td"] * 100 if bks else None,
        "nv_diff": plan.nv - bks["nv"] if bks else None,
        "on_time": plan.on_time_rate,
        "hist": history,
    }


def run_benchmark(
    instances: Iterable[Inst],
    algorithms: List[str],
    cfg: Config,
    result_path: Optional[str] = None,
) -> pd.DataFrame:
    instances = list(instances)
    if result_path is None:
        result_path = os.path.join(cfg.output_dir, "benchmark_clean.csv")

    rows: List[Dict] = []
    total = len(instances) * len(algorithms)
    print(f"Total: {total} combos x {cfg.n_runs} runs")
    print("=" * 60)

    for inst in instances:
        dataset = "RC1" if int(inst.name[2]) == 1 else "RC2"
        for algo in algorithms:
            print(f"\n[{inst.name}] {algo}")
            nv_vals, cost_vals, time_vals = [], [], []
            gap_vals, nv_diff_vals, on_time_vals = [], [], []

            for run_idx in range(cfg.n_runs):
                res = run_instance(inst, algo, cfg, cfg.seed + run_idx)
                nv_vals.append(res["nv"])
                cost_vals.append(res["cost"])
                time_vals.append(res["time"])
                gap_vals.append(res["td_gap"])
                nv_diff_vals.append(res["nv_diff"])
                on_time_vals.append(res["on_time"])
                print(
                    f"  run {run_idx + 1}/{cfg.n_runs}: "
                    f"nv={res['nv']} cost={res['cost']:.1f} ({res['time']:.1f}s)"
                )

            row = {
                "Dataset": dataset,
                "Instance": inst.name,
                "Algorithm": algo,
                "NV_mean": round(np.mean(nv_vals), 2),
                "NV_std": round(np.std(nv_vals), 2),
                "NV_diff": round(np.mean(nv_diff_vals), 2) if nv_diff_vals[0] is not None else None,
                "TD_mean": round(np.mean(cost_vals), 2),
                "TD_std": round(np.std(cost_vals), 2),
                "Gap%": round(np.mean(gap_vals), 2) if gap_vals[0] is not None else None,
                "OnTime": round(np.mean(on_time_vals) * 100, 1),
                "Time_s": round(np.mean(time_vals), 1),
                "NV_cv": round(np.std(nv_vals) / max(np.mean(nv_vals), 1) * 100, 2),
                "TD_cv": round(np.std(cost_vals) / max(np.mean(cost_vals), 1) * 100, 2),
            }
            rows.append(row)
            gap_text = f"{row['Gap%']:+.1f}%" if row["Gap%"] is not None else "--"
            print(
                f"  -> nv={row['NV_mean']:.1f}+-{row['NV_std']:.1f} "
                f"td={row['TD_mean']:.1f}+-{row['TD_std']:.1f} gap={gap_text}"
            )

    df = pd.DataFrame(rows)
    df.to_csv(result_path, index=False)
    return df


def print_summary_table(df: pd.DataFrame) -> None:
    summary = (
        df.groupby(["Dataset", "Algorithm"])
        .agg(
            NV=("NV_mean", "mean"),
            NV_std=("NV_std", "mean"),
            NV_diff=("NV_diff", "mean"),
            TD=("TD_mean", "mean"),
            TD_std=("TD_std", "mean"),
            Gap=("Gap%", "mean"),
            OnTime=("OnTime", "mean"),
            Time=("Time_s", "mean"),
        )
        .round(2)
        .reset_index()
    )

    print("\n" + "-" * 86)
    print(f"{'DS':<4}{'Algorithm':<18}{'NV':>6}{'+/-':>6}{'vsBKS':>8}{'TD':>10}{'+/-':>8}{'Gap%':>8}{'OT%':>7}{'Time':>8}")
    print("-" * 86)
    for _, row in summary.iterrows():
        gap = f"{row['Gap']:+.2f}%" if pd.notna(row["Gap"]) else "--"
        nv_diff = f"{row['NV_diff']:+.2f}" if pd.notna(row["NV_diff"]) else "--"
        print(
            f"{row['Dataset']:<4}{row['Algorithm']:<18}"
            f"{row['NV']:>6.2f}{row['NV_std']:>6.2f}{nv_diff:>8}"
            f"{row['TD']:>10.2f}{row['TD_std']:>8.2f}{gap:>8}"
            f"{row['OnTime']:>7.1f}{row['Time']:>7.1f}s"
        )
    print("-" * 86)


def build_default_split(cfg: Optional[Config] = None) -> Tuple[List[Inst], List[Inst]]:
    cfg = cfg or Config()
    datasets = load_datasets(cfg.data_path)
    return datasets["rc1"], datasets["rc2"]


__all__ = [
    "ALNSSolver",
    "BKS",
    "Config",
    "DEVICE",
    "Inst",
    "MODES",
    "PlateauHybridSolver",
    "Plan",
    "build_default_split",
    "build_greedy",
    "default_data_path",
    "default_output_dir",
    "load_datasets",
    "print_summary_table",
    "run_benchmark",
    "run_instance",
]
