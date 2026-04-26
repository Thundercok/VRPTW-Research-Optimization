from __future__ import annotations

from typing import Any

import httpx

from models.schemas import MatrixPoint
from services.distance_service import distance_km


async def calculate_matrix(points: list[MatrixPoint]) -> dict[str, Any]:
    if len(points) < 2:
        return {"matrix": [[0.0]], "provider": "none"}

    coords = ";".join(f"{p.lng},{p.lat}" for p in points)
    osrm = f"https://router.project-osrm.org/table/v1/driving/{coords}?annotations=distance"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(osrm)
            response.raise_for_status()
            data = response.json()
        matrix_km = [[(v or 0.0) / 1000 for v in row]
                     for row in data.get("distances", [])]
        return {"matrix": matrix_km, "provider": "osrm"}
    except Exception:
        geo_points = [(p.lat, p.lng) for p in points]
        fallback: list[list[float]] = []
        for i in geo_points:
            row: list[float] = []
            for j in geo_points:
                row.append(distance_km(i, j))
            fallback.append(row)
        return {"matrix": fallback, "provider": "haversine"}
