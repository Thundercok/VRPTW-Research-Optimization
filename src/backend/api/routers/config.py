"""Public configuration endpoint for the frontend.

Exposes only **non-secret** values (DSNs, public site keys) so the SPA can
initialise Sentry/Plausible/PostHog without bundling those values at build
time. Server-side secrets stay in environment variables.
"""

from __future__ import annotations

import os

from fastapi import APIRouter

router = APIRouter(tags=["config"])


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


@router.get("/config")
async def public_config() -> dict[str, object]:
    sentry_dsn = _env("SENTRY_FRONTEND_DSN") or _env("SENTRY_DSN_FRONTEND")
    sentry_env = _env("SENTRY_ENVIRONMENT") or "development"
    sentry_traces = _env("SENTRY_TRACES_SAMPLE_RATE") or "0.0"

    plausible_domain = _env("PLAUSIBLE_DOMAIN")
    plausible_src = _env("PLAUSIBLE_SCRIPT_SRC") or "https://plausible.io/js/script.js"

    posthog_key = _env("POSTHOG_PUBLIC_KEY")
    posthog_host = _env("POSTHOG_HOST") or "https://app.posthog.com"

    return {
        "app": {
            "name": "VRPTW Research Optimization",
            "version": _env("APP_VERSION") or "dev",
        },
        "sentry": {
            "dsn": sentry_dsn,
            "environment": sentry_env,
            "tracesSampleRate": _safe_float(sentry_traces, 0.0),
            "enabled": bool(sentry_dsn),
        },
        "plausible": {
            "domain": plausible_domain,
            "src": plausible_src,
            "enabled": bool(plausible_domain),
        },
        "posthog": {
            "apiKey": posthog_key,
            "apiHost": posthog_host,
            "enabled": bool(posthog_key),
        },
    }


def _safe_float(raw: str, default: float) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default
