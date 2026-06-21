import sys
import os
import time
import numpy as np

sys.path.insert(0, os.path.abspath("src"))

from vrptw.core import Inst, Plan
from vrptw.config import Config

def load_solomon(path: str) -> Inst:
    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()
    name = lines[0].strip()
    capacity = float(lines[4].strip().split()[1])
    rows = [list(map(float, ln.split())) for ln in lines[9:] if ln.strip()]
    return Inst({"name": name, "capacity": capacity, "data": np.array(rows)})

def run_ortools(inst: Inst, limit: float, use_correct_cost: bool, strategy_name: str) -> tuple[Plan | None, float]:
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    
    scale = 100000
    n_nodes = inst.n + 1
    n_vehicles = inst.n
    manager = pywrapcp.RoutingIndexManager(n_nodes, n_vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)

    dist_mat = np.round(inst.dist * scale).astype(np.int64)
    serv_int = np.round(inst.service_times * scale).astype(np.int64)

    # Cost Matrix
    if use_correct_cost:
        cost_matrix = dist_mat.tolist()
    else:
        cost_matrix = (dist_mat + serv_int[:, None]).tolist()
        
    cost_idx = routing.RegisterTransitMatrix(cost_matrix)
    routing.SetArcCostEvaluatorOfAllVehicles(cost_idx)
    routing.SetFixedCostOfAllVehicles(int(100000 * scale))
        
    # Time Dimension
    transit_matrix = (dist_mat + serv_int[:, None]).tolist()
    transit_idx = routing.RegisterTransitMatrix(transit_matrix)
    
    demands_int = inst.demands.astype(int)
    def demand_cb(fi):
        return int(demands_int[manager.IndexToNode(fi)])

    demand_idx = routing.RegisterUnaryTransitCallback(demand_cb)
    routing.AddDimensionWithVehicleCapacity(demand_idx, 0, [int(inst.capacity)] * n_vehicles, True, "Capacity")
    routing.AddDimension(
        transit_idx, int(np.round(inst.horizon * scale)), int(np.round(inst.horizon * scale)), False, "Time"
    )
    time_dim = routing.GetDimensionOrDie("Time")
    for node in range(1, inst.n + 1):
        idx = manager.NodeToIndex(node)
        time_dim.CumulVar(idx).SetRange(
            int(np.round(inst.ready_times[node] * scale)), int(np.round(inst.due_times[node] * scale))
        )
    for v in range(n_vehicles):
        routing.AddVariableMinimizedByFinalizer(time_dim.CumulVar(routing.Start(v)))
        routing.AddVariableMinimizedByFinalizer(time_dim.CumulVar(routing.End(v)))
        
    params = pywrapcp.DefaultRoutingSearchParameters()
    strategy = getattr(routing_enums_pb2.FirstSolutionStrategy, strategy_name)
    params.first_solution_strategy = strategy
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds = int(limit)
    params.log_search = False
    
    t0 = time.time()
    solution = routing.SolveWithParameters(params)
    elapsed = time.time() - t0
    if not solution:
        return None, elapsed
        
    routes: list[list[int]] = []
    for v in range(n_vehicles):
        route: list[int] = []
        idx = routing.Start(v)
        while not routing.IsEnd(idx):
            node = manager.IndexToNode(idx)
            if node != 0:
                route.append(node)
            idx = solution.Value(routing.NextVar(idx))
        if route:
            routes.append(route)
    plan = Plan(routes, inst, "ortools")
    return plan, elapsed

def main():
    instances_names = ["RC101", "R101"]
    
    for name in instances_names:
        inst_path = f"data/Solomon/{name}.txt"
        if not os.path.exists(inst_path):
            inst_path = f"docs/data/Solomon/{name}.txt"
        if not os.path.exists(inst_path):
            inst_path = f"docs/data/Solomon/{name}.TXT"
            
        inst = load_solomon(inst_path)
        print(f"\n==================== Instance: {name} ====================")
        
        # 1. Default (Biased + PATH_CHEAPEST_ARC) - 15s
        plan_d, t_d = run_ortools(inst, 15.0, use_correct_cost=False, strategy_name="PATH_CHEAPEST_ARC")
        print(f"Default OR-Tools Configuration (15s):        NV={plan_d.nv if plan_d else 'F'}, TD={plan_d.cost if plan_d else 0.0:.2f} ({t_d:.1f}s)")
        
        # 2. Fair Configuration (Unbiased + LOCAL_CHEAPEST_INSERTION) - 15s
        plan_f15, t_f15 = run_ortools(inst, 15.0, use_correct_cost=True, strategy_name="LOCAL_CHEAPEST_INSERTION")
        print(f"Fair OR-Tools Configuration (15s):           NV={plan_f15.nv if plan_f15 else 'F'}, TD={plan_f15.cost if plan_f15 else 0.0:.2f} ({t_f15:.1f}s)")
        
        # 3. Fair Configuration (Unbiased + LOCAL_CHEAPEST_INSERTION) - 60s
        plan_f60, t_f60 = run_ortools(inst, 60.0, use_correct_cost=True, strategy_name="LOCAL_CHEAPEST_INSERTION")
        print(f"Fair OR-Tools Configuration (60s):           NV={plan_f60.nv if plan_f60 else 'F'}, TD={plan_f60.cost if plan_f60 else 0.0:.2f} ({t_f60:.1f}s)")
        
        # 4. Fair Configuration (Unbiased + LOCAL_CHEAPEST_INSERTION) - 120s
        plan_f120, t_f120 = run_ortools(inst, 120.0, use_correct_cost=True, strategy_name="LOCAL_CHEAPEST_INSERTION")
        print(f"Fair OR-Tools Configuration (120s):          NV={plan_f120.nv if plan_f120 else 'F'}, TD={plan_f120.cost if plan_f120 else 0.0:.2f} ({t_f120:.1f}s)")

if __name__ == "__main__":
    main()
