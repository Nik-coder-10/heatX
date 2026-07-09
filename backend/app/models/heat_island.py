import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Float, Integer, ForeignKey, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry

from app.core.database import Base
from app.models.project import Project
from app.database.enums import SeverityLevel


class HeatIsland(Base):
    __tablename__ = "heat_islands"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    geometry: Mapped[Optional[Geometry]] = mapped_column(Geometry("POLYGON", srid=4326), nullable=True)
    severity: Mapped[SeverityLevel] = mapped_column(Enum(SeverityLevel), nullable=False)
    average_temperature: Mapped[float] = mapped_column(nullable=False)  # in Celsius or Kelvin? We'll use Celsius for ease
    affected_population: Mapped[int] = mapped_column(Integer, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    project: Mapped[Project] = relationship(back_populates="heat_islands")

    def __repr__(self) -> str:
        return f"<HeatIsland(id={self.id}, project_id='{self.project_id}', severity='{self.severity}')>"