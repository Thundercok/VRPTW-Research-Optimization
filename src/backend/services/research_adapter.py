"""Adapter: convert web JobRequest <-> research `Inst`/`Plan`.

Units: distance in km (approx via local Mercator from lat/lng), time in same
scale so the ALNS solver can reuse `inst.dist` for both. Users provide time
windows directly in that common unit (default: minutes assuming ~60 km/h, i.e.
"1 km ~= 1 minute"). This is a simplification sufficient for web demo.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

_ROOT = Path(__file__).resolve().parents[3]
for candidate in (_ROOT, _ROOT / "docs"):
    if candidate.exists():
        sys.path.insert(0, str(candidate))
from models.schemas import Point  # noqa: E402
from vrptw_clean import Inst, Plan  # noqa: E402

DEG_TO_KM = 111.0


def _project(points: list[Point]) -> np.ndarray:
    lats = np.array([p.lat for p in points], dtype=np.float64)
    lngs = np.array([p.lng for p in points], dtype=np.float64)
    lat0 = float(lats.mean())
    x = (lngs - lngs.mean()) * DEG_TO_KM * math.cos(math.radians(lat0))
    y = (lats - lat0) * DEG_TO_KM
    return np.stack([x, y], axis=1)


def build_inst(points: list[Point], capacity: int, name: str = "WebInput") -> Inst:
    """Build an `Inst` from web points. Index 0 must be depot."""
    if len(points) < 2:
        raise ValueError("Need at least depot + 1 customer")

    xy = _project(points)
    n = len(points)
    data = np.zeros((n, 7), dtype=np.float64)
    for i, p in enumerate(points):
        data[i, 0] = i
        data[i, 1] = xy[i, 0]
        data[i, 2] = xy[i, 1]
        data[i, 3] = max(0, int(p.demand))
        data[i, 4] = max(0.0, float(p.ready))
        data[i, 5] = max(data[i, 4] + 1.0, float(p.due))
        data[i, 6] = max(0.0, float(p.service))

    inst = Inst({"name": name, "capacity": float(capacity), "data": data})
    return inst


def plan_to_payload(
    plan: Plan,
    points: list[Point],
    runtime_sec: float,
) -> dict[str, Any]:
    depot = points[0]
    routes_out: list[dict[str, Any]] = []
    total_km = 0.0

    # Build a simple distance matrix from projected coordinates for schedule computation
    xy = _project(points)
    n = len(points)
    dist = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        for j in range(n):
            dist[i, j] = float(np.sqrt((xy[i, 0] - xy[j, 0]) ** 2 + (xy[i, 1] - xy[j, 1]) ** 2))

    for vid, route in enumerate(plan.routes, start=1):
        chain_idx = [0, *route, 0]
        path = [[points[i].lat, points[i].lng] for i in chain_idx]
        stops = [int(points[i].id) if points[i].id is not None else int(i) for i in route]
        dist_km = 0.0
        for a, b in zip(chain_idx[:-1], chain_idx[1:], strict=True):
            dist_km += _haversine(points[a].lat, points[a].lng, points[b].lat, points[b].lng)
        load = sum(int(points[i].demand) for i in route)
        total_km += dist_km

        # Compute schedule for Gantt chart
        schedule: list[dict[str, Any]] = []
        current_time = 0.0
        prev = 0
        for node in route:
            travel = dist[prev, node]
            arrival = current_time + travel
            ready = float(points[node].ready)
            service_start = max(arrival, ready)
            wait = max(0.0, ready - arrival)
            service_dur = float(points[node].service)
            departure = service_start + service_dur
            schedule.append({
                "customer_id": int(points[node].id) if points[node].id is not None else int(node),
                "name": getattr(points[node], "name", "") or f"Stop-{node}",
                "arrival": round(arrival, 2),
                "wait": round(wait, 2),
                "service_start": round(service_start, 2),
                "service_duration": round(service_dur, 2),
                "departure": round(departure, 2),
            })
            current_time = departure
            prev = node
        # Return to depot
        return_travel = dist[prev, 0]
        return_arrival = current_time + return_travel
        schedule.append({
            "customer_id": 0,
            "name": getattr(points[0], "name", "") or "Depot",
            "arrival": round(return_arrival, 2),
            "wait": 0,
            "service_start": round(return_arrival, 2),
            "service_duration": 0,
            "departure": round(return_arrival, 2),
        })

        routes_out.append(
            {
                "vehicle_id": vid,
                "distance_km": dist_km,
                "load": load,
                "path": path,
                "stops": stops,
                "schedule": schedule,
            }
        )

    _ = depot  # unused but documents intent (chain starts and ends at depot)
    return {
        "runtime_sec": runtime_sec,
        "total_distance_km": total_km,
        "vehicles_used": len(routes_out),
        "routes": routes_out,
    }


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))
