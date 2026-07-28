"""Route CPU/RAM-heavy solver work to a remote compute service.

Render's free tier caps a web service at 512 MB RAM, which is well under what
torch + numba + the DDQN weights need just to import. So in production the API
process stays slim and forwards every heavy call to a Hugging Face Space that
carries the research stack.

Set ``SOLVER_REMOTE_URL`` to enable the remote path; leave it unset and the
handlers keep running the solver in-process (local dev, full Docker image).
``SOLVER_API_TOKEN`` must match the token the Space expects.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# A cold Space wakes from sleep before it answers, and a 7-algorithm solve on
# 2 vCPUs is minutes, not seconds.
DEFAULT_TIMEOUT_SEC = 600.0


def remote_url() -> str | None:
    value = os.getenv("SOLVER_REMOTE_URL", "").strip().rstrip("/")
    return value or None


def remote_enabled() -> bool:
    return remote_url() is not None


def _headers() -> dict[str, str]:
    token = os.getenv("SOLVER_API_TOKEN", "").strip()
    return {"X-Solver-Token": token} if token else {}


async def call_remote(
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    method: str = "POST",
    params: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SEC,
) -> Any:
    """Forward a request to the remote solver and unwrap its JSON body.

    Errors are re-raised as ``HTTPException`` so callers can let them bubble
    straight out of a route handler.
    """
    base = remote_url()
    if base is None:
        raise HTTPException(status_code=503, detail="Remote solver is not configured (SOLVER_REMOTE_URL unset).")

    url = f"{base}{path}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method,
                url,
                json=payload,
                params=params,
                headers=_headers(),
            )
    except httpx.TimeoutException as exc:
        logger.error("Remote solver timed out after %ss: %s %s", timeout, method, url)
        raise HTTPException(status_code=504, detail=f"Remote solver timed out after {timeout:.0f}s.") from exc
    except httpx.HTTPError as exc:
        logger.error("Remote solver unreachable: %s %s (%s)", method, url, exc)
        raise HTTPException(status_code=502, detail=f"Remote solver unreachable: {exc}") from exc

    if response.status_code >= 400:
        # Pass the Space's own error through so the UI shows the real cause
        # (infeasible fleet, unknown dataset, ...) instead of a blanket 502.
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        logger.warning("Remote solver returned %s for %s: %s", response.status_code, path, detail)
        raise HTTPException(status_code=response.status_code, detail=detail)

    return response.json()


async def remote_health() -> dict[str, Any]:
    """Best-effort probe of the Space, for surfacing in ``/api/health``."""
    base = remote_url()
    if base is None:
        return {"configured": False}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base}/health", headers=_headers())
        return {
            "configured": True,
            "url": base,
            "reachable": response.status_code == 200,
            "detail": response.json() if response.status_code == 200 else response.text[:200],
        }
    except httpx.HTTPError as exc:
        return {"configured": True, "url": base, "reachable": False, "detail": str(exc)}
