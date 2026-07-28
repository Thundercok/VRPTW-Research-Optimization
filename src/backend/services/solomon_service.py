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
    # The checked-in directory is `data/Solomon`; the lowercase spelling only
    # resolves on case-insensitive filesystems, so both must be listed or every
    # dataset lookup 404s once deployed on Linux.
    dirs.append(project_root / "data" / "Solomon")
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


# Affine projection of Solomon XY into a stable local map window for
# visualization. Kept invertible so `to_inst_payload` can recover the planar
# coordinates the solver needs.
_LAT_ORIGIN = 10.55
_LNG_ORIGIN = 106.55
_XY_SCALE = 0.004


def _to_lat_lng(x: float, y: float) -> tuple[float, float]:
    lat = _LAT_ORIGIN + y * _XY_SCALE
    lng = _LNG_ORIGIN + x * _XY_SCALE
    return round(lat, 6), round(lng, 6)


def to_inst_payload(dataset: dict[str, Any]) -> dict[str, Any]:
    """Convert a :func:`load_solomon_dataset` payload into the ``{name, capacity,
    data}`` shape ``vrptw.Inst`` expects.

    ``load_solomon_dataset`` returns a display-oriented payload (lat/lng for the
    map, customers as dicts); ``Inst`` wants an ``(n+1, 7)`` array of planar
    Solomon coordinates. Passing the former straight to ``Inst`` raises
    ``KeyError: 'name'``, so every caller must go through this adapter.
    """
    import numpy as np

    customers = sorted(dataset["customers"], key=lambda c: int(c["id"]))
    if len(customers) < 2:
        raise ValueError("Dataset must contain a depot and at least one customer")

    data = np.zeros((len(customers), 7), dtype=np.float64)
    for i, cust in enumerate(customers):
        data[i, 0] = float(cust["id"])
        # Undo _to_lat_lng so distances match the original Solomon geometry;
        # projecting through lat/lng instead would silently rescale every
        # distance and make comparisons against BKS meaningless.
        data[i, 1] = (float(cust["lng"]) - _LNG_ORIGIN) / _XY_SCALE
        data[i, 2] = (float(cust["lat"]) - _LAT_ORIGIN) / _XY_SCALE
        data[i, 3] = float(cust["demand"])
        data[i, 4] = float(cust["ready"])
        data[i, 5] = float(cust["due"])
        data[i, 6] = float(cust["service"])

    return {
        "name": str(dataset.get("dataset", "unknown")).upper(),
        "capacity": float(dataset["fleet"]["capacity"]),
        "data": data,
    }


