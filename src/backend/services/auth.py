from __future__ import annotations
from typing import Any
from core.firebase import is_firebase_enabled

class _AuthService:
    def list_users(self) -> dict[str, Any]:
        if not is_firebase_enabled():
            return {"users": []}
        from firebase_admin import auth
        page = auth.list_users()
        return {"users": [
            {"email": u.email, "uid": u.uid, "disabled": u.disabled}
            for u in page.users
        ]}

    def update_user_role(self, email: str, role: str) -> dict[str, str]:
        if not is_firebase_enabled():
            return {"email": email, "role": role}
        from firebase_admin import auth
        user = auth.get_user_by_email(email)
        auth.set_custom_user_claims(user.uid, {"role": role})
        return {"email": email, "role": role}

    def delete_user(self, email: str) -> dict[str, str]:
        if not is_firebase_enabled():
            return {"deleted": email}
        from firebase_admin import auth
        user = auth.get_user_by_email(email)
        auth.delete_user(user.uid)
        return {"deleted": email}

auth_service = _AuthService()