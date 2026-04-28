from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from api.routers import admin, auth, ops
from api.routers import config as config_router
from core.config import cors_allow_origins, demo_auth_bypass_enabled, load_local_env
from core.firebase import init_firebase, is_firebase_enabled
from core.rate_limit import limiter
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from services.job_service import job_service
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

load_local_env()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("vrptw.backend")


def _maybe_init_sentry() -> None:
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        return
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=dsn,
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            environment=os.getenv("SENTRY_ENVIRONMENT", "development"),
            send_default_pii=False,
        )
        logger.info("Sentry SDK initialized.")
    except ImportError:
        logger.warning(
            "SENTRY_DSN is set but `sentry-sdk` is not installed. "
            "Run `pip install sentry-sdk` to enable error reporting."
        )
    except Exception as exc:
        logger.warning("Sentry init failed: %s", exc)


@asynccontextmanager
async def lifespan(_: FastAPI):
    _maybe_init_sentry()

    try:
        init_firebase()
    except Exception as exc:
        logger.warning("Firebase init failed (continuing without auth): %s", exc)

    if is_firebase_enabled():
        logger.info("Firebase Admin enabled - auth/admin endpoints active.")
    else:
        if demo_auth_bypass_enabled():
            logger.warning(
                "Firebase Admin disabled - demo bypass ON. "
                "All /api endpoints serve an anonymous operator. "
                "Set DEMO_AUTH_BYPASS=false in production."
            )
        else:
            logger.warning(
                "Firebase Admin disabled and demo bypass OFF - protected endpoints will return 503."
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


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply baseline security headers to every response.

    Defaults are conservative but compatible with the current frontend, which
    loads Leaflet, SheetJS, Google Fonts, and Shields.io badges from CDNs.
    Adjust the CSP via the ``CONTENT_SECURITY_POLICY`` env var if you swap
    asset providers or self-host them.
    """

    DEFAULT_CSP = (
        "default-src 'self'; "
        "img-src 'self' data: https:; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net "
        "https://www.gstatic.com https://browser.sentry-cdn.com https://js.sentry-cdn.com "
        "https://plausible.io https://app.posthog.com https://*.posthog.com; "
        "connect-src 'self' https: ws: wss:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'"
    )

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        csp = os.getenv("CONTENT_SECURITY_POLICY", "").strip() or self.DEFAULT_CSP
        response.headers.setdefault("Content-Security-Policy", csp)
        return response


app = FastAPI(title="VRPTW API", lifespan=lifespan)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Translate slowapi quota errors into the JSON shape the frontend expects."""
    retry_after = getattr(exc, "retry_after", None)
    detail = f"Too many requests. Limit: {exc.detail}." if getattr(exc, "detail", None) else "Too many requests."
    headers: dict[str, str] = {}
    if retry_after is not None:
        headers["Retry-After"] = str(int(retry_after))
    return JSONResponse(status_code=429, content={"detail": detail}, headers=headers)


app.add_middleware(NoCacheHTMLMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(ops.router, prefix="/api")
app.include_router(config_router.router, prefix="/api")


frontend_path = Path(__file__).resolve().parents[1] / "frontend"
if frontend_path.exists():
    app.mount("", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
