import re
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.auth import Token
from app.schemas.common import Pagination
from app.schemas.role import RoleRead


def _validate_name(v: str, field_name: str) -> str:
    if len(v) < 2 or len(v) > 50:
        raise ValueError(f"{field_name} must be between 2 and 50 characters")
    if not re.match(r"^[A-Za-z]+$", v):
        raise ValueError(f"{field_name} must contain only letters")
    return v


def _validate_username(v: str) -> str:
    if len(v) < 3 or len(v) > 30:
        raise ValueError("Username must be between 3 and 30 characters")
    if not re.match(r"^[a-z][a-z0-9_]{2,29}$", v):
        raise ValueError(
            "Username must start with a letter and contain only "
            "lowercase letters, numbers, and underscores"
        )
    return v


def _validate_password(v: str) -> str:
    if len(v) < 12:
        raise ValueError("Password must be at least 12 characters long")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", v):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", v):
        raise ValueError("Password must contain at least one digit")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
        raise ValueError("Password must contain at least one special character")
    return v


def _validate_phone(v: Optional[str]) -> Optional[str]:
    if v is not None:
        if not re.match(r"^\+[1-9]\d{1,14}$", v):
            raise ValueError(
                "Phone must be in E.164 format (e.g. +1234567890)"
            )
    return v


class UserCreate(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50, description="User first name")
    last_name: str = Field(..., min_length=2, max_length=50, description="User last name")
    username: str = Field(..., min_length=3, max_length=30, description="Unique username")
    email: EmailStr = Field(..., description="User email address")
    phone: Optional[str] = Field(default=None, description="Phone number in E.164 format")
    password: str = Field(..., min_length=12, max_length=128, description="Strong password")

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, v: str) -> str:
        return _validate_name(v, "First name")

    @field_validator("last_name")
    @classmethod
    def validate_last_name(cls, v: str) -> str:
        return _validate_name(v, "Last name")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        return _validate_username(v)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        return _validate_phone(v)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password(v)

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "username": "johndoe",
                "email": "john@example.com",
                "phone": "+1234567890",
                "password": "SecureP@ss1234",
            }
        },
    )


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=2, max_length=50, description="User first name")
    last_name: Optional[str] = Field(default=None, min_length=2, max_length=50, description="User last name")
    username: Optional[str] = Field(default=None, min_length=3, max_length=30, description="Unique username")
    email: Optional[EmailStr] = Field(default=None, description="User email address")
    phone: Optional[str] = Field(default=None, description="Phone number in E.164 format")
    is_verified: Optional[bool] = Field(default=None, description="Email verification status (admin)")
    is_active: Optional[bool] = Field(default=None, description="Account active status (admin)")
    role_ids: Optional[list[uuid.UUID]] = Field(default=None, description="List of role UUIDs to assign (admin)")

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return _validate_name(v, "First name")
        return v

    @field_validator("last_name")
    @classmethod
    def validate_last_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return _validate_name(v, "Last name")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return _validate_username(v)
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        return _validate_phone(v)

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "first_name": "Jane",
                "last_name": "Smith",
                "username": "janesmith",
                "email": "jane@example.com",
                "phone": "+1987654321",
            }
        },
    )


class UserSummary(BaseModel):
    id: uuid.UUID = Field(..., description="Unique user identifier")
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., description="Unique username")
    first_name: str = Field(..., description="User first name")
    last_name: str = Field(..., description="User last name")

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "john@example.com",
                "username": "johndoe",
                "first_name": "John",
                "last_name": "Doe",
            }
        },
    )


class UserRead(BaseModel):
    id: uuid.UUID = Field(..., description="Unique user identifier")
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., description="Unique username")
    first_name: str = Field(..., description="User first name")
    last_name: str = Field(..., description="User last name")
    phone: Optional[str] = Field(default=None, description="Phone number in E.164 format")
    is_verified: bool = Field(..., description="Whether email is verified")
    is_active: bool = Field(..., description="Whether account is active")
    last_login: Optional[datetime] = Field(default=None, description="Last login timestamp")
    roles: list[RoleRead] = Field(default_factory=list, description="Assigned roles")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "john@example.com",
                "username": "johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "phone": "+1234567890",
                "is_verified": True,
                "is_active": True,
                "last_login": "2024-07-01T12:00:00Z",
                "roles": [
                    {
                        "id": "660e8400-e29b-41d4-a716-446655440001",
                        "name": "researcher",
                        "description": "Researcher role",
                    }
                ],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-07-01T12:00:00Z",
            }
        },
    )


class AuditLogRead(BaseModel):
    id: uuid.UUID = Field(..., description="Unique audit log identifier")
    user_id: Optional[uuid.UUID] = Field(default=None, description="UUID of the acting user")
    action: str = Field(..., description="Action performed")
    resource: str = Field(..., description="Resource acted upon")
    ip_address: Optional[str] = Field(default=None, description="Client IP address")
    user_agent: Optional[str] = Field(default=None, description="Client user agent string")
    details: Optional[dict] = Field(default=None, description="Additional audit details")
    timestamp: datetime = Field(..., description="When the action occurred")

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "660e8400-e29b-41d4-a716-446655440001",
                "action": "user.login",
                "resource": "auth",
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0...",
                "details": {"method": "password"},
                "timestamp": "2024-07-01T12:00:00Z",
            }
        },
    )


# Backward-compatible alias for auth endpoints
UserToken = Token

# Backward-compatible response schema for auth endpoints
class UserResponse(UserRead):
    pass


class PaginatedUserResponse(BaseModel):
    items: list[UserRead] = Field(..., description="List of users")
    pagination: Pagination = Field(..., description="Pagination metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "email": "john@example.com",
                        "username": "johndoe",
                        "first_name": "John",
                        "last_name": "Doe",
                        "phone": "+1234567890",
                        "is_verified": True,
                        "is_active": True,
                        "last_login": "2024-07-01T12:00:00Z",
                        "roles": [],
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-07-01T12:00:00Z",
                    }
                ],
                "pagination": {
                    "page": 1,
                    "page_size": 20,
                    "total": 1,
                    "total_pages": 1,
                },
            }
        },
    )
