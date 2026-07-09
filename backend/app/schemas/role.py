import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.database.enums import UserRole


class RoleRead(BaseModel):
    id: uuid.UUID = Field(..., description="Unique role identifier")
    name: UserRole = Field(..., description="Role name from system enum")
    description: Optional[str] = Field(default=None, description="Optional role description")

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "administrator",
                "description": "Administrator with full system access",
            }
        },
    )


class RoleAssign(BaseModel):
    user_id: uuid.UUID = Field(..., description="UUID of the user to assign")
    role_id: uuid.UUID = Field(..., description="UUID of the role to assign")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "role_id": "660e8400-e29b-41d4-a716-446655440001",
            }
        },
    )
