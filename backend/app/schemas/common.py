from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class Pagination(BaseModel):
    page: int = Field(default=1, ge=1, description="Current page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Number of items per page")
    total: int = Field(default=0, ge=0, description="Total number of items")
    total_pages: int = Field(default=0, ge=0, description="Total number of pages")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "page": 1,
            "page_size": 20,
            "total": 100,
            "total_pages": 5,
        }
    })


class Metadata(BaseModel):
    key: str = Field(..., min_length=1, max_length=100, description="Metadata key")
    value: str = Field(..., description="Metadata value")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "key": "environment",
            "value": "production",
        }
    })


class APIResponse(BaseModel, Generic[T]):
    status: str = Field(default="success", description="Response status")
    message: str = Field(default="", description="Human-readable message")
    data: Optional[T] = Field(default=None, description="Response payload")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Operation completed successfully",
                "data": {},
            }
        }
    )


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error detail message")
    error_code: Optional[str] = Field(default=None, description="Machine-readable error code")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "User not found",
                "error_code": "NOT_FOUND",
            }
        }
    )
