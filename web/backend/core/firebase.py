from __future__ import annotations

import json

import firebase_admin
from firebase_admin import credentials, firestore

from core.config import firebase_project_id, firebase_service_account_json, firebase_service_account_path

_db: firestore.Client | None = None


def init_firebase() -> firestore.Client:
    global _db
    if _db is not None:
        return _db

    app = firebase_admin.get_app() if firebase_admin._apps else _build_firebase_app()
    _db = firestore.client(app=app)
    return _db


def get_db() -> firestore.Client:
    return init_firebase()


def _build_firebase_app() -> firebase_admin.App:
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
        return firebase_admin.initialize_app(credentials.Certificate(account_path), options=options or None)

    return firebase_admin.initialize_app(options=options or None)
