from __future__ import annotations

import os
from pathlib import Path

REGISTER_OTP_TTL_SEC = 600
RESET_TOKEN_TTL_SEC = 900
ACCESS_TOKEN_TTL_SEC = 86400


def load_local_env() -> None:
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def frontend_reset_url(token: str) -> str:
    from urllib.parse import urlencode

    base = os.getenv(
        "FRONTEND_URL", "http://127.0.0.1:8000").strip()
    query = urlencode({"screen": "reset", "token": token})
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}{query}"


def firebase_service_account_path() -> str | None:
    value = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "").strip()
    if not value:
        return None
    raw_path = Path(value)
    if raw_path.is_absolute():
        return str(raw_path)
    base_dir = Path(__file__).resolve().parents[3]
    return str((base_dir / raw_path).resolve())


def firebase_service_account_json() -> str | None:
    value = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    return value or None


def firebase_project_id() -> str | None:
    value = os.getenv("FIREBASE_PROJECT_ID", "").strip()
    return value or None


def env_flag(name: str, default: bool = False) -> bool:
    """Parse a boolean environment variable. Truthy: 1/true/yes/on (case-insensitive)."""
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def demo_auth_bypass_enabled() -> bool:
    """Return True when unauthenticated requests should be served as anonymous demo users.

    Default is True so that local "newbie clone" runs work without Firebase. Set
    ``DEMO_AUTH_BYPASS=false`` in production to enforce real auth.
    """
    return env_flag("DEMO_AUTH_BYPASS", default=True)


def cors_allow_origins() -> list[str]:
    """Comma-separated list of allowed origins. Defaults to ``*`` for local dev."""
    raw = os.getenv("CORS_ALLOW_ORIGINS", "*").strip()
    if not raw:
        return ["*"]
    if raw == "*":
        return ["*"]
    return [item.strip() for item in raw.split(",") if item.strip()]
