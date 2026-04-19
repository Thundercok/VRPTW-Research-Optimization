from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from models.schemas import JobRequest, JobState
from runtime_repositories.job_repo import job_repo
from services.solver_service import solve_model


class JobService:
    async def worker_loop(self) -> None:
        while True:
            job_id = await job_repo.queue.get()
            state = job_repo.get(job_id)
            if not state or not state.payload:
                job_repo.queue.task_done()
                continue

            try:
                state.status = "processing"
                job_repo.save(job_id, state)
                await asyncio.sleep(0.6)
                state.result = await solve_model(state.payload)
                state.status = "done"
                job_repo.save(job_id, state)
            except Exception as exc:  # pragma: no cover
                state.status = "failed"
                state.error = str(exc)
                job_repo.save(job_id, state)
            finally:
                job_repo.queue.task_done()

    async def submit(self, body: JobRequest) -> dict[str, str]:
        if len(body.customers) < 2:
            raise HTTPException(
                status_code=400, detail="Need depot and customer")

        job_id = str(uuid4())
        job_repo.save(job_id, JobState(status="queued", payload=body))
        await job_repo.queue.put(job_id)
        return {"job_id": job_id, "status": "queued"}

    def get(self, job_id: str) -> dict[str, Any]:
        state = job_repo.get(job_id)
        if not state:
            raise HTTPException(status_code=404, detail="Job not found")
        return {
            "job_id": job_id,
            "status": state.status,
            "result": state.result,
            "error": state.error,
        }


job_service = JobService()
