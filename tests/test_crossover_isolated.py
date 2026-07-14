import os
import numpy as np
from vrptw.core import Inst, Plan
from vrptw.rl import EliteArchive
from vrptw.heuristics import build_greedy

def load_inst_rc202() -> Inst:
    file_path = 'data/Solomon/RC202.txt'
    assert os.path.exists(file_path), f"Solomon file not found at {file_path}"
    with open(file_path, encoding="utf-8") as fh:
        lines = fh.readlines()
    name = lines[0].strip()
    capacity = float(lines[4].strip().split()[1])
    rows = [list(map(float, ln.split())) for ln in lines[9:] if ln.strip()]
    return Inst({"name": name, "capacity": capacity, "data": np.array(rows)})

def test_crossover_complete_plans():
    inst = load_inst_rc202()
    arch = EliteArchive(k=5)
    
    # Generate two distinct plans
    p1 = build_greedy(inst, heatmap=None, gnn_strength=0.0)
    # Generate a second plan by slightly shuffling/shifting routes to make it distinct
    routes2 = p1.routes[::-1]
    p2 = Plan(routes2, inst, "synth")
    
    key = inst.name
    bucket = arch._plans.setdefault(key, [])
    bucket.append(p1.copy())
    bucket.append(p2.copy())
    
    child = arch.crossover(inst.name)
    assert child is not None
    assert child.feasible
    assert len(child.routes) > 0

def test_crossover_missing_customers_sorting():
    inst = load_inst_rc202()
    arch = EliteArchive(k=5)
    
    p1 = build_greedy(inst)
    
    # Dynamically select 4 customers from the second half of p1 routes to drop
    second_half_customers = [c for r in p1.routes[len(p1.routes)//2:] for c in r]
    assert len(second_half_customers) >= 4
    drop_set = set(second_half_customers[:4])
    
    routes2 = [[c for c in r if c not in drop_set] for r in p1.routes]
    p2 = Plan(routes2, inst, "synth")
    
    # We temporarily bypass the feasibility check on archive update to insert p2
    key = inst.name
    bucket = arch._plans.setdefault(key, [])
    bucket.append(p1.copy())
    bucket.append(p2.copy())
    
    child = arch.crossover(inst.name)
    assert child is not None
    
    # Locate the leftover route containing the missing customers
    leftover_route = None
    for r in child.routes:
        if any(c in drop_set for c in r):
            leftover_route = r
            break
            
    assert leftover_route is not None, "Leftover route containing missing customers must exist"
    # The missing customers must be exactly the ones we dropped
    missing_found = [c for c in leftover_route if c in drop_set]
    assert set(missing_found) == drop_set
    
    # Assert they are sorted chronologically by inst.ready_times
    ready_times = [inst.ready_times[c] for c in missing_found]
    assert ready_times == sorted(ready_times), f"Missing customers in the leftover route must be sorted by ready times: {missing_found} (ready_times: {ready_times})"
