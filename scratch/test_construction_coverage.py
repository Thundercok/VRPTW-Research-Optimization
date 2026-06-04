import sys
import os
import random

sys.path.insert(0, "src")

from vrptw import Config, load_datasets
from vrptw.core import _check_route
from vrptw.heuristics import _best_insert_position

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

target_nv = 14
n_trials = 35

customers = list(range(1, inst.n + 1))
tw_sorted = sorted(customers, key=lambda n: (inst.ready_times[n] + inst.due_times[n]) / 2.0)
step = max(1, inst.n // target_nv)

unassigned_counts = []

for trial in range(n_trials):
    offset = trial % step
    seeds = []
    seen_seeds = set()
    for i in range(target_nv):
        idx = min(i * step + offset, inst.n - 1)
        s = tw_sorted[idx]
        if s not in seen_seeds:
            seeds.append(s)
            seen_seeds.add(s)

    route_lists = [[s] for s in seeds]
    route_loads = [float(inst.demands[s]) for s in seeds]

    unassigned = [c for c in customers if c not in seeds]
    unassigned.sort(key=lambda n: inst.due_times[n] - inst.ready_times[n])

    dropped = []
    for c in unassigned:
        best_delta, best_ri, best_pos = float("inf"), None, None
        for ri, route in enumerate(route_lists):
            if route_loads[ri] + inst.demands[c] > inst.capacity:
                continue
            delta, pos = _best_insert_position(c, route, inst)
            if pos is not None and delta < best_delta:
                best_delta, best_ri, best_pos = delta, ri, pos
        if best_ri is not None:
            route_lists[best_ri].insert(best_pos, c)
            route_loads[best_ri] += inst.demands[c]
        else:
            dropped.append(c)

    placed_count = sum(len(r) for r in route_lists)
    unassigned_counts.append(len(dropped))

print("\n--- NV-Targeted Construction Customer Coverage (target_nv=14) ---")
print(f"Number of trials: {n_trials}")
print(f"Min dropped customers: {min(unassigned_counts)}")
print(f"Max dropped customers: {max(unassigned_counts)}")
print(f"Avg dropped customers: {sum(unassigned_counts) / len(unassigned_counts):.1f}")
print(f"Raw dropped counts: {unassigned_counts}")
