from core.config import demo_auth_bypass_enabled
from core.firebase import init_firebase
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth

security = HTTPBearer(auto_error=False)


async def require_user(cred: HTTPAuthorizationCredentials = Depends(security)) -> dict[str, str]:
    if demo_auth_bypass_enabled():
        # Fallback to anonymous admin/operator during local demo run / tests
        uid = "demo-operator"
        email = "demo@vrptw.local"
        role = "admin"  # Make admin so feedback and admin views are functional in demo mode

        if cred and cred.credentials:
            try:
                init_firebase()
                decoded_token = auth.verify_id_token(cred.credentials)
                uid = decoded_token.get("uid", uid)
                email = decoded_token.get("email", email)
            except Exception:
                pass
        return {
            "uid": uid,
            "email": email,
            "role": role,
        }

    if not cred or not cred.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    init_firebase()
    try:
        decoded_token = auth.verify_id_token(cred.credentials)
        return {
            "uid": decoded_token.get("uid"),
            "email": decoded_token.get("email"),
            "role": "operator",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase ID token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
