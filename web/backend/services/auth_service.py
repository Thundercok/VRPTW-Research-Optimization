from __future__ import annotations

import secrets
import time
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from core.config import ACCESS_TOKEN_TTL_SEC, REGISTER_OTP_TTL_SEC, RESET_TOKEN_TTL_SEC, frontend_reset_url
from core.security import hash_password, hash_token, is_valid_email, is_valid_role
from database.repositories import otp_repo, token_repo, users_repo
from services.mail_service import send_email


def _build_otp_email_html(otp: str) -> str:
    return f"""
<!doctype html>
<html>
    <body style=\"margin:0;padding:0;background:#f3f6fb;font-family:Segoe UI,Arial,sans-serif;color:#1f2a37;\">
        <table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"padding:24px 0;\">
            <tr>
                <td align=\"center\">
                    <table role=\"presentation\" width=\"640\" cellpadding=\"0\" cellspacing=\"0\" style=\"background:#ffffff;border-radius:14px;overflow:hidden;box-shadow:0 10px 30px rgba(15,39,64,0.12);\">
                        <tr>
                            <td>
                                <img src=\"https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?auto=format&fit=crop&w=1200&q=80\" alt=\"Smart logistics delivery fleet\" width=\"640\" style=\"display:block;width:100%;height:auto;\" />
                            </td>
                        </tr>
                        <tr>
                            <td style=\"padding:28px 30px 22px 30px;\">
                                <h2 style=\"margin:0 0 10px 0;color:#0f2740;\">VRPTW Registration Verification</h2>
                                <p style=\"margin:0 0 14px 0;line-height:1.6;\">Hello,</p>
                                <p style=\"margin:0 0 16px 0;line-height:1.6;\">Thank you for registering with the VRPTW Dispatch Portal. Please use the one-time password below to verify your email address:</p>
                                <p style=\"margin:0 0 18px 0;text-align:center;\">
                                    <span style=\"display:inline-block;letter-spacing:8px;font-size:30px;font-weight:700;color:#0f2740;background:#eef5ff;border:1px solid #c9d9f2;border-radius:10px;padding:12px 18px;\">{otp}</span>
                                </p>
                                <p style=\"margin:0 0 8px 0;line-height:1.6;\">This OTP will expire in <strong>10 minutes</strong>.</p>
                                <p style=\"margin:0 0 8px 0;line-height:1.6;\">If you did not request this, please ignore this email.</p>
                                <p style=\"margin:14px 0 0 0;line-height:1.6;\">Best regards,<br/>VRPTW Dispatch Support Team</p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
</html>
""".strip()


def _build_temp_password_email_html(temp_password: str) -> str:
    return f"""
<!doctype html>
<html>
    <body style=\"margin:0;padding:0;background:#f3f6fb;font-family:Segoe UI,Arial,sans-serif;color:#1f2a37;\">
        <table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"padding:24px 0;\">
            <tr>
                <td align=\"center\">
                    <table role=\"presentation\" width=\"640\" cellpadding=\"0\" cellspacing=\"0\" style=\"background:#ffffff;border-radius:14px;overflow:hidden;box-shadow:0 10px 30px rgba(15,39,64,0.12);\">
                        <tr>
                            <td>
                                <img src=\"https://images.unsplash.com/photo-1489515217757-5fd1be406fef?auto=format&fit=crop&w=1200&q=80\" alt=\"Secure operations dashboard\" width=\"640\" style=\"display:block;width:100%;height:auto;\" />
                            </td>
                        </tr>
                        <tr>
                            <td style=\"padding:28px 30px 24px 30px;\">
                                <h2 style=\"margin:0 0 10px 0;color:#0f2740;\">Temporary Password Issued</h2>
                                <p style=\"margin:0 0 14px 0;line-height:1.6;\">Hello,</p>
                                <p style=\"margin:0 0 16px 0;line-height:1.6;\">We received your password reset request. Your temporary password is:</p>
                                <p style=\"margin:0 0 18px 0;text-align:center;\">
                                    <span style=\"display:inline-block;letter-spacing:2px;font-size:22px;font-weight:700;color:#0f2740;background:#eef5ff;border:1px solid #c9d9f2;border-radius:10px;padding:12px 18px;\">{temp_password}</span>
                                </p>
                                <p style=\"margin:0 0 8px 0;line-height:1.6;\">For security, you must change this temporary password immediately after login.</p>
                                <p style=\"margin:0 0 8px 0;line-height:1.6;\">If you did not request this, contact support right away.</p>
                                <p style=\"margin:14px 0 0 0;line-height:1.6;\">Best regards,<br/>VRPTW Dispatch Support Team</p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
</html>
""".strip()


