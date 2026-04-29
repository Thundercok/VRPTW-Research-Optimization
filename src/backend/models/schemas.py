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


class Point(BaseModel):
    id: int | None = None
    name: str = ""
    address: str = ""
    lat: float
    lng: float
    demand: int = 0
    isDepot: bool = False
    ready: float = 0.0
    due: float = 10_000.0
    service: float = 10.0


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


class FeedbackSubmitRequest(BaseModel):
    page: str = "feedback"
    language: str = Field(default="en", max_length=8)
    category: str = Field(default="general", max_length=40)
    message: str = Field(min_length=3, max_length=2000)
    contact: str = Field(default="", max_length=120)
    rating: int | None = Field(default=None, ge=1, le=5)


class FeedbackEntry(BaseModel):
    id: str
    created_at: int
    page: str
    language: str
    category: str
    message: str
    contact: str = ""
    rating: int | None = None
    source: str = "anonymous"
    user_agent: str = ""
    status: str = "new"


@dataclass
class JobState:
    status: str
    payload: JobRequest | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    debug: dict[str, Any] | None = None
