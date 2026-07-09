import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.satellite_image import SatelliteImage


class ProcessedImage(Base):
    __tablename__ = "processed_images"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, nullable=False
    )
    satellite_image_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("satellite_images.id"), nullable=False)
    processing_stage: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "raw", "calibrated", "georeferenced"
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    processing_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON metadata

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    satellite_image: Mapped[SatelliteImage] = relationship(back_populates="processed_images")
    ndvi_result: Mapped[Optional["NDVIResult"]] = relationship(back_populates="processed_image", uselist=False)
    ndbi_result: Mapped[Optional["NDBIResult"]] = relationship(back_populates="processed_image", uselist=False)
    lst_result: Mapped[Optional["LSTResult"]] = relationship(back_populates="processed_image", uselist=False)

    def __repr__(self) -> str:
        return f"<ProcessedImage(id={self.id}, satellite_image_id='{self.satellite_image_id}', processing_stage='{self.processing_stage}')>"