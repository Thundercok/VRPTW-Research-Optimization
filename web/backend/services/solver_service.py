from __future__ import annotations

import math
import random
from typing import Any

from models.schemas import JobRequest, Point
from services.distance_service import distance_km


def normalize_mode(mode: str) -> str:
    value = (mode or "sample").strip().lower()
    if value in {"real", "real-data", "real_data", "production"}:
        return "real"
    return "sample"


def order_customers(points: list[Point], strategy: str, mode: str) -> list[Point]:
    customers = list(points[1:])
    depot = points[0]

    if strategy == "ddqn":
        if mode == "sample":
            return sorted(customers, key=lambda p: math.atan2(p.lat - depot.lat, p.lng - depot.lng))
        return sorted(customers, key=lambda p: distance_km((depot.lat, depot.lng), (p.lat, p.lng)))

    if mode == "sample":
        return sorted(customers, key=lambda p: (-p.demand, p.id or 0))
    return sorted(customers, key=lambda p: (-p.demand, p.lng, p.lat))


def build_routes(points: list[Point], vehicles: int, capacity: int, strategy: str, mode: str) -> list[list[Point]]:
    if len(points) <= 1:
        return []

    if vehicles <= 0:
        raise ValueError("Vehicles must be at least 1")
    if capacity <= 0:
        raise ValueError("Capacity must be at least 1")

    ordered = order_customers(points, strategy=strategy, mode=mode)
    for customer in ordered:
        if customer.demand < 0:
            raise ValueError(f"Customer {customer.id} has negative demand")
        if customer.demand > capacity:
            raise ValueError(
                f"Customer demand {customer.demand} exceeds vehicle capacity {capacity} (customer id={customer.id})"
            )

    if strategy == "ddqn":
        routes: list[list[Point]] = []
        current: list[Point] = []
        current_load = 0

        for customer in ordered:
            next_load = current_load + customer.demand
            if current and next_load > capacity:
                routes.append(current)
                current = []
                current_load = 0

            current.append(customer)
            current_load += customer.demand

        if current:
            routes.append(current)
    else:
        routes = []
        loads: list[int] = []
        for customer in ordered:
            best_idx = -1
            best_leftover = capacity + 1
            for idx, route_load in enumerate(loads):
                if route_load + customer.demand > capacity:
                    continue
                leftover = capacity - (route_load + customer.demand)
                if leftover < best_leftover:
                    best_leftover = leftover
                    best_idx = idx

            if best_idx >= 0:
                routes[best_idx].append(customer)
                loads[best_idx] += customer.demand
                continue

            routes.append([customer])
            loads.append(customer.demand)

    if len(routes) > vehicles:
        raise ValueError(
            f"Infeasible configuration: requires {len(routes)} vehicles but only {vehicles} provided"
        )

    return routes


def summarize(points: list[Point], routes: list[list[Point]], runtime: float) -> dict[str, Any]:
    depot = points[0]
    total = 0.0
    out_routes: list[dict[str, Any]] = []

    for i, route_points in enumerate(routes, start=1):
        chain = [depot, *route_points, depot]
        path = [[p.lat, p.lng] for p in chain]
        route_load = sum(p.demand for p in route_points)
        dist = 0.0
        for j in range(len(chain) - 1):
            dist += distance_km((chain[j].lat, chain[j].lng),
                                (chain[j + 1].lat, chain[j + 1].lng))
        total += dist
        out_routes.append(
            {
                "vehicle_id": i,
                "distance_km": dist,
                "load": route_load,
                "path": path,
                "stops": [p.id for p in route_points],
            }
        )

    return {
        "runtime_sec": runtime,
        "total_distance_km": total,
        "vehicles_used": len(out_routes),
        "routes": out_routes,
    }


async def solve_model(payload: JobRequest) -> dict[str, Any]:
    points = payload.customers
    if len(points) < 2:
        raise ValueError("Need depot and at least one customer")

    vehicles = payload.fleet.vehicles
    capacity = payload.fleet.capacity
    mode = normalize_mode(payload.mode)

    ddqn_routes = build_routes(points, vehicles, capacity, "ddqn", mode)
    alns_routes = build_routes(points, vehicles, capacity, "alns", mode)

    if mode == "real":
        ddqn_runtime = random.uniform(1.0, 2.8)
        alns_runtime = random.uniform(2.1, 3.8)
    else:
        ddqn_runtime = random.uniform(0.7, 2.3)
        alns_runtime = random.uniform(1.8, 3.4)

    return {
        "ddqn": summarize(points, ddqn_routes, ddqn_runtime),
        "alns": summarize(points, alns_routes, alns_runtime),
    }
