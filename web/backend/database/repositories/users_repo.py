from __future__ import annotations

from typing import Any

from core.firebase import get_db


def _users_collection():
    return get_db().collection("users")


def find_user_by_email(email: str):
    snap = _users_collection().document(email).get()
    if not snap.exists:
        return None
    return snap.to_dict()


def create_user(email: str, password_hash: str, role: str, created_at: int) -> None:
    _users_collection().document(email).set(
        {
            "email": email,
            "password_hash": password_hash,
            "role": role,
            "created_at": int(created_at),
            "must_change_password": False,
        }
    )


def update_user_password(email: str, password_hash: str, must_change_password: bool | None = None) -> None:
    payload: dict[str, Any] = {"password_hash": password_hash}
    if must_change_password is not None:
        payload["must_change_password"] = bool(must_change_password)
    _users_collection().document(email).update(payload)


def list_users() -> dict[str, Any]:
    snaps = _users_collection().stream()
    items = []
    for snap in snaps:
        row = snap.to_dict() or {}
        items.append(
            {
                "email": row.get("email", snap.id),
                "role": row.get("role", "operator"),
                "created_at": int(row.get("created_at", 0)),
            }
        )
    items.sort(key=lambda r: int(r["created_at"]), reverse=True)
    return {
        "items": items
    }


def update_user_role(email: str, role: str) -> None:
    _users_collection().document(email).update({"role": role})


def delete_user(email: str) -> None:
    _users_collection().document(email).delete()
