"""API endpoints for SatelliteImage CRUD and query operations."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.endpoints.auth import get_current_user
from app.core.database import get_db
from app.database.enums import ProcessingStatus, SatelliteProvider
from app.models.user import User
from app.schemas.satellite_image import (
    SatelliteImageCreate,
    SatelliteImageFilter,
    SatelliteImageListResponse,
    SatelliteImageResponse,
    SatelliteImageUpdate,
)
from app.services.satellite_image import (
    DuplicateSceneIdError,
    ImageNotFoundError,
    InvalidMetadataError,
    InvalidProviderError,
    InvalidRasterPathError,
    InvalidStatusTransitionError,
    SatelliteImageService,
)

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> SatelliteImageService:
    return SatelliteImageService(db)


def _or_404(service_call):
    try:
        return service_call()
    except ImageNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/", response_model=SatelliteImageListResponse)
def list_satellite_images(
    filters: SatelliteImageFilter = Depends(),
    sort_by: str = Query("capture_date"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: SatelliteImageService = Depends(get_service),
    _current_user: User = Depends(get_current_user),
):
    filter_dict = filters.model_dump(exclude_none=True) or None
    items, total = service.search_images(
        filters=filter_dict,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return SatelliteImageListResponse(
        items=[SatelliteImageResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/", response_model=SatelliteImageResponse, status_code=status.HTTP_201_CREATED)
def create_satellite_image(
    data: SatelliteImageCreate,
    service: SatelliteImageService = Depends(get_service),
    _current_user: User = Depends(get_current_user),
):
    try:
        return service.create_image(data.model_dump())
    except DuplicateSceneIdError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except InvalidProviderError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/search", response_model=SatelliteImageListResponse)
def search_satellite_images(
    filters: SatelliteImageFilter = Depends(),
    sort_by: str = Query("capture_date"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: SatelliteImageService = Depends(get_service),
    _current_user: User = Depends(get_current_user),
):
    filter_dict = filters.model_dump(exclude_none=True) or None
    items, total = service.search_images(
        filters=filter_dict,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return SatelliteImageListResponse(
        items=[SatelliteImageResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/statistics", response_model=dict)
def get_statistics(
    project_id: Optional[uuid.UUID] = Query(None),
    service: SatelliteImageService = Depends(get_service),
    _current_user: User = Depends(get_current_user),
):
    return service.statistics(project_id=project_id)


@router.get("/project/{project_id}", response_model=list[SatelliteImageResponse])
def get_images_by_project(
    project_id: uuid.UUID,
    service: SatelliteImageService = Depends(get_service),
    _current_user: User = Depends(get_current_user),
):
    return service.list_images(filters={"project_id": project_id})


@router.get("/provider/{provider}", response_model=list[SatelliteImageResponse])
def get_images_by_provider(
    provider: SatelliteProvider,
    service: SatelliteImageService = Depends(get_service),
    _current_user: User = Depends(get_current_user),
):
    return service.list_images(filters={"provider": provider})


@router.get("/status/{status}", response_model=list[SatelliteImageResponse])
def get_images_by_status(
    status: ProcessingStatus,
    service: SatelliteImageService = Depends(get_service),
    _current_user: User = Depends(get_current_user),
):
    return service.list_images(filters={"status": status})


@router.get("/{image_id}", response_model=SatelliteImageResponse)
def get_satellite_image(
    image_id: uuid.UUID,
    service: SatelliteImageService = Depends(get_service),
    _current_user: User = Depends(get_current_user),
):
    return _or_404(lambda: service.get_image(image_id))


@router.patch("/{image_id}", response_model=SatelliteImageResponse)
def update_satellite_image(
    image_id: uuid.UUID,
    data: SatelliteImageUpdate,
    service: SatelliteImageService = Depends(get_service),
    _current_user: User = Depends(get_current_user),
):
    try:
        return service.update_image(image_id, data.model_dump(exclude_none=True))
    except ImageNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DuplicateSceneIdError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except InvalidStatusTransitionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_satellite_image(
    image_id: uuid.UUID,
    service: SatelliteImageService = Depends(get_service),
    _current_user: User = Depends(get_current_user),
):
    _or_404(lambda: service.delete_image(image_id))


@router.post("/{image_id}/restore", response_model=SatelliteImageResponse)
def restore_satellite_image(
    image_id: uuid.UUID,
    service: SatelliteImageService = Depends(get_service),
    _current_user: User = Depends(get_current_user),
):
    return _or_404(lambda: service.restore_image(image_id))
