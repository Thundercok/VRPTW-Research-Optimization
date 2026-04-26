from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import require_user
from core.firebase import is_firebase_enabled
from models.schemas import JobRequest, MatrixRequest
from services.geocode_service import geocode_address, reverse_geocode_address
from services.job_service import job_service
from services.matrix_service import calculate_matrix
from services.solomon_service import load_solomon_dataset

router = APIRouter(tags=["ops"])

_ROOT_PATH = Path(__file__).resolve().parents[4]
_LOGS_PATH = _ROOT_PATH / "logs"


def _parse_result_version(folder_name: str) -> str | None:
    if not folder_name.startswith("results-v"):
        return None
    version = folder_name.replace("results-", "", 1)
    if not version.startswith("v"):
        return None
    if not all(ch.isdigit() or ch == "." or ch == "v" for ch in version):
        return None
    return version


def _version_key(version: str) -> tuple[int, ...]:
    core = version.lstrip("v")
    parts = []
    for token in core.split("."):
        try:
            parts.append(int(token))
        except ValueError:
            parts.append(0)
    return tuple(parts)


@router.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "firebase_enabled": is_firebase_enabled(),
        "demo_mode": not is_firebase_enabled(),
    }


@router.get("/geocode")
async def geocode(q: str = Query(min_length=2), limit: int = Query(default=5, ge=1, le=10)) -> dict[str, Any]:
    return await geocode_address(q, limit)


@router.get("/reverse-geocode")
async def reverse_geocode(lat: float = Query(), lng: float = Query()) -> dict[str, Any]:
    return await reverse_geocode_address(lat, lng)


@router.get("/solomon")
async def solomon_dataset(
    name: str = Query(default="rc101", min_length=2, max_length=10),
    _: dict[str, str] = Depends(require_user),
) -> dict[str, Any]:
    try:
        return load_solomon_dataset(name)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=(
                f"{exc} Solomon benchmark files are not bundled with this repo. "
                "Run `python scripts/fetch_solomon.py` to download them, or use the "
                "Real Data import option to upload your own customers."
            ),
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/analysis/versions")
async def analysis_versions(_: dict[str, str] = Depends(require_user)) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    if not _LOGS_PATH.exists():
        return {"items": [], "default": None}

    # New flat layout: logs/nexus_demo.json
    flat_nexus = _LOGS_PATH / "nexus_demo.json"
    if flat_nexus.exists():
        version = "v9.5"
        try:
            with flat_nexus.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            meta_version = str(payload.get("meta", {}).get("version", "")).strip()
            if meta_version:
                version = meta_version
        except Exception:
            pass
        modified = datetime.fromtimestamp(flat_nexus.stat().st_mtime, tz=timezone.utc).isoformat()
        items.append(
            {
                "version": version.lower(),
                "folder": "logs",
                "nexus_file": flat_nexus.name,
                "updated_at": modified,
            }
        )

    # Legacy layout: logs/results-vX/nexus_demo.json
    for child in _LOGS_PATH.iterdir():
        if not child.is_dir():
            continue
        version = _parse_result_version(child.name)
        if not version:
            continue
        nexus_path = child / "nexus_demo.json"
        if not nexus_path.exists():
            continue

        modified = datetime.fromtimestamp(nexus_path.stat().st_mtime, tz=timezone.utc).isoformat()
        items.append(
            {
                "version": version,
                "folder": child.name,
                "nexus_file": str(nexus_path.name),
                "updated_at": modified,
            }
        )

    items.sort(key=lambda item: _version_key(item["version"]), reverse=True)
    default = items[0]["version"] if items else None
    return {"items": items, "default": default}


@router.get("/analysis/nexus")
async def analysis_nexus(
    version: str = Query(min_length=2, max_length=20),
    _: dict[str, str] = Depends(require_user),
) -> dict[str, Any]:
    normalized = version.strip().lower()
    if not normalized.startswith("v"):
        raise HTTPException(status_code=400, detail="Version must start with v, for example v9.5")
    if not all(ch.isdigit() or ch == "." or ch == "v" for ch in normalized):
        raise HTTPException(status_code=400, detail="Version format is invalid")

    file_path = _LOGS_PATH / "nexus_demo.json"
    folder = _LOGS_PATH
    if not file_path.exists():
        folder = _LOGS_PATH / f"results-{normalized}"
        file_path = folder / "nexus_demo.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Cannot find nexus_demo.json for version {normalized}")

    with file_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    payload["_source"] = {
        "version": normalized,
        "folder": folder.name,
        "file": file_path.name,
    }
    return payload


@router.post("/matrix")
async def matrix(body: MatrixRequest, _: dict[str, str] = Depends(require_user)) -> dict[str, Any]:
    return await calculate_matrix(body.points)


@router.post("/jobs")
async def submit_job(body: JobRequest, _: dict[str, str] = Depends(require_user)) -> dict[str, str]:
    return await job_service.submit(body)


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, _: dict[str, str] = Depends(require_user)) -> dict[str, Any]:
    return job_service.get(job_id)


@router.get("/jobs/{job_id}/debug")
async def get_job_debug(job_id: str, _: dict[str, str] = Depends(require_user)) -> dict[str, Any]:
    return job_service.get_debug(job_id)