def issue_token(email: str) -> str:
    access = str(uuid4())
    now = int(time.time())
    token_repo.create_token(access, email, now, now + ACCESS_TOKEN_TTL_SEC)
    return access


def get_user_by_token(token: str) -> dict[str, str]:
    row = token_repo.find_valid_token(token, int(time.time()))
    if not row:
        raise HTTPException(status_code=401, detail="Invalid token")
    email = str(row["email"])

    row = users_repo.find_user_by_email(email)
    if not row:
        raise HTTPException(status_code=401, detail="User not found")
    return {"email": row["email"], "role": row["role"]}


def request_register_otp(email: str) -> dict[str, str]:
    email = email.strip().lower()
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    existed = users_repo.find_user_by_email(email)
    if existed:
        raise HTTPException(status_code=409, detail="User already exists")

    otp = f"{secrets.randbelow(1_000_000):06d}"
    now = int(time.time())
    otp_repo.upsert_register_otp(email, hash_token(
        otp), now + REGISTER_OTP_TTL_SEC, now)

    delivery = send_email(
        email,
        "[VRPTW] Registration OTP",
        (
            "Dear user,\\n\\n"
            f"Your registration OTP is: {otp}\\n"
            "This code expires in 10 minutes.\\n\\n"
            "If you did not request this code, please ignore this email.\\n\\n"
            "Best regards,\\nVRPTW Dispatch Support Team"
        ),
        _build_otp_email_html(otp),
    )
    return {"message": "otp_sent", "delivery": delivery}


def verify_register_otp(email: str, otp: str) -> dict[str, str | bool]:
    email = email.strip().lower()
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    if not otp or not otp.strip():
        raise HTTPException(status_code=400, detail="OTP is required")

    now = int(time.time())
    otp_row = otp_repo.find_register_otp(email)
    if not otp_row:
        raise HTTPException(status_code=400, detail="OTP not requested")
    if now > int(otp_row["expires_at"]):
        raise HTTPException(status_code=400, detail="OTP expired")
    if hash_token(otp.strip()) != otp_row["otp_hash"]:
        raise HTTPException(status_code=400, detail="OTP invalid")

    return {"message": "otp_verified", "verified": True}


def register_user(email: str, password: str, otp: str) -> dict[str, str]:
    email = email.strip().lower()
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    if len(password) < 6:
        raise HTTPException(
            status_code=400, detail="Password must be at least 6 characters")

    now = int(time.time())
    existed = users_repo.find_user_by_email(email)
    if existed:
        raise HTTPException(status_code=409, detail="User already exists")

    otp_row = otp_repo.find_register_otp(email)
    if not otp_row:
        raise HTTPException(status_code=400, detail="OTP not requested")
    if now > int(otp_row["expires_at"]):
        raise HTTPException(status_code=400, detail="OTP expired")
    if hash_token(otp.strip()) != otp_row["otp_hash"]:
        raise HTTPException(status_code=400, detail="OTP invalid")

    users_repo.create_user(email, hash_password(password), "operator", now)
    otp_repo.delete_register_otp(email)

    return {"message": "registered", "role": "operator"}


def login_user(email: str, password: str) -> dict[str, str | bool]:
    email = email.strip().lower()
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    row = users_repo.find_user_by_email(email)
    if not row or row["password_hash"] != hash_password(password):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password. Check your credentials and try again. If you forgot your password, use 'Forgot Password' option."
        )

    access_token = issue_token(email)
    users_repo.record_user_event(email, "login", source="backend-login")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": row["role"],
        "must_change_password": bool(row.get("must_change_password", False)),
    }


