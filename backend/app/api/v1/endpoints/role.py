"""Role management endpoints — CRUD, user assignment."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.v1.endpoints.auth import get_current_user
from app.core.database import get_db
from app.database.enums import UserRole
from app.repositories.base import DuplicateError, NotFoundError
from app.schemas.role import RoleRead
from app.schemas.user import UserRead, PaginatedUserResponse
from app.schemas.common import Pagination
from app.services.role_service import RoleService

router = APIRouter()


def get_role_service(db: Session = Depends(get_db)) -> RoleService:
    return RoleService(db)


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    return client.host if client else "unknown"


@router.get("/", response_model=list[RoleRead])
def list_roles(
    current_user=Depends(get_current_user),
    role_service: RoleService = Depends(get_role_service),
):
    return role_service.role_repo.get_all_roles()


@router.post("/", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
def create_role(
    name: UserRole,
    description: Optional[str] = Query(None),
    request: Request = None,
    current_user=Depends(get_current_user),
    role_service: RoleService = Depends(get_role_service),
):
    ip_address = _get_client_ip(request) if request else None
    try:
        return role_service.create_role(
            name=name,
            description=description,
            ip_address=ip_address,
        )
    except DuplicateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get("/{role_id}", response_model=RoleRead)
def get_role(
    role_id: uuid.UUID,
    current_user=Depends(get_current_user),
    role_service: RoleService = Depends(get_role_service),
):
    role = role_service.role_repo.get_by_id(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with id {role_id} not found",
        )
    return role


@router.put("/{role_id}", response_model=RoleRead)
def update_role(
    role_id: uuid.UUID,
    name: UserRole,
    description: Optional[str] = Query(None),
    request: Request = None,
    current_user=Depends(get_current_user),
    role_service: RoleService = Depends(get_role_service),
):
    ip_address = _get_client_ip(request) if request else None
    try:
        return role_service.rename_role(
            role_id=role_id,
            new_name=name,
            description=description,
            ip_address=ip_address,
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except DuplicateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: uuid.UUID,
    request: Request = None,
    current_user=Depends(get_current_user),
    role_service: RoleService = Depends(get_role_service),
):
    ip_address = _get_client_ip(request) if request else None
    try:
        role_service.delete_role(role_id=role_id, ip_address=ip_address)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/{role_id}/users", response_model=PaginatedUserResponse)
def get_role_users(
    role_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    role_service: RoleService = Depends(get_role_service),
):
    try:
        items, total = role_service.get_users(
            role_id=role_id,
            page=page,
            page_size=page_size,
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    total_pages = max(1, (total + page_size - 1) // page_size)
    return PaginatedUserResponse(
        items=[UserRead.model_validate(u) for u in items],
        pagination=Pagination(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        ),
    )


@router.post("/{role_id}/users", response_model=RoleRead)
def assign_users_to_role(
    role_id: uuid.UUID,
    user_ids: list[uuid.UUID],
    request: Request = None,
    current_user=Depends(get_current_user),
    role_service: RoleService = Depends(get_role_service),
):
    ip_address = _get_client_ip(request) if request else None
    try:
        return role_service.assign_users(
            role_id=role_id,
            user_ids=user_ids,
            ip_address=ip_address,
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete("/{role_id}/users", response_model=RoleRead)
def remove_users_from_role(
    role_id: uuid.UUID,
    user_ids: list[uuid.UUID],
    request: Request = None,
    current_user=Depends(get_current_user),
    role_service: RoleService = Depends(get_role_service),
):
    ip_address = _get_client_ip(request) if request else None
    try:
        return role_service.remove_users(
            role_id=role_id,
            user_ids=user_ids,
            ip_address=ip_address,
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
