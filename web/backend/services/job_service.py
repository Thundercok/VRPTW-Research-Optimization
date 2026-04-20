from __future__ import annotations

import asyncio
import time
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from models.schemas import JobRequest, JobState
from runtime_repositories.job_repo import job_repo
from services.matrix_service import calculate_matrix
from services.solver_service import solve_model


class JobService:
    def _now(self) -> float:
        return time.time()

    def _ensure_debug(self, state: JobState) -> dict[str, Any]:
        if not isinstance(state.debug, dict):
            state.debug = {}
        if not isinstance(state.debug.get("events"), list):
            state.debug["events"] = []
        return state.debug

    def _record_event(self, state: JobState, stage: str, message: str) -> None:
        debug = self._ensure_debug(state)
        events = debug["events"]
        events.append({"ts": self._now(), "stage": stage, "message": message})

    def _build_result_summary(self, result: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(result, dict):
            return None

        summary: dict[str, Any] = {}
        for algo in ("ddqn", "alns"):
            data = result.get(algo)
            if not isinstance(data, dict):
                continue
            summary[algo] = {
                "runtime_sec": data.get("runtime_sec"),
                "total_distance_km": data.get("total_distance_km"),
                "vehicles_used": data.get("vehicles_used"),
                "route_count": len(data.get("routes", [])) if isinstance(data.get("routes"), list) else 0,
            }

        return summary or None

    async def worker_loop(self) -> None:
        while True:
            job_id = await job_repo.queue.get()
            state = job_repo.get(job_id)
            if not state or not state.payload:
                job_repo.queue.task_done()
                continue

            try:
                debug = self._ensure_debug(state)
                dequeued_at = self._now()
                debug["phase"] = "processing"
                debug["dequeued_at"] = dequeued_at
                if isinstance(debug.get("queued_at"), (int, float)):
                    debug["queue_wait_sec"] = max(0.0, dequeued_at - float(debug["queued_at"]))
                self._record_event(state, "processing", "Worker picked job from queue")

                state.status = "processing"
                job_repo.save(job_id, state)
                await asyncio.sleep(0.6)

                matrix_started_at = self._now()
                debug["phase"] = "matrix"
                debug["matrix_started_at"] = matrix_started_at
                self._record_event(state, "matrix", "Building distance matrix")
                matrix_result = await calculate_matrix(state.payload.customers)
                matrix_finished_at = self._now()
                debug["matrix_finished_at"] = matrix_finished_at
                debug["matrix_duration_sec"] = max(0.0, matrix_finished_at - matrix_started_at)
                debug["matrix_provider"] = matrix_result.get("provider")
                debug["matrix_size"] = len(matrix_result.get("matrix", [])) if isinstance(matrix_result.get("matrix"), list) else 0
                self._record_event(state, "matrix", f"Distance matrix ready via {matrix_result.get('provider', 'unknown')}")

                solver_started_at = self._now()
                debug["phase"] = "solving"
                debug["solver_started_at"] = solver_started_at
                self._record_event(state, "solving", "Solver started")

                state.result = await solve_model(state.payload)

                solver_finished_at = self._now()
                debug["solver_finished_at"] = solver_finished_at
                debug["solver_duration_sec"] = max(0.0, solver_finished_at - solver_started_at)

                state.status = "done"
                debug["phase"] = "done"
                debug["completed_at"] = solver_finished_at
                if isinstance(debug.get("created_at"), (int, float)):
                    debug["total_elapsed_sec"] = max(0.0, solver_finished_at - float(debug["created_at"]))
                self._record_event(state, "done", "Job completed")
                job_repo.save(job_id, state)
            except Exception as exc:  # pragma: no cover
                state.status = "failed"
                state.error = str(exc)
                debug = self._ensure_debug(state)
                failed_at = self._now()
                debug["phase"] = "failed"
                debug["failed_at"] = failed_at
                if isinstance(debug.get("created_at"), (int, float)):
                    debug["total_elapsed_sec"] = max(0.0, failed_at - float(debug["created_at"]))
                self._record_event(state, "failed", f"Job failed: {state.error}")
                job_repo.save(job_id, state)
            finally:
                job_repo.queue.task_done()

    async def submit(self, body: JobRequest) -> dict[str, str]:
        if len(body.customers) < 2:
            raise HTTPException(
                status_code=400, detail="Need depot and customer")

        job_id = str(uuid4())
        now = self._now()
        state = JobState(
            status="queued",
            payload=body,
            debug={
                "phase": "queued",
                "created_at": now,
                "queued_at": now,
                "queue_size_on_submit": job_repo.queue.qsize(),
                "events": [{"ts": now, "stage": "queued", "message": "Job submitted"}],
            },
        )
        job_repo.save(job_id, state)
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
            "debug": state.debug or {},
        }

    def get_debug(self, job_id: str) -> dict[str, Any]:
        state = job_repo.get(job_id)
        if not state:
            raise HTTPException(status_code=404, detail="Job not found")
        return {
            "job_id": job_id,
            "status": state.status,
            "error": state.error,
            "queue_size": job_repo.queue.qsize(),
            "has_result": state.result is not None,
            "result_summary": self._build_result_summary(state.result),
            "debug": state.debug or {},
        }


job_service = JobService()
