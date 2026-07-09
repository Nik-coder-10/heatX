import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, JSON, String, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, BaseModel


class AuditLog(BaseModel, Base):
    __tablename__ = "audit_logs"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    resource: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[Optional["User"]] = relationship(back_populates="audit_logs")

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, user_id='{self.user_id}', "
            f"action='{self.action}', resource='{self.resource}')>"
        )
