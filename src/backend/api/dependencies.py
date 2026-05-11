from __future__ import annotations

from core.config import demo_auth_bypass_enabled
from core.firebase import is_firebase_enabled
from fastapi import Header, HTTPException
from services.auth_service import get_user_by_token


async def require_user(authorization: str | None = Header(default=None)) -> dict[str, str]:
    """Resolve the current user, with optional demo bypass for local runs.

    - If ``DEMO_AUTH_BYPASS`` is true and the bearer token is the synthetic
      ``demo-guest`` value, the request is served as an anonymous guest.
      This works regardless of whether Firebase is configured, so the live
      demo can coexist with real auth.
    - If Firebase is configured, real bearer-token auth is required.
    - If Firebase is NOT configured AND ``DEMO_AUTH_BYPASS`` is true (default),
      requests without any token are served as a synthetic operator.
    - If Firebase is NOT configured AND ``DEMO_AUTH_BYPASS=false``, the API
      returns 503 so production deploys never accidentally expose endpoints.
    """
    # Fast path: synthetic guest token from the frontend "Continue as Guest" flow.
    if demo_auth_bypass_enabled():
        token = (authorization or "").removeprefix("Bearer ").strip()
        if token == "demo-guest" or (not is_firebase_enabled() and not token):
            return {
                "email": "guest@demo.local",
                "role": "operator",
                "mode": "demo",
            }

    if not is_firebase_enabled():
        raise HTTPException(
            status_code=503,
            detail="Authentication backend not configured. Set up Firebase or enable DEMO_AUTH_BYPASS.",
        )

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    return get_user_by_token(token)
