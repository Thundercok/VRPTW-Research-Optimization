from __future__ import annotations

from typing import Any

import httpx


REVERSE_GEOCODE_CACHE: dict[tuple[float, float], dict[str, Any]] = {}


def _extract_short_address(data: dict[str, Any]) -> str:
    parts = data.get("address", {}) or {}
    house_no = str(parts.get("house_number", "")).strip()
    road = (
        parts.get("road")
        or parts.get("pedestrian")
        or parts.get("residential")
        or parts.get("hamlet")
        or parts.get("suburb")
        or ""
    )
    road = str(road).strip()
    if house_no and road:
        return f"{house_no} {road}"
    if road:
        return road
    return ""


async def geocode_address(q: str, limit: int) -> dict[str, Any]:
    headers = {"User-Agent": "vrptw-dashboard/1.0"}

    async with httpx.AsyncClient(timeout=8.0) as client:
        data = []
        try:
            nominatim_resp = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": q,
                    "format": "json",
                    "limit": str(limit),
                    "accept-language": "vi,en",
                    "countrycodes": "vn",
                },
                headers=headers,
            )
            nominatim_resp.raise_for_status()
            data = nominatim_resp.json()
        except httpx.HTTPError:
            try:
                mapsco_resp = await client.get(
                    "https://geocode.maps.co/search",
                    params={"q": f"{q}, Vietnam"},
                    headers=headers,
                )
                mapsco_resp.raise_for_status()
                data = (mapsco_resp.json() or [])[: max(1, int(limit))]
            except httpx.HTTPError:
                data = []

    items = [
        {
            "address": it.get("display_name", ""),
            "lat": float(it.get("lat", 0.0)),
            "lng": float(it.get("lon", 0.0)),
        }
        for it in data
    ]
    return {"items": items}


async def reverse_geocode_address(lat: float, lng: float) -> dict[str, Any]:
    cache_key = (round(float(lat), 6), round(float(lng), 6))
    cached = REVERSE_GEOCODE_CACHE.get(cache_key)
    if cached:
        return cached

    headers = {"User-Agent": "vrptw-dashboard/1.0"}

    async def fetch_nominatim(client: httpx.AsyncClient) -> dict[str, Any]:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": str(lat),
            "lon": str(lng),
            "format": "jsonv2",
            "addressdetails": "1",
            "accept-language": "vi,en",
        }
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()

    async def fetch_mapsco(client: httpx.AsyncClient) -> dict[str, Any]:
        url = "https://geocode.maps.co/reverse"
        params = {
            "lat": str(lat),
            "lon": str(lng),
        }
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()

    async def fetch_bigdatacloud(client: httpx.AsyncClient) -> dict[str, Any]:
        url = "https://api.bigdatacloud.net/data/reverse-geocode-client"
        params = {
            "latitude": str(lat),
            "longitude": str(lng),
            "localityLanguage": "vi",
        }
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

        locality = str(data.get("locality", "")).strip()
        city = str(data.get("city", "")).strip()
        region = str(data.get("principalSubdivision", "")).strip()
        country = str(data.get("countryName", "")).strip()
        pieces = [p for p in [locality, city, region, country] if p]
        display_name = ", ".join(pieces)

        return {
            "display_name": display_name,
            "address": {
                "suburb": locality,
            },
            "lat": data.get("latitude", lat),
            "lon": data.get("longitude", lng),
        }

    data: dict[str, Any] = {}
    async with httpx.AsyncClient(timeout=8.0) as client:
        try:
            data = await fetch_nominatim(client)
        except httpx.HTTPError:
            try:
                data = await fetch_mapsco(client)
            except httpx.HTTPError:
                try:
                    data = await fetch_bigdatacloud(client)
                except httpx.HTTPError:
                    data = {}

    short_address = _extract_short_address(data)

    payload = {
        "address": str(data.get("display_name", "")).strip(),
        "short_address": short_address,
        "lat": float(data.get("lat", lat) or lat),
        "lng": float(data.get("lon", lng) or lng),
    }
    REVERSE_GEOCODE_CACHE[cache_key] = payload
    return payload
