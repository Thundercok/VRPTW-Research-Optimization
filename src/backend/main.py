from __future__ import annotations

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from api.routers import admin, auth, ops
from core.config import load_local_env
from core.firebase import init_firebase, is_firebase_enabled
from services.job_service import job_service

load_local_env()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("vrptw.backend")


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        init_firebase()
    except Exception as exc:
        logger.warning("Firebase init failed (continuing without auth): %s", exc)

    if is_firebase_enabled():
        logger.info("Firebase Admin enabled - auth/admin endpoints active.")
    else:
        logger.warning(
            "Firebase Admin disabled - VRPTW demo solver still works at /, "
            "but /api/auth and /api/admin will return 503."
        )

    worker_task = asyncio.create_task(job_service.worker_loop())
    try:
        yield
    finally:
        worker_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await worker_task


class NoCacheHTMLMiddleware(BaseHTTPMiddleware):
    """Disable browser caching for HTML/JS/CSS during development.

    Prevents stale frontend bundles when iterating quickly. Static binary
    assets (images, fonts) are still cacheable to keep page loads fast.
    """

    NO_CACHE_PATTERNS = (".html", ".js", ".css", ".map")

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        path = request.url.path.lower()
        is_root = path == "/" or path.endswith("/")
        if is_root or any(path.endswith(suffix) for suffix in self.NO_CACHE_PATTERNS):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


app = FastAPI(title="VRPTW API", lifespan=lifespan)
app.add_middleware(NoCacheHTMLMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(ops.router, prefix="/api")


frontend_path = Path(__file__).resolve().parents[1] / "frontend"
if frontend_path.exists():
    app.mount("", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
