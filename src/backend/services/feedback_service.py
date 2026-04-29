from __future__ import annotations

import time
from uuid import uuid4

from fastapi import HTTPException
from models.schemas import FeedbackEntry, FeedbackSubmitRequest
from runtime_repositories.feedback_repo import feedback_repo


def _normalize_language(language: str) -> str:
    value = language.strip().lower()
    return value if value in {"en", "vn"} else "en"


def _normalize_category(category: str) -> str:
    value = category.strip().lower()
    return value[:40] if value else "general"


def submit_feedback(body: FeedbackSubmitRequest, user_agent: str = "") -> dict[str, str]:
    message = body.message.strip()
    if len(message) < 3:
        raise HTTPException(status_code=400, detail="Feedback message is required")

    entry = FeedbackEntry(
        id=str(uuid4()),
        created_at=int(time.time()),
        page=body.page.strip() or "feedback",
        language=_normalize_language(body.language),
        category=_normalize_category(body.category),
        message=message,
        contact=body.contact.strip(),
        rating=body.rating,
        source="anonymous",
        user_agent=user_agent.strip()[:250],
        status="new",
    )
    feedback_repo.save(entry)
    return {"message": "feedback_saved", "feedback_id": entry.id}


def list_feedback(limit: int = 100) -> dict[str, object]:
    items = feedback_repo.list(limit=limit)
    return {"items": [item.model_dump() for item in items]}