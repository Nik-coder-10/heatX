import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.processed_image import ProcessedImage


class LSTResult(Base):
    __tablename__ = "lst_results"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, nullable=False
    )
    processed_image_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("processed_images.id"), nullable=False)
    average_temperature: Mapped[float] = mapped_column(nullable=False)  # in Kelvin or Celsius? We'll use Kelvin as per standard
    maximum_temperature: Mapped[float] = mapped_column(nullable=False)
    minimum_temperature: Mapped[float] = mapped_column(nullable=False)
    heatmap_file: Mapped[str] = mapped_column(String(500), nullable=False)  # Path to the heatmap image

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    processed_image: Mapped[ProcessedImage] = relationship(back_populates="lst_result")

    def __repr__(self) -> str:
        return f"<LSTResult(id={self.id}, processed_image_id='{self.processed_image_id}', average_temperature={self.average_temperature})>"