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

    for vid, route in enumerate(plan.routes, start=1):
        chain_idx = [0, *route, 0]
        path = [[points[i].lat, points[i].lng] for i in chain_idx]
        stops = [int(points[i].id) if points[i].id is not None else int(i) for i in route]
        dist_km = 0.0
        for a, b in zip(chain_idx[:-1], chain_idx[1:], strict=True):
            dist_km += _haversine(points[a].lat, points[a].lng, points[b].lat, points[b].lng)
        load = sum(int(points[i].demand) for i in route)
        total_km += dist_km
        routes_out.append(
            {
                "vehicle_id": vid,
                "distance_km": dist_km,
                "load": load,
                "path": path,
                "stops": stops,
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
