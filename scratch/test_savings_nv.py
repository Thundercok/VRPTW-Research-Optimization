import sys
import os
import random
import numpy as np

sys.path.insert(0, "src")

from vrptw import Config, load_datasets
from vrptw.core import _check_route

# Load dataset
datasets = load_datasets("data/Solomon")
inst = None
for g, insts in datasets.items():
    for i in insts:
        if i.name == "RC101":
            inst = i
            break

if inst is None:
    print("Instance RC101 not found!")
    sys.exit(1)

print(f"Loaded instance: {inst.name}")

n_runs = 100
nv_counts = {}

for run in range(n_runs):
    # savings computation
    savings = []
    for i in range(1, inst.n + 1):
        for j in range(i + 1, inst.n + 1):
            s = float(inst.dist[0, i] + inst.dist[0, j] - inst.dist[i, j])
            if run > 0:
                s *= 1.0 + (random.random() - 0.5) * 0.08 * run
            savings.append((s, i, j))
    savings.sort(key=lambda x: -x[0])

    routes = [[i] for i in range(inst.n + 1)]
    loads = [0.0] + [float(inst.demands[i]) for i in range(1, inst.n + 1)]
    which_route = {i: i for i in range(1, inst.n + 1)}

    for _, i, j in savings:
        ri = which_route.get(i)
        rj = which_route.get(j)
        if ri is None or rj is None or ri == rj:
            continue
        r1 = routes[ri]
        r2 = routes[rj]
        if not r1 or not r2:
            continue
        if loads[ri] + loads[rj] > inst.capacity:
            continue

        merged = None
        for a, b in (
            (r1, r2),
            (r1[::-1], r2),
            (r1, r2[::-1]),
            (r1[::-1], r2[::-1]),
        ):
            candidate = a + b
            if _check_route(candidate, inst):
                merged = candidate
                break

        if merged is None:
            continue

        routes[ri] = merged
        loads[ri] += loads[rj]
        routes[rj] = []
        loads[rj] = 0.0
        for c in r2:
            which_route[c] = ri

    non_empty = [r for idx, r in enumerate(routes) if idx > 0 and r]
    nv = len(non_empty)
    nv_counts[nv] = nv_counts.get(nv, 0) + 1

print("\n--- Clarke-Wright Savings Vehicle Count Distribution ---")
for nv, count in sorted(nv_counts.items()):
    print(f"nv={nv}: {count} runs")
