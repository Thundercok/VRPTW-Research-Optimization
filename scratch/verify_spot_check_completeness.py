import os
import sys
import json

# Ensure the vrptw package is importable
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from vrptw import load_datasets
from vrptw.core import Plan

def check_plan(name, routes, inst, json_cost):
    print(f"\nVerifying plan for instance: {name}")
    
    # 1. Check customer coverage (1 to n must be visited exactly once)
    expected_customers = set(range(1, inst.n + 1))
    flat_routes = [node for r in routes for node in r]
    actual_customers = set(flat_routes)
    
    missing = expected_customers - actual_customers
    extra = actual_customers - expected_customers
    duplicates = [node for node in actual_customers if flat_routes.count(node) > 1]
    
    print(f"  Total customers: expected={inst.n}, actual={len(flat_routes)}")
    if missing:
        print(f"  ❌ MISSING CUSTOMERS: {missing}")
    if extra:
        print(f"  ❌ EXTRA/OUT-OF-BOUNDS CUSTOMERS: {extra}")
    if duplicates:
        print(f"  ❌ DUPLICATED CUSTOMERS: {duplicates}")
        
    if len(flat_routes) != inst.n or len(actual_customers) != inst.n or missing or extra or duplicates:
        print("  ❌ CUSTOMER COVERAGE CHECK FAILED!")
        return False
    else:
        print("  ✅ Customer coverage check passed.")
        
    # 2. Check time window and capacity constraints
    plan = Plan(routes, inst)
    feasible = plan.feasible
    
    # Calculate actual cost and check against JSON cost
    calculated_cost = plan.cost
    cost_matched = abs(calculated_cost - json_cost) < 1e-4
    
    print(f"  Plan feasibility: {feasible}")
    print(f"  Plan cost: calculated={calculated_cost:.4f}, json={json_cost:.4f} (Matched: {cost_matched})")
    
    if not feasible:
        print("  ❌ FEASIBILITY CHECK FAILED (time windows or capacity violated)!")
        return False
    if not cost_matched:
        print("  ❌ COST MISMATCH!")
        return False
        
    print("  ✅ All checks passed successfully.")
    return True

def main():
    print("=== SPOT-CHECK SOLUTIONS INDEPENDENT VERIFICATION ===")
    
    # Load Solomon instances
    data_path = "data/Solomon"
    datasets = load_datasets(data_path)
    insts_dict = {}
    for group, insts in datasets.items():
        for i in insts:
            insts_dict[i.name.upper()] = i
            
    folders = [
        "results/spot_check/ALNS-Base/elite_plans",
        "results/spot_check/Hybrid-DDQN/elite_plans",
    ]
    
    all_ok = True
    for folder in folders:
        if not os.path.exists(folder):
            print(f"Folder {folder} does not exist. Skipping.")
            continue
            
        print(f"\n--- Scanning folder: {folder} ---")
        for fname in os.listdir(folder):
            if not fname.endswith(".json"):
                continue
            path = os.path.join(folder, fname)
            with open(path) as f:
                data = json.load(f)
                
            inst_name = data["instance"].upper()
            routes = data["routes"]
            json_cost = data["cost"]
            
            if inst_name not in insts_dict:
                print(f"Error: instance {inst_name} not found in loaded datasets.")
                all_ok = False
                continue
                
            inst = insts_dict[inst_name]
            ok = check_plan(fname, routes, inst, json_cost)
            if not ok:
                all_ok = False
                
    if all_ok:
        print("\n🏆 SUCCESS: All spot-check plans are 100% correct, cover all customers exactly once, and have verified costs!")
    else:
        print("\n❌ FAILURE: One or more plans failed verification checks.")
        sys.exit(1)

if __name__ == "__main__":
    main()
