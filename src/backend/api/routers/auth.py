from __future__ import annotations

from typing import Any

from api.dependencies import require_user
from core.rate_limit import (
    AUTH_FORGOT_LIMIT,
    AUTH_OTP_LIMIT,
    AUTH_REGISTER_LIMIT,
    AUTH_TOKEN_LIMIT,
    limiter,
)
from fastapi import APIRouter, Depends, Query, Request
from models.schemas import (
    AuthRequest,
    ForgotPasswordRequest,
    ForgotPasswordResetRequest,
    RegisterConfirmRequest,
    RegisterOTPRequest,
    RegisterVerifyRequest,
    RequiredPasswordChangeRequest,
)
from services import auth_service

router = APIRouter(tags=["auth"])


@router.post("/auth/register/request-otp")
@limiter.limit(AUTH_OTP_LIMIT)
async def register_request_otp(request: Request, body: RegisterOTPRequest) -> dict[str, str]:
    return auth_service.request_register_otp(body.email)


@router.post("/auth/register/verify-otp")
@limiter.limit(AUTH_OTP_LIMIT)
async def register_verify_otp(request: Request, body: RegisterVerifyRequest) -> dict[str, str | bool]:
    return auth_service.verify_register_otp(body.email, body.otp)


@router.post("/auth/register")
@limiter.limit(AUTH_REGISTER_LIMIT)
async def register(request: Request, body: RegisterConfirmRequest) -> dict[str, str]:
    return auth_service.register_user(body.email, body.password, body.otp)


@router.post("/auth/token")
@limiter.limit(AUTH_TOKEN_LIMIT)
async def token(request: Request, body: AuthRequest) -> dict[str, Any]:
    return auth_service.login_user(body.email, body.password)


@router.post("/auth/forgot-password/request")
@limiter.limit(AUTH_FORGOT_LIMIT)
async def forgot_password_request(request: Request, body: ForgotPasswordRequest) -> dict[str, str]:
    return auth_service.request_password_reset(body.email)


@router.get("/auth/forgot-password/validate")
async def validate_reset_token(token: str = Query(min_length=10)) -> dict[str, bool]:
    return auth_service.validate_password_reset_token(token)


@router.post("/auth/forgot-password/reset")
@limiter.limit(AUTH_FORGOT_LIMIT)
async def forgot_password_reset(request: Request, body: ForgotPasswordResetRequest) -> dict[str, str]:
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
