import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.project import Project


class Simulation(Base):
    __tablename__ = "simulations"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    scenario_name: Mapped[str] = mapped_column(String(255), nullable=False)
    input_parameters: Mapped[dict] = mapped_column(JSON, nullable=False)
    predicted_results: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    project: Mapped[Project] = relationship(back_populates="simulations")

    def __repr__(self) -> str:
        return f"<Simulation(id={self.id}, project_id='{self.project_id}', scenario='{self.scenario_name}')>"