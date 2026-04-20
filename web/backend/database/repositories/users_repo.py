from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from firebase_admin import firestore

from core.firebase import get_db


def _users_collection():
    return get_db().collection("users")


def find_user_by_email(email: str):
    snap = _users_collection().document(email).get()
    if not snap.exists:
        return None
    return snap.to_dict()


def _ts_to_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    if hasattr(value, "to_datetime"):
        try:
            dt = value.to_datetime()
            dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except Exception:
            return 0
    if hasattr(value, "timestamp"):
        try:
            return int(value.timestamp())
        except Exception:
            return 0
    return 0


def _event_doc(collection_email: str):
    return _users_collection().document(collection_email).collection("events")


def create_user(email: str, password_hash: str, role: str, created_at: int, must_change_password: bool = False) -> None:
    _users_collection().document(email).set(
        {
            "email": email,
            "password_hash": password_hash,
            "role": role,
            "created_at": int(created_at),
            "must_change_password": bool(must_change_password),
        }
    )


def update_user_password(email: str, password_hash: str, must_change_password: bool | None = None) -> None:
    payload: dict[str, Any] = {"password_hash": password_hash}
    if must_change_password is not None:
        payload["must_change_password"] = bool(must_change_password)
    _users_collection().document(email).update(payload)


def record_user_event(email: str, event_type: str, source: str = "auth") -> None:
    now = int(datetime.now(tz=timezone.utc).timestamp())
    payload: dict[str, Any] = {
        "updatedAt": now,
        "lastEventType": event_type,
        "lastEventAt": now,
    }
    if event_type == "login":
        payload["lastLoginAt"] = now
    if event_type == "logout":
        payload["lastLogoutAt"] = now

    _users_collection().document(email).set(payload, merge=True)
    _event_doc(email).add(
        {
            "type": event_type,
            "source": source,
            "createdAt": now,
        }
    )


def list_user_activity(email: str, limit: int = 10) -> dict[str, Any]:
    snaps = (
        _event_doc(email)
        .order_by("createdAt", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    items = []
    for snap in snaps:
        row = snap.to_dict() or {}
        created_at = _ts_to_int(row.get("createdAt") or row.get("created_at") or row.get("timestamp"))
        items.append(
            {
                "type": row.get("type", "event"),
                "source": row.get("source", "auth"),
                "created_at": created_at,
                "meta": row.get("meta", {}),
            }
        )
    return {"items": items}


def list_users() -> dict[str, Any]:
    snaps = _users_collection().stream()
    user_map: dict[str, dict[str, Any]] = {}
    for snap in snaps:
        row = snap.to_dict() or {}
        email = str(row.get("email") or snap.id).strip().lower()
        if not email:
            continue

        existing = user_map.get(email)
        last_login_at = _ts_to_int(row.get("lastLoginAt") or row.get("last_login_at"))
        last_logout_at = _ts_to_int(row.get("lastLogoutAt") or row.get("last_logout_at"))
        last_event_at = _ts_to_int(row.get("lastEventAt") or row.get("last_event_at"))
        created_at = _ts_to_int(row.get("created_at") or row.get("createdAt"))
        must_change_password = bool(row.get("must_change_password", False))
        status = "online" if last_login_at and last_login_at >= last_logout_at else "offline"

        next_item = {
            "email": email,
            "role": row.get("role", "operator"),
            "created_at": created_at,
            "must_change_password": must_change_password,
            "last_login_at": last_login_at,
            "last_logout_at": last_logout_at,
            "last_event_at": last_event_at,
            "last_event_type": row.get("lastEventType") or row.get("last_event_type") or "-",
            "status": status,
            "doc_id": snap.id,
        }

        if not existing:
            user_map[email] = next_item
            continue

        existing["created_at"] = max(int(existing.get("created_at", 0)), created_at)
        existing["last_login_at"] = max(int(existing.get("last_login_at", 0)), last_login_at)
        existing["last_logout_at"] = max(int(existing.get("last_logout_at", 0)), last_logout_at)
        existing["last_event_at"] = max(int(existing.get("last_event_at", 0)), last_event_at)
        if status == "online":
            existing["status"] = "online"
        existing["must_change_password"] = existing.get("must_change_password", False) or must_change_password
        if row.get("role"):
            existing["role"] = row.get("role", existing.get("role", "operator"))

    items = sorted(user_map.values(), key=lambda r: int(r.get("created_at", 0)), reverse=True)
    summary = {
        "total_users": len(items),
        "admins": sum(1 for item in items if item.get("role") == "admin"),
        "operators": sum(1 for item in items if item.get("role") == "operator"),
        "viewers": sum(1 for item in items if item.get("role") == "viewer"),
        "online": sum(1 for item in items if item.get("status") == "online"),
    }
    return {
        "items": items,
        "summary": summary,
    }


def update_user_role(email: str, role: str) -> None:
    _users_collection().document(email).update({"role": role})


def delete_user(email: str) -> None:
    _users_collection().document(email).delete()
