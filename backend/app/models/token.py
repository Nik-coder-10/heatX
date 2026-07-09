import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, nullable=False
    )
    token_jti: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)  # JWT ID
    token_type: Mapped[str] = mapped_column(String(20), nullable=False)  # access or refresh
    blacklisted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<TokenBlacklist(id={self.id}, token_jti='{self.token_jti}', token_type='{self.token_type}')>"