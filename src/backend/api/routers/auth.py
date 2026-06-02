from api.dependencies import require_user
from core.rate_limit import AUTH_TOKEN_LIMIT, limiter
from fastapi import APIRouter, Depends, HTTPException, Request, status

router = APIRouter(tags=["auth"])


@router.get("/auth/me")
async def auth_me(user: dict[str, str] = Depends(require_user)) -> dict[str, str]:
    """Returns the verified user context from the Firebase token."""
    return user


@router.post("/auth/token")
@limiter.limit(AUTH_TOKEN_LIMIT)
async def auth_token(request: Request) -> dict[str, str]:
    """Stub endpoint for authentication token requests, primarily for compatibility and rate limiting tests."""
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Password authentication is disabled. Please use Firebase ID token auth.",
    )
