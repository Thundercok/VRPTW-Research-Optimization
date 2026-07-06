from __future__ import annotations

from typing import Any

from api.dependencies import require_user
from fastapi import APIRouter, Depends, HTTPException, Request
from models.schemas import FeedbackSubmitRequest
from services.feedback_service import list_feedback, submit_feedback

router = APIRouter(tags=["feedback"])


from pydantic import BaseModel, Field

class FeedbackUpdateRequest(BaseModel):
    status: str = Field(default="checked", max_length=40)
    developer_note: str = Field(default="", max_length=1000)


@router.post("/feedback")
async def feedback_submit(request: Request, body: FeedbackSubmitRequest) -> dict[str, str]:
    return submit_feedback(body, user_agent=request.headers.get("user-agent", ""))


@router.get("/admin/feedback")
async def feedback_admin_list(user: dict[str, str] = Depends(require_user)) -> dict[str, Any]:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return list_feedback()


@router.post("/admin/feedback/{feedback_id}")
async def feedback_admin_update(
    feedback_id: str,
    body: FeedbackUpdateRequest,
    user: dict[str, str] = Depends(require_user)
) -> dict[str, str]:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    
    from runtime_repositories.feedback_repo import feedback_repo
    entry = feedback_repo.get(feedback_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Feedback entry not found")
    
    entry.status = body.status
    entry.developer_note = body.developer_note
    feedback_repo.save(entry)
    return {"message": "feedback_updated", "feedback_id": feedback_id}
