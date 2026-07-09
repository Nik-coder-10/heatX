import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., min_length=1, description="User password")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "SecureP@ss1234",
            }
        },
    )


class Token(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIs...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
                "token_type": "bearer",
            }
        },
    )


class TokenRefresh(BaseModel):
    refresh_token: str = Field(..., min_length=1, description="Valid refresh token")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
            }
        },
    )


class PasswordChange(BaseModel):
    old_password: str = Field(..., min_length=1, description="Current password")
    new_password: str = Field(..., min_length=12, max_length=128, description="New password")

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
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

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "old_password": "OldP@ss1234",
                "new_password": "NewP@ss5678",
            }
        },
    )


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered email address")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "email": "user@example.com",
            }
        },
    )


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1, description="Password reset token")
    new_password: str = Field(..., min_length=12, max_length=128, description="New password")

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
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

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "token": "reset-token-abc123",
                "new_password": "NewP@ss5678",
            }
        },
    )


class VerifyEmailRequest(BaseModel):
    token: str = Field(..., min_length=1, description="Email verification token")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "token": "verify-token-abc123",
            }
        },
    )
