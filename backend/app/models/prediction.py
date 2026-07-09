import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Integer, Float, ForeignKey, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.project import Project
from app.database.enums import PredictionModel


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    prediction_model: Mapped[PredictionModel] = mapped_column(Enum(PredictionModel), nullable=False)
    prediction_year: Mapped[int] = mapped_column(Integer, nullable=False)
    predicted_temperature: Mapped[float] = mapped_column(nullable=False)  # in Celsius or Kelvin? We'll use Celsius for simplicity
    confidence: Mapped[float] = mapped_column(nullable=False)  # between 0 and 1

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    project: Mapped[Project] = relationship(back_populates="predictions")

    def __repr__(self) -> str:
        return f"<Prediction(id={self.id}, project_id='{self.project_id}', model='{self.prediction_model}', year={self.prediction_year})>"