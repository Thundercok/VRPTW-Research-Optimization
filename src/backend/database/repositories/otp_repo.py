from __future__ import annotations

from core.firebase import get_db


def _register_otps_collection():
    return get_db().collection("register_otps")


def _reset_tokens_collection():
    return get_db().collection("password_reset_tokens")


def upsert_register_otp(email: str, otp_hash: str, expires_at: int, requested_at: int) -> None:
    _register_otps_collection().document(email).set(
        {
            "email": email,
            "otp_hash": otp_hash,
            "expires_at": int(expires_at),
            "requested_at": int(requested_at),
        }
    )


def find_register_otp(email: str):
    snap = _register_otps_collection().document(email).get()
    if not snap.exists:
        return None
    return snap.to_dict()


def delete_register_otp(email: str) -> None:
    _register_otps_collection().document(email).delete()


def replace_password_reset_token(email: str, token_hash: str, expires_at: int, created_at: int) -> None:
    existing = _reset_tokens_collection().where("email", "==", email).stream()
    for snap in existing:
        snap.reference.delete()
    _reset_tokens_collection().document(token_hash).set(
        {
            "token_hash": token_hash,
            "email": email,
            "expires_at": int(expires_at),
            "used": 0,
            "created_at": int(created_at),
        }
    )


def find_valid_password_reset_token(token_hash: str, now_ts: int):
    snap = _reset_tokens_collection().document(token_hash).get()
    if not snap.exists:
        return None
    row = snap.to_dict() or {}
    if int(row.get("used", 0)) == 0 and int(row.get("expires_at", 0)) >= int(now_ts):
        return row
    return None


def find_password_reset_token(token_hash: str):
    snap = _reset_tokens_collection().document(token_hash).get()
    if not snap.exists:
        return None
    return snap.to_dict()


def mark_password_reset_token_used(token_hash: str) -> None:
    _reset_tokens_collection().document(token_hash).update({"used": 1})
