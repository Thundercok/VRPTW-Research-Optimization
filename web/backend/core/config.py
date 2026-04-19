from __future__ import annotations

import os
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "auth.db"
REGISTER_OTP_TTL_SEC = 600
RESET_TOKEN_TTL_SEC = 900


def load_local_env() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
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
