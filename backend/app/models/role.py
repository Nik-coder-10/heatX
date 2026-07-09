from typing import List, Optional

from sqlalchemy import String, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, BaseModel
from app.database.enums import UserRole


class Role(BaseModel, Base):
    __tablename__ = "roles"

    name: Mapped[UserRole] = mapped_column(
        Enum(UserRole), unique=True, nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    users: Mapped[List["User"]] = relationship(
        secondary="user_roles", back_populates="roles", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name='{self.name}')>"