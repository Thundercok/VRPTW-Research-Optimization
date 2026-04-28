"""Security helpers: argon2 password hashing with legacy SHA-256 fallback.

Why both schemes?
- Existing user records in Firestore were created using a raw SHA-256 hash.
  We keep accepting them so logins do not break, but every successful login
  triggers a transparent re-hash to argon2 via ``needs_upgrade``.
- New registrations and password resets always store argon2 hashes.

Tokens (auth_tokens) and OTP codes are still SHA-256 hashed; those are short-
lived secrets so a fast hash is fine, and we prefer to store hashes server-
side so a database leak does not yield raw tokens.
"""

from __future__ import annotations

import hashlib
import re

from passlib.context import CryptContext

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
VALID_ROLES = {"operator", "admin", "viewer"}

_LEGACY_SHA256 = re.compile(r"^[0-9a-f]{64}$")

_pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__time_cost=2,
    argon2__memory_cost=64 * 1024,  # 64 MiB
    argon2__parallelism=2,
)


def hash_password(raw: str) -> str:
    """Hash a plain password using argon2."""
    return _pwd_context.hash(raw)


def verify_password(raw: str, stored_hash: str) -> bool:
    """Verify a password against either an argon2 hash or a legacy SHA-256 hash."""
    if not stored_hash:
        return False
    if _LEGACY_SHA256.fullmatch(stored_hash):
        return hashlib.sha256(raw.encode("utf-8")).hexdigest() == stored_hash
    try:
        return _pwd_context.verify(raw, stored_hash)
    except Exception:
        return False


def needs_upgrade(stored_hash: str) -> bool:
    """Return True if ``stored_hash`` should be re-hashed (legacy or weak parameters)."""
    if not stored_hash:
        return True
    if _LEGACY_SHA256.fullmatch(stored_hash):
        return True
    try:
        return _pwd_context.needs_update(stored_hash)
    except Exception:
        return True


def hash_token(raw: str) -> str:
    """Deterministic hash for short-lived tokens (OTP, session token)."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_PATTERN.fullmatch(email.strip()))


def is_valid_role(role: str) -> bool:
    return role in VALID_ROLES
