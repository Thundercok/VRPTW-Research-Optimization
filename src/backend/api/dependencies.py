from __future__ import annotations

from fastapi import Header, HTTPException

from core.firebase import is_firebase_enabled
from services.auth_service import get_user_by_token


async def require_user(authorization: str | None = Header(default=None)) -> dict[str, str]:
    if not is_firebase_enabled():
        return {
            "email": "anonymous@demo.local",
            "role": "operator",
            "mode": "demo",
        }

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    return get_user_by_token(token)
