from __future__ import annotations

from typing import Any

from api.dependencies import require_user
from fastapi import APIRouter, Depends, HTTPException, Request
from models.schemas import FeedbackSubmitRequest
from services.feedback_service import list_feedback, submit_feedback

router = APIRouter(tags=["feedback"])


@router.post("/feedback")
async def feedback_submit(request: Request, body: FeedbackSubmitRequest) -> dict[str, str]:
    return submit_feedback(body, user_agent=request.headers.get("user-agent", ""))


@router.get("/admin/feedback")
async def feedback_admin_list(user: dict[str, str] = Depends(require_user)) -> dict[str, Any]:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return list_feedback()