def logout_user(email: str, token: str | None = None) -> dict[str, str]:
    if token:
        token_repo.delete_token(token)
    users_repo.record_user_event(email, "logout", source="backend-logout")
    return {"message": "logged_out"}


def request_password_reset(email: str) -> dict[str, str]:
    email = email.strip().lower()
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    row = users_repo.find_user_by_email(email)
    if not row:
        raise HTTPException(status_code=404, detail="Email not found")

    temp_password = secrets.token_urlsafe(9)
    users_repo.update_user_password(
        email,
        hash_password(temp_password),
        must_change_password=True,
    )

    delivery = send_email(
        email,
        "[VRPTW] Temporary password",
        (
            "Dear user,\\n\\n"
            f"Your temporary password is: {temp_password}\\n"
            "Please login and change your password immediately.\\n"
            "If you did not request this, contact support immediately.\\n\\n"
            "Best regards,\\nVRPTW Dispatch Support Team"
        ),
        _build_temp_password_email_html(temp_password),
    )
    return {"message": "temporary_password_sent", "delivery": delivery}


def validate_password_reset_token(token: str) -> dict[str, bool]:
    token_hash = hash_token(token)
    now = int(time.time())
    row = otp_repo.find_valid_password_reset_token(token_hash, now)
    return {"valid": bool(row)}


def reset_password(token: str, new_password: str) -> dict[str, str]:
    if len(new_password) < 6:
        raise HTTPException(
            status_code=400, detail="Password must be at least 6 characters")

    token_hash = hash_token(token.strip())
    now = int(time.time())

    row = otp_repo.find_password_reset_token(token_hash)
    if not row:
        raise HTTPException(status_code=400, detail="Invalid reset token")
    if int(row["used"]) == 1:
        raise HTTPException(status_code=400, detail="Reset token already used")
    if now > int(row["expires_at"]):
        raise HTTPException(status_code=400, detail="Reset token expired")

    users_repo.update_user_password(row["email"], hash_password(new_password))
    otp_repo.mark_password_reset_token_used(token_hash)

    return {"message": "password_reset_done"}


def change_required_password(user: dict[str, str], new_password: str) -> dict[str, str]:
    if len(new_password) < 6:
        raise HTTPException(
            status_code=400, detail="Password must be at least 6 characters")

    target_email = user["email"].strip().lower()
    row = users_repo.find_user_by_email(target_email)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    if not bool(row.get("must_change_password", False)):
        raise HTTPException(status_code=400, detail="Password change is not required")

    users_repo.update_user_password(
        target_email,
        hash_password(new_password),
        must_change_password=False,
    )
    return {"message": "required_password_changed"}


def list_users() -> dict[str, Any]:
    return users_repo.list_users()


def list_user_activity(email: str, limit: int = 10) -> dict[str, Any]:
    target_email = email.strip().lower()
    if not is_valid_email(target_email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    row = users_repo.find_user_by_email(target_email)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return users_repo.list_user_activity(target_email, limit)


def admin_create_user(email: str, password: str, role: str, must_change_password: bool = True) -> dict[str, str]:
    target_email = email.strip().lower()
    if not is_valid_email(target_email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if not is_valid_role(role):
        raise HTTPException(status_code=400, detail="Invalid role")
    if users_repo.find_user_by_email(target_email):
        raise HTTPException(status_code=409, detail="User already exists")

    now = int(time.time())
    users_repo.create_user(
        target_email,
        hash_password(password),
        role,
        now,
        must_change_password=must_change_password,
    )
    return {"message": "user_created", "email": target_email, "role": role}


def update_user_role(email: str, role: str) -> dict[str, str]:
    target_email = email.strip().lower()
    if not is_valid_email(target_email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    if not is_valid_role(role):
        raise HTTPException(status_code=400, detail="Invalid role")

    row = users_repo.find_user_by_email(target_email)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    users_repo.update_user_role(target_email, role)

    return {"message": "role_updated", "email": target_email, "role": role}


def delete_user(email: str) -> dict[str, str]:
    target_email = email.strip().lower()
    if not is_valid_email(target_email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    row = users_repo.find_user_by_email(target_email)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    users_repo.delete_user(target_email)

    return {"message": "user_deleted", "email": target_email}

