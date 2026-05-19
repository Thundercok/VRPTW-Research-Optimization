import os

import firebase_admin
from firebase_admin import credentials, firestore

_db = None

def is_firebase_enabled() -> bool:
    return bool(firebase_admin._apps)

def init_firebase():
    """Initializes Firebase Admin SDK supporting both Emulator and Prod contexts."""
    # Check if the application is explicitly directed to an emulator host
    if os.getenv("FIREBASE_AUTH_EMULATOR_HOST"):
        # The Admin SDK can initialize without explicit certificate credentials
        # when running against local emulators.
        if not firebase_admin._apps:
            firebase_admin.initialize_app(options={
                'projectId': os.getenv("FIREBASE_PROJECT_ID", "vrptw-54d81")
            })
    else:
        # Standard production credential resolution path
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.json")
        if not os.path.exists(cred_path):
            raise FileNotFoundError(f"Firebase credentials not found at path: {cred_path}")

        cred = credentials.Certificate(cred_path)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)


def get_db():
    global _db
    if _db is None:
        init_firebase()
        _db = firestore.client()
    return _db
