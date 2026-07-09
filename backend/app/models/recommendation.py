import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Float, Integer, ForeignKey, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.project import Project
from app.database.enums import RecommendationType


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    recommendation_type: Mapped[RecommendationType] = mapped_column(Enum(RecommendationType), nullable=False)
    estimated_cost: Mapped[float] = mapped_column(nullable=False)  # in USD
    expected_temperature_reduction: Mapped[float] = mapped_column(nullable=False)  # in degrees Celsius
    carbon_reduction: Mapped[float] = mapped_column(nullable=False)  # in tons of CO2 equivalent per year
    priority: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 (highest) to 5 (lowest)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    project: Mapped[Project] = relationship(back_populates="recommendations")

    def __repr__(self) -> str:
        return f"<Recommendation(id={self.id}, project_id='{self.project_id}', type='{self.recommendation_type}', priority={self.priority})>"