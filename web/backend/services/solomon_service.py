from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def _data_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "legacy" / "data"


def _to_lat_lng(x: float, y: float) -> tuple[float, float]:
    # Project Solomon XY coordinates into a stable local map window for visualization.
    lat = 10.55 + y * 0.004
    lng = 106.55 + x * 0.004
    return round(lat, 6), round(lng, 6)


def load_solomon_dataset(name: str = "c101") -> dict[str, Any]:
    dataset = (name or "c101").strip().lower()
    if not re.fullmatch(r"[a-z]\d{3}", dataset):
        raise ValueError("Dataset name must look like c101, r101, rc101")

    file_path = _data_dir() / f"{dataset}.txt"
    if not file_path.exists():
        raise FileNotFoundError(f"Solomon file not found: {dataset}.txt")

    lines = file_path.read_text(encoding="utf-8").splitlines()
    header_idx = next((i for i, line in enumerate(lines) if "CUST NO." in line and "XCOORD." in line), -1)
    if header_idx < 0:
        raise ValueError(f"Invalid Solomon file format: {dataset}.txt")

    vehicle_match = None
    for line in lines[:header_idx]:
        m = re.match(r"^\s*(\d+)\s+(\d+(?:\.\d+)?)\s*$", line)
        if m:
            vehicle_match = m

    vehicles = int(vehicle_match.group(1)) if vehicle_match else 25
    capacity = int(float(vehicle_match.group(2))) if vehicle_match else 200

    row_re = re.compile(
        r"^\s*(\d+)\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+"
        r"(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*$"
    )

    customers: list[dict[str, Any]] = []
    for raw in lines[header_idx + 1 :]:
        m = row_re.match(raw)
        if not m:
            continue

        cust_id = int(m.group(1))
        x = float(m.group(2))
        y = float(m.group(3))
        demand = int(float(m.group(4)))
        lat, lng = _to_lat_lng(x, y)

        customers.append(
            {
                "id": cust_id,
                "name": "Depot" if cust_id == 0 else f"{dataset.upper()}-{cust_id}",
                "address": f"Solomon {dataset.upper()} point {cust_id}",
                "lat": lat,
                "lng": lng,
                "demand": demand,
                "isDepot": cust_id == 0,
            }
        )

    if len(customers) < 2:
        raise ValueError(f"No valid customer rows found in {dataset}.txt")

    customers.sort(key=lambda item: int(item["id"]))
    return {
        "dataset": dataset,
        "fleet": {"vehicles": vehicles, "capacity": capacity},
        "customers": customers,
    }
