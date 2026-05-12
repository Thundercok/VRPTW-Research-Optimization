from __future__ import annotations

from core.config import demo_auth_bypass_enabled
from core.firebase import is_firebase_enabled
from fastapi import Header, HTTPException
from services.auth_service import get_user_by_token


async def require_user(authorization: str | None = Header(default=None)) -> dict[str, str]:
    """Resolve the current user, with optional demo bypass for local runs.

    - If Firebase is configured, real bearer-token auth is required (no bypass).
    - If Firebase is NOT configured AND ``DEMO_AUTH_BYPASS`` is true (default),
      requests are served as a synthetic ``anonymous@demo.local`` operator.
    - If Firebase is NOT configured AND ``DEMO_AUTH_BYPASS=false``, the API
      returns 503 so production deploys never accidentally expose endpoints.
    """
    if not is_firebase_enabled():
        if demo_auth_bypass_enabled():
            return {
                "email": "anonymous@demo.local",
                "role": "operator",
                "mode": "demo",
            }
        raise HTTPException(
            status_code=503,
            detail="Authentication backend not configured. Set up Firebase or enable DEMO_AUTH_BYPASS.",
        )

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    return get_user_by_token(token)