# --- Built-in synthetic instance ---------------------------------------------------
# A 12-customer mini benchmark centred on Ho Chi Minh City. Ships in-process so the
# demo always has something to load, even before users run scripts/fetch_solomon.py.
# Demand/time-window scale mirrors a small Solomon RC1 instance so the solver does
# not need to be retuned. Distance and time use the same unit (~1 km <-> 1 unit).
_DEMO_FLEET = {"vehicles": 4, "capacity": 80}
_DEMO_NAMES = [
    "Đại học Tôn Đức Thắng",
    "Ben Thanh Market",
    "Notre-Dame Cathedral",
    "Tan Dinh Market",
    "Independence Palace",
    "Pham Ngu Lao Hostel",
    "Cho Lon Wholesale",
    "Phu My Hung Office",
    "An Phu Logistics Park",
    "Thao Dien Studios",
    "Phu Nhuan Pharmacy",
    "Tan Binh Cargo",
    "Go Vap Warehouse",
]
_DEMO_ADDRESSES = [
    "19 Nguyễn Hữu Thọ, Tân Hưng, Quận 7, Hồ Chí Minh",
    "Chợ Bến Thành, Lê Lợi, Bến Thành, Quận 1, Hồ Chí Minh",
    "01 Công xã Paris, Bến Nghé, Quận 1, Hồ Chí Minh",
    "Chợ Tân Định, 336 Hai Bà Trưng, Tân Định, Quận 1, Hồ Chí Minh",
    "Dinh Độc Lập, 135 Nam Kỳ Khởi Nghĩa, Bến Nghé, Quận 1, Hồ Chí Minh",
    "Đường Phạm Ngũ Lão, Quận 1, Hồ Chí Minh",
    "Chợ Lớn, Trang Tử, Phường 2, Quận 6, Hồ Chí Minh",
    "Khu đô thị Phú Mỹ Hưng, Tân Phong, Quận 7, Hồ Chí Minh",
    "Khu dân cư An Phú, Quận 2, Hồ Chí Minh",
    "Phường Thảo Điền, Quận 2, Hồ Chí Minh",
    "Phan Xích Long, Phường 2, Phú Nhuận, Hồ Chí Minh",
    "Phường 2, Quận Tân Bình, Hồ Chí Minh",
    "Phường 10, Quận Gò Vấp, Hồ Chí Minh",
]
_DEMO_RAW: list[tuple[float, float, int, int, int, int]] = [
    # (lat, lng, demand, ready, due, service)
    (10.7330, 106.7025, 0, 0, 240, 0),  # Ton Duc Thang University Depot
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


_C1_DEMO_RAW: list[tuple[float, float, int, int, int, int]] = [
    # Clustered demo
    (10.7330, 106.7025, 0, 0, 240, 0),
    (10.7723, 106.6985, 8, 0, 90, 10),
    (10.7798, 106.6991, 6, 30, 120, 10),
    (10.7765, 106.6951, 7, 40, 140, 10),
    (10.7670, 106.6932, 5, 0, 80, 10),
    (10.7995, 106.7375, 11, 50, 170, 12),
    (10.8014, 106.7308, 7, 30, 150, 10),
    (10.8050, 106.7350, 10, 60, 180, 10),
    (10.7950, 106.7310, 8, 70, 190, 10),
    (10.8400, 106.6650, 8, 60, 220, 12),
    (10.8420, 106.6610, 9, 80, 230, 12),
    (10.8380, 106.6680, 6, 50, 200, 12),
    (10.8450, 106.6600, 7, 90, 240, 12),
]


_R1_DEMO_RAW: list[tuple[float, float, int, int, int, int]] = [
    # Random demo
    (10.7330, 106.7025, 0, 0, 240, 0),
    (10.7530, 106.6510, 12, 60, 180, 15),
    (10.7886, 106.6904, 9, 20, 110, 10),
    (10.7281, 106.7191, 10, 70, 200, 12),
    (10.7969, 106.6800, 6, 20, 130, 10),
    (10.7976, 106.6500, 9, 40, 160, 12),
    (10.8100, 106.7000, 8, 10, 100, 10),
    (10.7400, 106.7500, 5, 80, 150, 10),
    (10.7600, 106.6800, 7, 30, 120, 10),
    (10.8200, 106.6300, 11, 50, 170, 15),
    (10.7100, 106.6400, 6, 90, 190, 10),
    (10.8300, 106.7200, 10, 40, 140, 12),
    (10.7700, 106.7400, 8, 60, 160, 12),
]


def _builtin_variant(name: str) -> dict[str, Any]:
    raw_data = _DEMO_RAW
    if name == "c1_demo":
        raw_data = _C1_DEMO_RAW
    elif name == "r1_demo":
        raw_data = _R1_DEMO_RAW

    customers: list[dict[str, Any]] = []
    for idx, (lat, lng, demand, ready, due, service) in enumerate(raw_data):
        customers.append(
            {
                "id": idx,
                "name": _DEMO_NAMES[idx] if idx < len(_DEMO_NAMES) else f"DEMO-{idx}",
                "address": _DEMO_ADDRESSES[idx] if idx < len(_DEMO_ADDRESSES) else f"Demo customer {idx}",
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
        "dataset": name if name in {"c1_demo", "r1_demo"} else "demo",
        "fleet": dict(_DEMO_FLEET),
        "customers": customers,
        "_builtin": True,
    }


def _is_builtin(name: str) -> bool:
    return name.strip().lower() in {"demo", "builtin", "sample", "c1_demo", "r1_demo"}


def load_solomon_dataset(name: str = "demo") -> dict[str, Any]:
    raw_name = (name or "demo").strip().lower()

    if _is_builtin(raw_name):
        return _builtin_variant(raw_name)

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
    for raw in lines[header_idx + 1 :]:
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
    items.append({"name": "demo", "label": "Demo RC (12 customers, HCMC)", "builtin": True})
    items.append({"name": "c1_demo", "label": "Demo C1 (12 customers, HCMC)", "builtin": True})
    items.append({"name": "r1_demo", "label": "Demo R1 (12 customers, HCMC)", "builtin": True})
    seen.update(["demo", "c1_demo", "r1_demo"])

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
