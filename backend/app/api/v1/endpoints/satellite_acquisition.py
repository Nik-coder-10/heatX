"""API endpoints for satellite data acquisition operations."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.endpoints.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.satellite_acquisition import (
    SatelliteCacheStatsResponse,
    SatelliteDownloadRequest,
    SatelliteDownloadTaskResponse,
    SatelliteImportResult,
    SatelliteProviderResponse,
    SatelliteSearchRequest,
    SatelliteSearchResponse,
    SatelliteStorageStatsResponse,
)
from app.services.satellite_acquisition_service import (
    ProviderLookupError,
    SatelliteAcquisitionError,
    SatelliteAcquisitionService,
    SceneDownloadError,
    SceneImportError,
)

router = APIRouter()


def get_acquisition_service(
    db: Session = Depends(get_db),
) -> SatelliteAcquisitionService:
    return SatelliteAcquisitionService(db)


@router.post("/search", response_model=SatelliteSearchResponse)
def search_satellite_catalog(
    query: SatelliteSearchRequest,
    service: SatelliteAcquisitionService = Depends(get_acquisition_service),
    _current_user: User = Depends(get_current_user),
):
    """Search for satellite imagery across all registered providers."""
    try:
        return service.search_catalog(
            bbox=query.bbox,
            city=query.city,
            date_from=query.date_from,
            date_to=query.date_to,
            max_cloud_cover=query.max_cloud_cover,
            resolution=query.resolution,
            missions=query.missions,
            bands=query.bands,
            providers=query.providers,
            limit=query.limit,
            offset=query.offset,
        )
    except SatelliteAcquisitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.post("/download", response_model=dict)
def download_satellite_scene(
    request: SatelliteDownloadRequest,
    service: SatelliteAcquisitionService = Depends(get_acquisition_service),
    _current_user: User = Depends(get_current_user),
):
    """Queue a satellite scene for download."""
    try:
        task_id = service.download_scene(
            scene_id=request.scene_id,
            provider=request.provider,
            mission=request.mission,
            acquisition_date=request.acquisition_date,
            bands=request.bands,
            download_urls=request.download_urls,
            checksum=request.checksum,
        )
        return {"task_id": task_id, "status": "queued"}
    except ProviderLookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    except SatelliteAcquisitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.post("/import", response_model=SatelliteImportResult)
def import_satellite_scene(
    request: SatelliteDownloadRequest,
    service: SatelliteAcquisitionService = Depends(get_acquisition_service),
    _current_user: User = Depends(get_current_user),
):
    """Download, validate, and persist a satellite scene into the database."""
    try:
        result = service.import_scene(
            scene_id=request.scene_id,
            provider=request.provider,
            mission=request.mission,
            acquisition_date=request.acquisition_date,
            project_id=str(request.project_id),
            bands=request.bands,
            download_urls=request.download_urls,
            checksum=request.checksum,
        )
        return SatelliteImportResult(
            image_id=result["image_id"],
            scene_id=result["scene_id"],
            provider=result["provider"],
            status=result["status"],
            storage_path=result["storage_path"],
            bands_available=result["bands_available"],
            capture_date=result["capture_date"],
        )
    except ProviderLookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    except SceneDownloadError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e)
        )
    except SceneImportError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    except SatelliteAcquisitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.get("/downloads", response_model=list[SatelliteDownloadTaskResponse])
def list_download_tasks(
    status_filter: Optional[str] = Query(None, alias="status"),
    service: SatelliteAcquisitionService = Depends(get_acquisition_service),
    _current_user: User = Depends(get_current_user),
):
    """List all download tasks, optionally filtered by status."""
    tasks = service.get_download_tasks(status=status_filter)
    return [SatelliteDownloadTaskResponse(**t) for t in tasks]


@router.get(
    "/downloads/{task_id}",
    response_model=SatelliteDownloadTaskResponse,
)
def get_download_task(
    task_id: str,
    service: SatelliteAcquisitionService = Depends(get_acquisition_service),
    _current_user: User = Depends(get_current_user),
):
    """Get the status of a specific download task."""
    task = service.get_download_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Download task '{task_id}' not found",
        )
    return SatelliteDownloadTaskResponse(**task)


@router.post("/downloads/{task_id}/cancel", response_model=dict)
def cancel_download_task(
    task_id: str,
    service: SatelliteAcquisitionService = Depends(get_acquisition_service),
    _current_user: User = Depends(get_current_user),
):
    """Cancel a queued or in-progress download."""
    cancelled = service.cancel_download(task_id)
    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Download task '{task_id}' not found",
        )
    return {"task_id": task_id, "status": "cancelled"}


@router.get("/providers", response_model=list[SatelliteProviderResponse])
def list_providers(
    service: SatelliteAcquisitionService = Depends(get_acquisition_service),
    _current_user: User = Depends(get_current_user),
):
    """List all available satellite data providers and their capabilities."""
    return service.list_providers()


@router.get("/storage", response_model=SatelliteStorageStatsResponse)
def get_storage_stats(
    service: SatelliteAcquisitionService = Depends(get_acquisition_service),
    _current_user: User = Depends(get_current_user),
):
    """Get storage usage statistics for satellite imagery."""
    return service.get_storage_stats()


@router.get("/cache", response_model=SatelliteCacheStatsResponse)
def get_cache_stats(
    service: SatelliteAcquisitionService = Depends(get_acquisition_service),
    _current_user: User = Depends(get_current_user),
):
    """Get satellite search cache statistics."""
    return service.get_cache_stats()


@router.post("/cache/clear", response_model=dict)
def clear_cache(
    service: SatelliteAcquisitionService = Depends(get_acquisition_service),
    _current_user: User = Depends(get_current_user),
):
    """Clear the satellite search result cache."""
    service.clear_cache()
    return {"status": "cache cleared"}
