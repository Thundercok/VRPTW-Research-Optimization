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
        self.persistence_enabled = True

    def save(self, job_id: str, state: JobState) -> None:
        self.jobs[job_id] = state
        if not self.persistence_enabled:
            return

        try:
            firestore_result = self._prepare_result_for_persistence(state.result)
            self._jobs_collection().document(job_id).set(
                {
                    "job_id": job_id,
                    "status": state.status,
                    "payload": state.payload.model_dump() if state.payload else None,
                    "result": firestore_result,
                    "error": state.error,
                    "debug": state.debug,
                    "updated_at": int(time.time()),
                },
                timeout=5,
            )
        except Exception:
            # Fail open: keep queue processing in-memory when Firestore is unavailable.
            self.persistence_enabled = False

    def get(self, job_id: str) -> JobState | None:
        cached = self.jobs.get(job_id)
        if cached:
            return cached

        if not self.persistence_enabled:
            return None

        try:
            snap = self._jobs_collection().document(job_id).get(timeout=5)
        except Exception:
            self.persistence_enabled = False
            return None
        if not snap.exists:
            return None

        row = snap.to_dict() or {}
        payload_data = row.get("payload")
        payload = JobRequest.model_validate(payload_data) if payload_data else None
        state = JobState(
            status=str(row.get("status", "queued")),
            payload=payload,
            result=self._restore_result_from_persistence(row.get("result")),
            error=row.get("error"),
            debug=row.get("debug") if isinstance(row.get("debug"), dict) else None,
        )
        self.jobs[job_id] = state
        return state

    def _prepare_result_for_persistence(self, result: dict | None) -> dict | None:
        if not isinstance(result, dict):
            return result

        out: dict = {}
        for algo_key, algo_value in result.items():
            if not isinstance(algo_value, dict):
                out[algo_key] = algo_value
                continue

            algo_doc = dict(algo_value)
            routes = algo_doc.get("routes")
            if isinstance(routes, list):
                safe_routes = []
                for route in routes:
                    if not isinstance(route, dict):
                        safe_routes.append(route)
                        continue

                    safe_route = dict(route)
                    path = safe_route.get("path")
                    if isinstance(path, list):
                        safe_path = []
                        for point in path:
                            if (
                                isinstance(point, list)
                                and len(point) == 2
                                and all(isinstance(v, (int, float)) for v in point)
                            ):
                                safe_path.append({"lat": float(point[0]), "lng": float(point[1])})
                            else:
                                safe_path.append(point)
                        safe_route["path"] = safe_path

                    safe_routes.append(safe_route)
                algo_doc["routes"] = safe_routes

            out[algo_key] = algo_doc

        return out

    def _restore_result_from_persistence(self, result: dict | None) -> dict | None:
        if not isinstance(result, dict):
            return result

        out: dict = {}
        for algo_key, algo_value in result.items():
            if not isinstance(algo_value, dict):
                out[algo_key] = algo_value
                continue

            algo_doc = dict(algo_value)
            routes = algo_doc.get("routes")
            if isinstance(routes, list):
                restored_routes = []
                for route in routes:
                    if not isinstance(route, dict):
                        restored_routes.append(route)
                        continue

                    restored_route = dict(route)
                    path = restored_route.get("path")
                    if isinstance(path, list):
                        restored_path = []
                        for point in path:
                            if isinstance(point, dict) and "lat" in point and "lng" in point:
                                restored_path.append([point.get("lat"), point.get("lng")])
                            else:
                                restored_path.append(point)
                        restored_route["path"] = restored_path

                    restored_routes.append(restored_route)
                algo_doc["routes"] = restored_routes

            out[algo_key] = algo_doc

        return out

    def _jobs_collection(self):
        return get_db().collection("jobs")


job_repo = JobRepository()
