from __future__ import annotations

from typing import Any

from api.dependencies import require_user
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Path as ApiPath
from models.schemas import RoleUpdateRequest
from services import auth_service

router = APIRouter(tags=["admin"])


def _ensure_admin(user: dict[str, str]) -> dict[str, str]:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


@router.get("/admin/users")
async def admin_list_users(user: dict[str, str] = Depends(require_user)) -> dict[str, Any]:
    _ensure_admin(user)
    return auth_service.list_users()


@router.patch("/admin/users/{email}/role")
async def admin_update_role(
    body: RoleUpdateRequest,
    email: str = ApiPath(...),
    user: dict[str, str] = Depends(require_user),
) -> dict[str, str]:
    _ensure_admin(user)
    return auth_service.update_user_role(email, body.role)


@router.delete("/admin/users/{email}")
async def admin_delete_user(
    email: str = ApiPath(...),
    user: dict[str, str] = Depends(require_user),
) -> dict[str, str]:
    _ensure_admin(user)
    return auth_service.delete_user(email)
