from fastapi import APIRouter, Depends
from api.dependencies import require_user

router = APIRouter(tags=["auth"])

@router.get("/auth/me")
async def auth_me(user: dict[str, str] = Depends(require_user)) -> dict[str, str]:
    """Returns the verified user context from the Firebase token."""
    return user
