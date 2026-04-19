from __future__ import annotations

import asyncio
import contextlib
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routers import admin, auth, ops
from core.config import load_local_env
from core.database import init_db
from services.job_service import job_service

load_local_env()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    worker_task = asyncio.create_task(job_service.worker_loop())
    try:
        yield
    finally:
        worker_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await worker_task


app = FastAPI(title="VRPTW API", lifespan=lifespan)
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

# Serve static files - must be last
frontend_path = Path(__file__).resolve().parents[1] / "frontend"
if frontend_path.exists():
    app.mount("", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
