import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.project import Project
from app.models.user import User
from app.database.enums import ReportType


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    generated_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    report_type: Mapped[ReportType] = mapped_column(Enum(ReportType), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    project: Mapped[Project] = relationship(back_populates="reports")
    generator: Mapped[User] = relationship(back_populates="reports")

    def __repr__(self) -> str:
        return f"<Report(id={self.id}, project_id='{self.project_id}', generated_by='{self.generated_by}', type='{self.report_type}')>"