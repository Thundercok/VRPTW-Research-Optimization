from __future__ import annotations

from core.firebase import get_db, init_firebase


def init_db() -> None:
    init_firebase()


def open_db():
    return get_db()
