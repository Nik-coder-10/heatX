import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, BaseModel


class User(BaseModel, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    roles: Mapped[List["Role"]] = relationship(
        secondary="user_roles", back_populates="users", lazy="selectin"
    )
    projects: Mapped[List["Project"]] = relationship(back_populates="owner")
    reports: Mapped[List["Report"]] = relationship(back_populates="generator")
    audit_logs: Mapped[List["AuditLog"]] = relationship(back_populates="user", lazy="selectin")

    def __repr__(self) -> str:
        return (
            f"<User(id={self.id}, email='{self.email}', "
            f"username='{self.username}')>"
        )
