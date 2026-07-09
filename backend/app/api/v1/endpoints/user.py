"""User management endpoints — CRUD, search, role assignment."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.v1.endpoints.auth import get_current_user
from app.core.database import get_db
from app.repositories.base import DuplicateError, NotFoundError
from app.schemas.user import (
    PaginatedUserResponse,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.services.user_service import UserService

router = APIRouter()


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    return client.host if client else "unknown"


@router.get("/", response_model=PaginatedUserResponse)
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    include_deleted: bool = Query(False),
    current_user=Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    if search:
        try:
            items, total = user_service.search_users(
                query=search,
                page=page,
                page_size=page_size,
                include_deleted=include_deleted,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
    else:
        from app.repositories.user_repository import UserRepository
        repo = UserRepository(user_service.db)
        items, total = repo.get_all_users(include_deleted=include_deleted)
        offset = (page - 1) * page_size
        items = items[offset:offset + page_size]

    total_pages = max(1, (total + page_size - 1) // page_size)
    from app.schemas.common import Pagination
    return PaginatedUserResponse(
        items=[UserRead.model_validate(u) for u in items],
        pagination=Pagination(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        ),
    )


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    request: Request = None,
    current_user=Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    ip_address = _get_client_ip(request) if request else None
    try:
        return user_service.create_user(user_in=user_in, ip_address=ip_address)
    except DuplicateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: uuid.UUID,
    current_user=Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    try:
        return user_service.get_profile(user_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    request: Request = None,
    current_user=Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    ip_address = _get_client_ip(request) if request else None
    try:
        return user_service.update_user(
            user_id=user_id,
            user_in=user_in,
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


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: uuid.UUID,
    request: Request = None,
    current_user=Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    ip_address = _get_client_ip(request) if request else None
    try:
        user_service.soft_delete_user(user_id=user_id, ip_address=ip_address)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/{user_id}/restore", response_model=UserRead)
def restore_user(
    user_id: uuid.UUID,
    request: Request = None,
    current_user=Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    ip_address = _get_client_ip(request) if request else None
    try:
        return user_service.restore_user(user_id=user_id, ip_address=ip_address)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/{user_id}/activate", response_model=UserRead)
def activate_user(
    user_id: uuid.UUID,
    request: Request = None,
    current_user=Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    ip_address = _get_client_ip(request) if request else None
    try:
        return user_service.activate_user(user_id=user_id, ip_address=ip_address)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/{user_id}/deactivate", response_model=UserRead)
def deactivate_user(
    user_id: uuid.UUID,
    request: Request = None,
    current_user=Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    ip_address = _get_client_ip(request) if request else None
    try:
        return user_service.deactivate_user(user_id=user_id, ip_address=ip_address)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete("/{user_id}/hard", status_code=status.HTTP_204_NO_CONTENT)
def hard_delete_user(
    user_id: uuid.UUID,
    request: Request = None,
    current_user=Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    ip_address = _get_client_ip(request) if request else None
    try:
        user_service.delete_user(user_id=user_id, ip_address=ip_address)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/{user_id}/roles/{role_id}", response_model=UserRead)
def assign_role_to_user(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    request: Request = None,
    current_user=Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    ip_address = _get_client_ip(request) if request else None
    try:
        return user_service.assign_role(
            user_id=user_id,
            role_id=role_id,
            ip_address=ip_address,
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete("/{user_id}/roles/{role_id}", response_model=UserRead)
def remove_role_from_user(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    request: Request = None,
    current_user=Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    ip_address = _get_client_ip(request) if request else None
    try:
        return user_service.remove_role(
            user_id=user_id,
            role_id=role_id,
            ip_address=ip_address,
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
