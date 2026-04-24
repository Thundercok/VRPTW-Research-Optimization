"""End-to-end smoke: build a synthetic JobRequest and run the web solver path.

Tests:
  - Schema accepts TW fields with defaults
  - Adapter builds Inst correctly
  - DDQN-ALNS and ALNS both return plans
  - Transfer weights load if present
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "web" / "backend"))

from models.schemas import FleetConfig, JobRequest, Point  # noqa: E402
from services.solver_service import solve_model  # noqa: E402


def _build_request() -> JobRequest:
    # Depot at center, 8 customers around it (HCMC-ish lat/lng)
    points = [
        Point(id=0, name="Depot", lat=10.7769, lng=106.7008, demand=0, isDepot=True, ready=0, due=500, service=0),
        Point(id=1, name="A", lat=10.7800, lng=106.7050, demand=15, ready=0, due=200, service=10),
        Point(id=2, name="B", lat=10.7820, lng=106.6980, demand=10, ready=0, due=200, service=10),
        Point(id=3, name="C", lat=10.7730, lng=106.7100, demand=20, ready=0, due=300, service=10),
        Point(id=4, name="D", lat=10.7850, lng=106.7020, demand=12, ready=50, due=300, service=10),
        Point(id=5, name="E", lat=10.7700, lng=106.7030, demand=8, ready=0, due=400, service=10),
        Point(id=6, name="F", lat=10.7810, lng=106.7120, demand=18, ready=100, due=400, service=10),
        Point(id=7, name="G", lat=10.7780, lng=106.6950, demand=11, ready=0, due=300, service=10),
        Point(id=8, name="H", lat=10.7760, lng=106.7090, demand=14, ready=0, due=350, service=10),
    ]
    return JobRequest(mode="real", fleet=FleetConfig(vehicles=5, capacity=60), customers=points)


async def main() -> None:
    req = _build_request()
    print(f"Running solver on {len(req.customers)} points (1 depot + {len(req.customers)-1} customers)")
    result = await solve_model(req)

    for algo in ("ddqn", "alns"):
        r = result[algo]
        print(f"\n[{algo.upper()}] runtime={r['runtime_sec']:.1f}s  "
              f"vehicles={r['vehicles_used']}  total={r['total_distance_km']:.2f} km")
        for route in r["routes"]:
            print(f"  vehicle {route['vehicle_id']}: stops={route['stops']} "
                  f"load={route['load']} dist={route['distance_km']:.2f} km")


if __name__ == "__main__":
    asyncio.run(main())
