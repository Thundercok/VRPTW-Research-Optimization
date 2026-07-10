import asyncio
import logging
from typing import Any
import httpx
from models.schemas import MatrixPoint
from services.distance_service import distance_km

logger = logging.getLogger(__name__)

OSRM_HOSTS = [
    "https://router.project-osrm.org",
    "https://routing.openstreetmap.de/routed-car"
]


async def calculate_matrix(points: list[MatrixPoint]) -> dict[str, Any]:
    if len(points) < 2:
        return {"matrix": [[0.0]], "provider": "none"}

    coords = ";".join(f"{p.lng},{p.lat}" for p in points)

    for host in OSRM_HOSTS:
        url = f"{host}/table/v1/driving/{coords}?annotations=distance"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    matrix_km = [[(v or 0.0) / 1000 for v in row] for row in data.get("distances", [])]
                    if matrix_km and len(matrix_km) == len(points):
                        provider_name = host.split("//")[1].split(".")[0]
                        return {"matrix": matrix_km, "provider": f"osrm-{provider_name}"}
        except Exception as e:
            logger.warning("OSRM host %s matrix table query failed: %s", host, e)

    # Fallback to haversine if all hosts fail
    geo_points = [(p.lat, p.lng) for p in points]
    fallback: list[list[float]] = []
    for i in geo_points:
        row: list[float] = []
        for j in geo_points:
            row.append(distance_km(i, j))
        fallback.append(row)
    return {"matrix": fallback, "provider": "haversine"}


async def fetch_road_path(path: list[list[float]], semaphore: asyncio.Semaphore | None = None) -> list[list[float]]:
    """Query OSRM for the exact driving coordinates along the given path sequence."""
    if len(path) <= 2:  # Depot-to-depot or empty route, skip OSRM query
        return path

    if semaphore:
        async with semaphore:
            await asyncio.sleep(0.18)  # Polite gap between queries to prevent OSRM rate limits
            return await _fetch_road_path_raw(path)
    return await _fetch_road_path_raw(path)


async def _fetch_road_path_raw(path: list[list[float]]) -> list[list[float]]:
    coords = ";".join(f"{p[1]},{p[0]}" for p in path)  # OSRM expects lng,lat
    
    for host in OSRM_HOSTS:
        url = f"{host}/route/v1/driving/{coords}?overview=full&geometries=geojson"
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == "Ok" and data.get("routes"):
                        geo = data["routes"][0]["geometry"]["coordinates"]
                        # geo coordinates are [lng, lat] -> translate to [lat, lng]
                        return [[c[1], c[0]] for c in geo]
        except Exception as e:
            logger.warning("OSRM host %s route geometry query failed: %s", host, e)
            
    return path
