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

    async def fetch_nominatim(client: httpx.AsyncClient, query_str: str) -> list[dict[str, Any]]:
        try:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": query_str,
                    "format": "json",
                    "limit": str(limit),
                    "accept-language": "vi,en",
                    "countrycodes": "vn",
                },
                headers=headers,
            )
            if resp.status_code == 200:
                return resp.json() or []
        except Exception:
            pass
        return []

    async def fetch_mapsco(client: httpx.AsyncClient, query_str: str) -> list[dict[str, Any]]:
        try:
            resp = await client.get(
                "https://geocode.maps.co/search",
                params={"q": f"{query_str}, Vietnam"},
                headers=headers,
            )
            if resp.status_code == 200:
                return resp.json() or []
        except Exception:
            pass
        return []

    async with httpx.AsyncClient(timeout=8.0) as client:
        import re
        import logging
        logger = logging.getLogger("vrptw.geocoder")

        # Generate progressive search candidate variations
        candidates = [q]

        # Candidate 2: Strip house number prefix (e.g. "12 Nguyễn Huệ, Quận 1" -> "Nguyễn Huệ, Quận 1")
        cleaned_no_house = re.sub(r'^(?:số\s+)?\d+(?:\s*[\/\-]\s*\d+)?\s+', '', q, flags=re.IGNORECASE).strip()
        if cleaned_no_house and cleaned_no_house not in candidates:
            candidates.append(cleaned_no_house)

        # Candidate 3: Strip district sub-clauses (e.g. "12 Nguyễn Huệ, Quận 1" -> "12 Nguyễn Huệ")
        cleaned_no_district = re.sub(r'[,]?\s*(?:quận|q\.)\s*\d+\b', '', q, flags=re.IGNORECASE).strip()
        if cleaned_no_district and cleaned_no_district not in candidates:
            candidates.append(cleaned_no_district)

        # Candidate 4: Strip both house number and district (e.g. "12 Nguyễn Huệ, Quận 1" -> "Nguyễn Huệ")
        cleaned_both = re.sub(r'[,]?\s*(?:quận|q\.)\s*\d+\b', '', cleaned_no_house, flags=re.IGNORECASE).strip()
        if cleaned_both and cleaned_both not in candidates:
            candidates.append(cleaned_both)

        # Evaluate candidates sequentially
        data = []
        for cand in candidates:
            data = await fetch_nominatim(client, cand)
            if not data:
                data = await fetch_mapsco(client, cand)
            if data:
                logger.info("Geocoding success for [%s] using rewrite [%s]", q, cand)
                break

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
