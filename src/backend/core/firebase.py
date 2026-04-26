from __future__ import annotations

import json
import logging
from pathlib import Path

import firebase_admin
from fastapi import HTTPException
from firebase_admin import credentials, firestore

from core.config import firebase_project_id, firebase_service_account_json, firebase_service_account_path

logger = logging.getLogger(__name__)

_db: firestore.Client | None = None
_initialized: bool = False
_init_error: str | None = None


def init_firebase() -> firestore.Client | None:
    """Initialize Firebase Admin lazily.

    Returns the Firestore client when credentials are valid, otherwise returns
    ``None`` and records the reason in ``_init_error`` so the demo can still
    run (auth/admin endpoints will respond with 503 instead of crashing the
    whole process at startup).
    """
    global _db, _initialized, _init_error

    if _initialized:
        return _db

    _initialized = True
    try:
        app = firebase_admin.get_app() if firebase_admin._apps else _build_firebase_app()
        if app is None:
            return None
        _db = firestore.client(app=app)
        return _db
    except Exception as exc:
        _init_error = str(exc)
        logger.warning(
            "Firebase Admin not initialized (%s). Auth/admin endpoints will be disabled. "
            "The VRPTW demo solver still works.",
            exc,
        )
        return None


def get_db() -> firestore.Client:
    db = init_firebase()
    if db is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Firebase is not configured. Set FIREBASE_SERVICE_ACCOUNT_PATH or "
                "FIREBASE_SERVICE_ACCOUNT_JSON in .env to enable auth/admin features. "
                f"Last error: {_init_error or 'no credentials provided'}"
            ),
        )
    return db


def is_firebase_enabled() -> bool:
    return init_firebase() is not None


def _build_firebase_app() -> firebase_admin.App | None:
    options: dict[str, str] = {}
    project_id = firebase_project_id()
    if project_id:
        options["projectId"] = project_id

    account_json = firebase_service_account_json()
    if account_json:
        info = json.loads(account_json)
        return firebase_admin.initialize_app(credentials.Certificate(info), options=options or None)

    account_path = firebase_service_account_path()
    if account_path:
        if not Path(account_path).exists():
            logger.warning(
                "FIREBASE_SERVICE_ACCOUNT_PATH points to %s but the file does not exist.",
                account_path,
            )
            return None
        return firebase_admin.initialize_app(credentials.Certificate(account_path), options=options or None)

    logger.info(
        "No Firebase credentials found in environment. Skipping Firebase init "
        "(set FIREBASE_SERVICE_ACCOUNT_PATH or FIREBASE_SERVICE_ACCOUNT_JSON to enable)."
    )
    return None
