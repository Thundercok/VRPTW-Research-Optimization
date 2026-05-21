from __future__ import annotations
import math
import numpy as np
from typing import Dict, List, Optional
import glob
import os
from .core import Inst

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
    for group in ("c1", "c2", "r1", "r2", "rc1", "rc2"):
        pat_lower = os.path.join(base_path, f"{group.lower()}*.txt")
        pat_upper = os.path.join(base_path, f"{group.upper()}*.txt")
        files = sorted(list(set(glob.glob(pat_lower) + glob.glob(pat_upper))))
        insts: List[Inst] = []
        for path in files:
            with open(path, encoding="utf-8") as fh:
                lines = fh.readlines()
            name     = lines[0].strip()
            capacity = float(lines[4].strip().split()[1])
            rows     = [list(map(float, ln.split())) for ln in lines[9:] if ln.strip()]
            insts.append(Inst({"name": name, "capacity": capacity, "data": np.array(rows)}))
        if insts:
            datasets[group] = insts
    return datasets

