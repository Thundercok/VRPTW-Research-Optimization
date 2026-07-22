import sys
import os

# Ensure the vrptw package is importable
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from vrptw import load_datasets, Config
from vrptw.heuristics import build_greedy
from vrptw.local_search import _ejection_chain_eliminate, _try_chain_elimination
from vrptw.core import Plan

def main():
    print("=== EJECTION CHAINS DIAGNOSTIC ===")
    
    # Load Solomon instances
    data_path = "data/Solomon"
    print(f"Loading Solomon instances from {data_path}...")
    datasets = load_datasets(data_path)
    
    # Let's find RC201 (or another hard instance)
    inst = None
    for group, insts in datasets.items():
        for i in insts:
            if i.name.upper() == "RC201":
                inst = i
                break
        if inst:
            break
            
    if not inst:
        print("Error: RC201 not found.")
        sys.exit(1)
        
    print(f"Loaded instance: {inst.name} (Customers: {inst.n}, Capacity: {inst.capacity})")
    
    # Build a greedy plan
    plan = build_greedy(inst, "ALNS-Base")
    print(f"Greedy initial plan: NV={plan.nv}, TD={plan.cost:.2f}, Feasible={plan.feasible}")
    
    # Run ejection chain with max_depth=3
    print("\n--- Running ejection chain with max_depth=3 ---")
    res_depth_3 = _ejection_chain_eliminate(plan, beam_width=8, max_depth=3)
    if res_depth_3:
        print(f"Success! Eliminated a route. New NV={res_depth_3.nv}, TD={res_depth_3.cost:.2f}, Feasible={res_depth_3.feasible}")
    else:
        print("Failed to eliminate a route at depth 3.")
        
    # Run ejection chain with max_depth=6
    print("\n--- Running ejection chain with max_depth=6 ---")
    res_depth_6 = _ejection_chain_eliminate(plan, beam_width=8, max_depth=6)
    if res_depth_6:
        print(f"Success! Eliminated a route. New NV={res_depth_6.nv}, TD={res_depth_6.cost:.2f}, Feasible={res_depth_6.feasible}")
    else:
        print("Failed to eliminate a route at depth 6.")

    print("\n=== All basic checks completed successfully! ===")

if __name__ == "__main__":
    main()
