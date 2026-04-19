from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from api.dependencies import require_user
from models.schemas import JobRequest, MatrixRequest
from services.geocode_service import geocode_address, reverse_geocode_address
from services.job_service import job_service
from services.matrix_service import calculate_matrix

router = APIRouter(tags=["ops"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/geocode")
async def geocode(q: str = Query(min_length=2), limit: int = Query(default=5, ge=1, le=10)) -> dict[str, Any]:
    return await geocode_address(q, limit)


@router.get("/reverse-geocode")
async def reverse_geocode(lat: float = Query(), lng: float = Query()) -> dict[str, Any]:
    return await reverse_geocode_address(lat, lng)


@router.post("/matrix")
async def matrix(body: MatrixRequest, _: dict[str, str] = Depends(require_user)) -> dict[str, Any]:
    return await calculate_matrix(body.points)


@router.post("/jobs")
async def submit_job(body: JobRequest, _: dict[str, str] = Depends(require_user)) -> dict[str, str]:
    return await job_service.submit(body)


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, _: dict[str, str] = Depends(require_user)) -> dict[str, Any]:
    return job_service.get(job_id)
