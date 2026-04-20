from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, Query

from api.dependencies import require_user
from models.schemas import AuthRequest, ForgotPasswordRequest, ForgotPasswordResetRequest, RegisterConfirmRequest, RegisterOTPRequest, RegisterVerifyRequest, RequiredPasswordChangeRequest
from services import auth_service

router = APIRouter(tags=["auth"])


@router.post("/auth/register/request-otp")
async def register_request_otp(body: RegisterOTPRequest) -> dict[str, str]:
    return auth_service.request_register_otp(body.email)


@router.post("/auth/register/verify-otp")
async def register_verify_otp(body: RegisterVerifyRequest) -> dict[str, str | bool]:
    return auth_service.verify_register_otp(body.email, body.otp)


@router.post("/auth/register")
async def register(body: RegisterConfirmRequest) -> dict[str, str]:
    return auth_service.register_user(body.email, body.password, body.otp)


@router.post("/auth/token")
async def token(body: AuthRequest) -> dict[str, Any]:
    return auth_service.login_user(body.email, body.password)


@router.post("/auth/logout")
async def logout(
    authorization: str | None = Header(default=None),
    user: dict[str, str] = Depends(require_user),
) -> dict[str, str]:
    token = authorization.removeprefix("Bearer ").strip() if authorization else None
    return auth_service.logout_user(user["email"], token)


@router.post("/auth/forgot-password/request")
async def forgot_password_request(body: ForgotPasswordRequest) -> dict[str, str]:
    return auth_service.request_password_reset(body.email)


@router.get("/auth/forgot-password/validate")
async def validate_reset_token(token: str = Query(min_length=10)) -> dict[str, bool]:
    return auth_service.validate_password_reset_token(token)


@router.post("/auth/forgot-password/reset")
async def forgot_password_reset(body: ForgotPasswordResetRequest) -> dict[str, str]:
    return auth_service.reset_password(body.token, body.new_password)


@router.post("/auth/password/change-required")
async def change_required_password(
    body: RequiredPasswordChangeRequest,
    user: dict[str, str] = Depends(require_user),
) -> dict[str, str]:
    return auth_service.change_required_password(user, body.new_password)


@router.get("/auth/me")
async def auth_me(user: dict[str, str] = Depends(require_user)) -> dict[str, str]:
    return user
