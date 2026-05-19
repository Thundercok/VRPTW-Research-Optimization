from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth
from core.firebase import init_firebase

# Ensure Firebase is initialized
init_firebase()

security = HTTPBearer()

async def require_user(cred: HTTPAuthorizationCredentials = Depends(security)) -> dict[str, str]:
    """
    Intercepts the Bearer token, passes it to Firebase for cryptographic verification, 
    and returns the decoded user payload.
    """
    try:
        decoded_token = auth.verify_id_token(cred.credentials)
        return {
            "uid": decoded_token.get("uid"), 
            "email": decoded_token.get("email"), 
            "role": "operator"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase ID token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
