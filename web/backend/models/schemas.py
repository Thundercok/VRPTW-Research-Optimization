from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field


class AuthRequest(BaseModel):
    email: str
    password: str


class RegisterOTPRequest(BaseModel):
    email: str


class RegisterConfirmRequest(BaseModel):
    email: str
    password: str
    otp: str


class RegisterVerifyRequest(BaseModel):
    email: str
    otp: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ForgotPasswordResetRequest(BaseModel):
    token: str
    new_password: str


class RequiredPasswordChangeRequest(BaseModel):
    new_password: str


class RoleUpdateRequest(BaseModel):
    role: str


class AdminCreateUserRequest(BaseModel):
    email: str
    password: str
    role: str = "operator"
    must_change_password: bool = True


class Point(BaseModel):
    id: int | None = None
    name: str = ""
    address: str = ""
    lat: float
    lng: float
    demand: int = 0
    isDepot: bool = False


class FleetConfig(BaseModel):
    vehicles: int = Field(ge=1, le=200)
    capacity: int = Field(ge=1, le=10_000)


class MatrixPoint(BaseModel):
    lat: float
    lng: float


class MatrixRequest(BaseModel):
    points: list[MatrixPoint]


class JobRequest(BaseModel):
    mode: str = "sample"
    fleet: FleetConfig
    customers: list[Point]


@dataclass
class JobState:
    status: str
    payload: JobRequest | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    debug: dict[str, Any] | None = None
