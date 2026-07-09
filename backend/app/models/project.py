"""Project model for the UrbanHeatAI platform."""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, DateTime, Text, ForeignKey, Enum, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user import User
from app.models.city import City
from app.database.enums import ProjectStatus, Visibility


class Project(Base):
    """Project model representing analysis projects in the system.

    Attributes:
        id: UUID primary key
        name: Project name
        description: Optional project description
        owner_id: Foreign key to the project owner (User)
        city_id: Foreign key to the associated city (City)
        status: Project status (from ProjectStatus enum)
        visibility: Project visibility (from Visibility enum)
        start_date: Optional project start date
        end_date: Optional project end date
        created_at: Record creation timestamp
        updated_at: Record last update timestamp
        deleted_at: Soft delete timestamp
        owner: Related User who owns this project
        city: Related City associated with this project
        satellite_images: List of satellite images for this project
        heat_islands: List of heat island analyses for this project
        predictions: List of predictions for this project
        recommendations: List of recommendations for this project
        reports: List of reports for this project
        simulations: List of simulations for this project
    """

    __tablename__ = "projects"
    __table_args__ = (
        Index("ix_projects_owner_id", "owner_id"),
        Index("ix_projects_city_id", "city_id"),
        Index("ix_projects_status_created", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    city_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cities.id"), nullable=False)
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.ACTIVE)
    visibility: Mapped[Visibility] = mapped_column(Enum(Visibility), default=Visibility.PRIVATE)
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    owner: Mapped[User] = relationship(back_populates="projects")
    city: Mapped[City] = relationship(back_populates="projects")
    satellite_images: Mapped[List["SatelliteImage"]] = relationship(back_populates="project")
    reports: Mapped[List["Report"]] = relationship(back_populates="project")
    # FIXME: Uncomment when models are created (future features)
    # heat_islands: Mapped[List["HeatIsland"]] = relationship(back_populates="project")
    # predictions: Mapped[List["Prediction"]] = relationship(back_populates="project")
    # recommendations: Mapped[List["Recommendation"]] = relationship(back_populates="project")
    # simulations: Mapped[List["Simulation"]] = relationship(back_populates="project")

    def __repr__(self) -> str:
        return (
            f"<Project(id={self.id}, name='{self.name}', "
            f"owner_id='{self.owner_id}', status='{self.status}')>"
        )