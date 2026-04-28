"""Rate limiting helpers built on slowapi.

We keep one shared :data:`limiter` so all routers share the same in-memory
counter store. Limits are intentionally generous for the demo but tight enough
to slow down credential stuffing or job-spamming bots.

Override defaults at runtime with environment variables, e.g.::

    RATE_LIMIT_AUTH_TOKEN="20/minute"
    RATE_LIMIT_AUTH_OTP="3/minute"
    RATE_LIMIT_JOBS="30/minute"

If ``RATE_LIMIT_ENABLED=false`` the limiter is created but no requests are
counted (useful for load tests on a private staging box).
"""

from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address


def _flag(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


RATE_LIMIT_ENABLED = _flag("RATE_LIMIT_ENABLED", default=True)


def _env(name: str, default: str) -> str:
    return os.getenv(name, default).strip() or default


AUTH_TOKEN_LIMIT = _env("RATE_LIMIT_AUTH_TOKEN", "10/minute")
AUTH_OTP_LIMIT = _env("RATE_LIMIT_AUTH_OTP", "5/minute")
AUTH_REGISTER_LIMIT = _env("RATE_LIMIT_AUTH_REGISTER", "5/minute")
AUTH_FORGOT_LIMIT = _env("RATE_LIMIT_AUTH_FORGOT", "5/minute")
JOBS_LIMIT = _env("RATE_LIMIT_JOBS", "30/minute")
GEOCODE_LIMIT = _env("RATE_LIMIT_GEOCODE", "60/minute")


limiter = Limiter(
    key_func=get_remote_address,
    enabled=RATE_LIMIT_ENABLED,
    default_limits=[],
    # ``headers_enabled`` injects X-RateLimit-* into responses by mutating the
    # endpoint return value. That breaks any endpoint returning ``dict``/Pydantic
    # (FastAPI default), so we leave it off. The 429 response set by our
    # exception handler in ``main.py`` still includes Retry-After.
    headers_enabled=False,
    storage_uri="memory://",
)
