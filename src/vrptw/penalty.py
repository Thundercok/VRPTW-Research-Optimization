from __future__ import annotations
import numpy as np

class PenaltyManager:
    def __init__(self, inst):
        self.inst = inst
        # Initial values: alpha_q (capacity) and alpha_tw (time window)
        # Adjusted by instance characteristics
        self.alpha_q = 10.0
        self.alpha_tw = 1.0
        
        self.cap_history = []
        self.tw_history = []
        
    def penalized_cost(self, plan) -> float:
        cap_viol = plan.violation_capacity
        tw_viol = plan.violation_tw
        return plan.cost + self.alpha_q * cap_viol + self.alpha_tw * tw_viol

    def record_solution(self, plan) -> None:
        cap_ok = plan.violation_capacity < 1e-6
        tw_ok = plan.violation_tw < 1e-6
        self.cap_history.append(cap_ok)
        self.tw_history.append(tw_ok)
        if len(self.cap_history) > 100:
            self.cap_history.pop(0)
        if len(self.tw_history) > 100:
            self.tw_history.pop(0)
            
    def update_penalties(self) -> None:
        if len(self.cap_history) < 10:
            return
        
        cap_infeasible_rate = sum(1 for ok in self.cap_history if not ok) / len(self.cap_history)
        tw_infeasible_rate = sum(1 for ok in self.tw_history if not ok) / len(self.tw_history)
        
        # Self-adjusting capacity penalty
        if cap_infeasible_rate > 0.50:
            self.alpha_q = min(10000.0, self.alpha_q * 2.0)
        elif cap_infeasible_rate < 0.10:
            self.alpha_q = max(0.01, self.alpha_q / 2.0)
            
        # Self-adjusting time window penalty
        if tw_infeasible_rate > 0.50:
            self.alpha_tw = min(10000.0, self.alpha_tw * 2.0)
        elif tw_infeasible_rate < 0.10:
            self.alpha_tw = max(0.01, self.alpha_tw / 2.0)


def eliminate_route_infeasible(plan, penalty_manager: PenaltyManager):
    """
    Greedily eliminates the smallest route in the plan (the one with the fewest customers)
    and distributes its customers into the remaining routes at the positions that minimize
    the increase in penalized cost.
    """
    from .core import Plan
    inst = plan.inst
    routes = [r[:] for r in plan.routes]
    if len(routes) <= 1:
        return plan.copy()
    
    # Find the index of the route with the fewest customers
    route_idx = min(range(len(routes)), key=lambda i: len(routes[i]))
    removed_customers = routes.pop(route_idx)
    
    # Create a plan with the remaining routes
    new_plan = Plan(routes, inst, plan.algo)
    
    # Insert each removed customer into the best position
    for cust in removed_customers:
        best_plan = None
        best_cost = float("inf")
        
        # Try inserting cust at every position of every route
        for r_idx in range(len(new_plan.routes)):
            for pos in range(len(new_plan.routes[r_idx]) + 1):
                # Create a copy of the routes and insert the customer
                temp_routes = [r[:] for r in new_plan.routes]
                temp_routes[r_idx].insert(pos, cust)
                temp_plan = Plan(temp_routes, inst, plan.algo)
                
                cost = penalty_manager.penalized_cost(temp_plan)
                if cost < best_cost:
                    best_cost = cost
                    best_plan = temp_plan
                    
        if best_plan is not None:
            new_plan = best_plan
            
    return new_plan


def eliminate_two_routes_infeasible(plan, penalty_manager: PenaltyManager):
    """
    Eliminates the two smallest routes simultaneously and redistributes
    all their customers into remaining routes via penalized insertion.
    More powerful than single-route eliminate when NV is near BKS.
    """
    from .core import Plan
    inst = plan.inst
    routes = [r[:] for r in plan.routes]
    if len(routes) <= 2:
        return plan.copy()
    
    # Find two smallest routes by customer count
    sorted_idx = sorted(range(len(routes)), key=lambda i: len(routes[i]))
    idx1, idx2 = sorted_idx[0], sorted_idx[1]
    
    # Remove both (higher index first to avoid index shift)
    removed_customers = routes[max(idx1, idx2)] + routes[min(idx1, idx2)]
    for i in sorted([idx1, idx2], reverse=True):
        routes.pop(i)
        
    if not routes:
        return plan.copy()
        
    # Create a plan with the remaining routes
    new_plan = Plan(routes, inst, plan.algo)
    
    # Redistribute all removed customers via penalized insertion
    for cust in removed_customers:
        best_plan = None
        best_cost = float("inf")
        
        # Try inserting cust at every position of every route
        for r_idx in range(len(new_plan.routes)):
            for pos in range(len(new_plan.routes[r_idx]) + 1):
                temp_routes = [r[:] for r in new_plan.routes]
                temp_routes[r_idx].insert(pos, cust)
                temp_plan = Plan(temp_routes, inst, plan.algo)
                
                cost = penalty_manager.penalized_cost(temp_plan)
                if cost < best_cost:
                    best_cost = cost
                    best_plan = temp_plan
                    
        if best_plan is not None:
            new_plan = best_plan
            
    return new_plan

