from __future__ import annotations

import asyncio
import time

from core.firebase import get_db
from models.schemas import JobRequest
from models.schemas import JobState


class JobRepository:
    def __init__(self) -> None:
        self.jobs: dict[str, JobState] = {}
        self.queue: asyncio.Queue[str] = asyncio.Queue()

    def save(self, job_id: str, state: JobState) -> None:
        self.jobs[job_id] = state
        self._jobs_collection().document(job_id).set(
            {
                "job_id": job_id,
                "status": state.status,
                "payload": state.payload.model_dump() if state.payload else None,
                "result": state.result,
                "error": state.error,
                "updated_at": int(time.time()),
            }
        )

    def get(self, job_id: str) -> JobState | None:
        cached = self.jobs.get(job_id)
        if cached:
            return cached

        snap = self._jobs_collection().document(job_id).get()
        if not snap.exists:
            return None

        row = snap.to_dict() or {}
        payload_data = row.get("payload")
        payload = JobRequest.model_validate(payload_data) if payload_data else None
        state = JobState(
            status=str(row.get("status", "queued")),
            payload=payload,
            result=row.get("result"),
            error=row.get("error"),
        )
        self.jobs[job_id] = state
        return state

    def _jobs_collection(self):
        return get_db().collection("jobs")


job_repo = JobRepository()
