from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


def _data_dirs() -> list[Path]:
    """Return candidate directories to search for Solomon .txt files, in priority order."""
    dirs: list[Path] = []
    env = os.environ.get("VRPTW_DATA_DIR")
    if env:
        p = Path(env)
        if p.exists():
            dirs.append(p)
    project_root = Path(__file__).resolve().parents[3]
    dirs.append(project_root / "data" / "solomon")
    dirs.append(project_root / "data")
    return dirs


def _find_solomon_file(name: str) -> Path | None:
    """Find a Solomon .txt file by name across all candidate directories."""
    filename = f"{name}.txt"
    for d in _data_dirs():
        candidate = d / filename
        if candidate.exists():
            return candidate
    return None


def _to_lat_lng(x: float, y: float) -> tuple[float, float]:
    # Project Solomon XY coordinates into a stable local map window for visualization.
    lat = 10.55 + y * 0.004
    lng = 106.55 + x * 0.004
    return round(lat, 6), round(lng, 6)


# --- Built-in synthetic instance ---------------------------------------------------
# A 12-customer mini benchmark centred on Ho Chi Minh City. Ships in-process so the
# demo always has something to load, even before users run scripts/fetch_solomon.py.
# Demand/time-window scale mirrors a small Solomon RC1 instance so the solver does
# not need to be retuned. Distance and time use the same unit (~1 km <-> 1 unit).
_DEMO_FLEET = {"vehicles": 4, "capacity": 80}
_DEMO_NAMES = [
    "Saigon Central Depot", "Ben Thanh Market", "Notre-Dame Cathedral",
    "Tan Dinh Market", "Independence Palace", "Pham Ngu Lao Hostel",
    "Cho Lon Wholesale", "Phu My Hung Office", "An Phu Logistics Park",
    "Thao Dien Studios", "Phu Nhuan Pharmacy", "Tan Binh Cargo", "Go Vap Warehouse",
]
_DEMO_RAW: list[tuple[float, float, int, int, int, int]] = [
    # (lat, lng, demand, ready, due, service)
    (10.7769, 106.7009, 0, 0, 240, 0),     # Depot 0
    (10.7723, 106.6985, 8, 0, 90, 10),
    (10.7798, 106.6991, 6, 30, 120, 10),
    (10.7886, 106.6904, 9, 20, 110, 10),
    (10.7765, 106.6951, 7, 40, 140, 10),
    (10.7670, 106.6932, 5, 0, 80, 10),
    (10.7530, 106.6510, 12, 60, 180, 15),
    (10.7281, 106.7191, 10, 70, 200, 12),
    (10.7995, 106.7375, 11, 50, 170, 12),
    (10.8014, 106.7308, 7, 30, 150, 10),
    (10.7969, 106.6800, 6, 20, 130, 10),
    (10.7976, 106.6500, 9, 40, 160, 12),
    (10.8400, 106.6650, 8, 60, 220, 12),
]


def _builtin_demo() -> dict[str, Any]:
    customers: list[dict[str, Any]] = []
    for idx, (lat, lng, demand, ready, due, service) in enumerate(_DEMO_RAW):
        customers.append(
            {
                "id": idx,
                "name": _DEMO_NAMES[idx] if idx < len(_DEMO_NAMES) else f"DEMO-{idx}",
                "address": _DEMO_NAMES[idx] if idx < len(_DEMO_NAMES) else f"Demo customer {idx}",
                "lat": lat,
                "lng": lng,
                "demand": demand,
                "ready": float(ready),
                "due": float(due),
                "service": float(service),
                "isDepot": idx == 0,
            }
        )
    return {
        "dataset": "demo",
        "fleet": dict(_DEMO_FLEET),
        "customers": customers,
        "_builtin": True,
    }


def _is_builtin(name: str) -> bool:
    return name.strip().lower() in {"demo", "builtin", "sample"}


def load_solomon_dataset(name: str = "demo") -> dict[str, Any]:
    raw_name = (name or "demo").strip().lower()

    if _is_builtin(raw_name):
        return _builtin_demo()

    if not re.fullmatch(r"[a-z]+\d{3}", raw_name):
        raise ValueError("Dataset name must look like c101, r101, rc101, or 'demo'")

    file_path = _find_solomon_file(raw_name)
    if file_path is None:
        raise FileNotFoundError(f"Solomon file not found: {raw_name}.txt")

    lines = file_path.read_text(encoding="utf-8").splitlines()
    header_idx = next((i for i, line in enumerate(lines) if "CUST NO." in line and "XCOORD." in line), -1)
    if header_idx < 0:
        raise ValueError(f"Invalid Solomon file format: {raw_name}.txt")

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
    for raw in lines[header_idx + 1:]:
        m = row_re.match(raw)
        if not m:
            continue

        cust_id = int(m.group(1))
        x = float(m.group(2))
        y = float(m.group(3))
        demand = int(float(m.group(4)))
        ready = float(m.group(5))
        due = float(m.group(6))
        service = float(m.group(7))
        lat, lng = _to_lat_lng(x, y)

        customers.append(
            {
                "id": cust_id,
                "name": "Depot" if cust_id == 0 else f"{raw_name.upper()}-{cust_id}",
                "address": f"Solomon {raw_name.upper()} point {cust_id}",
                "lat": lat,
                "lng": lng,
                "demand": demand,
                "ready": ready,
                "due": due,
                "service": service,
                "isDepot": cust_id == 0,
            }
        )

    if len(customers) < 2:
        raise ValueError(f"No valid customer rows found in {raw_name}.txt")

    customers.sort(key=lambda item: int(item["id"]))
    return {
        "dataset": raw_name,
        "fleet": {"vehicles": vehicles, "capacity": capacity},
        "customers": customers,
    }


def list_solomon_datasets() -> list[dict[str, Any]]:
    """Discover all available Solomon .txt files across candidate directories."""
    seen: set[str] = set()
    items: list[dict[str, Any]] = []

    # Always include the built-in demo
    items.append({"name": "demo", "label": "Demo (12 customers, HCMC)", "builtin": True})
    seen.add("demo")

    pattern = re.compile(r"^([a-z]+\d{3})\.txt$")
    for d in _data_dirs():
        if not d.exists():
            continue
        for f in sorted(d.iterdir()):
            if not f.is_file():
                continue
            m = pattern.match(f.name.lower())
            if not m:
                continue
            name = m.group(1)
            if name in seen:
                continue
            seen.add(name)
            items.append({"name": name, "label": name.upper(), "builtin": False})

    return items
