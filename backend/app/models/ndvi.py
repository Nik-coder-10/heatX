import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.processed_image import ProcessedImage


class NDVIResult(Base):
    __tablename__ = "ndvi_results"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, nullable=False
    )
    processed_image_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("processed_images.id"), nullable=False)
    mean_ndvi: Mapped[float] = mapped_column(nullable=False)
    max_ndvi: Mapped[float] = mapped_column(nullable=False)
    min_ndvi: Mapped[float] = mapped_column(nullable=False)
    output_file: Mapped[str] = mapped_column(String(500), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    processed_image: Mapped[ProcessedImage] = relationship(back_populates="ndvi_result")

    def __repr__(self) -> str:
        return f"<NDVIResult(id={self.id}, processed_image_id='{self.processed_image_id}', mean_ndvi={self.mean_ndvi})>"