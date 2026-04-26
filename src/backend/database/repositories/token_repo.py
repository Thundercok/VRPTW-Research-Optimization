from __future__ import annotations

from core.firebase import get_db


def _tokens_collection():
    return get_db().collection("auth_tokens")


def create_token(token: str, email: str, created_at: int, expires_at: int) -> None:
    _tokens_collection().document(token).set(
        {
            "token": token,
            "email": email,
            "created_at": int(created_at),
            "expires_at": int(expires_at),
        }
    )


def find_valid_token(token: str, now_ts: int):
    snap = _tokens_collection().document(token).get()
    if not snap.exists:
        return None
    row = snap.to_dict() or {}
    if int(row.get("expires_at", 0)) < int(now_ts):
        return None
    return row


def delete_token(token: str) -> None:
    _tokens_collection().document(token).delete()
