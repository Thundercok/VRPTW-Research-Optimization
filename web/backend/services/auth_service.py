from __future__ import annotations

import secrets
import time
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from core.config import REGISTER_OTP_TTL_SEC, RESET_TOKEN_TTL_SEC, frontend_reset_url
from core.security import hash_password, hash_token, is_valid_email, is_valid_role
from database.repositories import otp_repo, users_repo
from services.mail_service import send_email

_tokens: dict[str, str] = {}


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


def _build_reset_email_html(reset_link: str) -> str:
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
                                <h2 style=\"margin:0 0 10px 0;color:#0f2740;\">Password Reset Request</h2>
                                <p style=\"margin:0 0 14px 0;line-height:1.6;\">Hello,</p>
                                <p style=\"margin:0 0 18px 0;line-height:1.6;\">We received a request to reset your VRPTW Dispatch Portal password. Please use the secure link below:</p>
                                <p style=\"margin:0 0 18px 0;\"><a href=\"{reset_link}\" style=\"display:inline-block;background:#0f2740;color:#ffffff;text-decoration:none;padding:12px 18px;border-radius:9px;font-weight:600;\">Reset Password</a></p>
                                <p style=\"margin:0 0 8px 0;line-height:1.6;\">This link expires in <strong>15 minutes</strong>.</p>
                                <p style=\"margin:0 0 8px 0;line-height:1.6;\">If you did not request a password reset, please ignore this message.</p>
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
    _tokens[access] = email
    return access


def get_user_by_token(token: str) -> dict[str, str]:
    email = _tokens.get(token)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token")

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


def login_user(email: str, password: str) -> dict[str, str]:
    email = email.strip().lower()
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    row = users_repo.find_user_by_email(email)
    if not row or row["password_hash"] != hash_password(password):
        raise HTTPException(status_code=401, detail="Bad credentials")

    access_token = issue_token(email)
    return {"access_token": access_token, "token_type": "bearer", "role": row["role"]}


def request_password_reset(email: str) -> dict[str, str]:
    email = email.strip().lower()
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    row = users_repo.find_user_by_email(email)
    if not row:
        raise HTTPException(status_code=404, detail="Email not found")

    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_token(raw_token)
    now = int(time.time())
    otp_repo.replace_password_reset_token(
        email, token_hash, now + RESET_TOKEN_TTL_SEC, now)

    reset_link = frontend_reset_url(raw_token)
    delivery = send_email(
        email,
        "[VRPTW] Password reset link",
        (
            "Dear user,\\n\\n"
            "Use the following secure link to reset your password:\\n"
            f"{reset_link}\\n\\n"
            "This link expires in 15 minutes.\\n"
            "If you did not request this, you can safely ignore this email.\\n\\n"
            "Best regards,\\nVRPTW Dispatch Support Team"
        ),
        _build_reset_email_html(reset_link),
    )
    return {"message": "reset_link_sent", "delivery": delivery}


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


def list_users() -> dict[str, Any]:
    return users_repo.list_users()


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
