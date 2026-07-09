"""Authentication endpoints — register, login, logout, token management."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.base import DuplicateError, NotFoundError
from app.core.exceptions import (
    ExpiredToken,
    InvalidPassword,
    InvalidToken,
    SecurityError,
    TokenRevoked,
)
from app.schemas.auth import (
    ForgotPasswordRequest,
    PasswordChange,
    ResetPasswordRequest,
    Token,
    TokenRefresh,
    VerifyEmailRequest,
)
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.auth_service import AuthService
from app.services.user_service import UserService

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    return client.host if client else "unknown"


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service),
):
    payload = auth_service.validate_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return user_service.get_profile(uuid.UUID(user_id))
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    auth_service: AuthService = Depends(get_auth_service),
):
    ip_address = _get_client_ip(request) if request else None
    try:
        return auth_service.login(
            email=form_data.username,
            password=form_data.password,
            ip_address=ip_address,
        )
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidPassword:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except SecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    user_in: UserCreate,
    request: Request = None,
    auth_service: AuthService = Depends(get_auth_service),
):
    ip_address = _get_client_ip(request) if request else None
    try:
        return auth_service.register_user(user_in=user_in, ip_address=ip_address)
    except DuplicateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.post("/refresh", response_model=Token)
def refresh_token(
    body: TokenRefresh,
    request: Request = None,
    auth_service: AuthService = Depends(get_auth_service),
):
    ip_address = _get_client_ip(request) if request else None
    try:
        return auth_service.refresh_access_token(
            refresh_token=body.refresh_token,
            ip_address=ip_address,
        )
    except (InvalidToken, ExpiredToken, TokenRevoked):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except SecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.post("/logout")
def logout(
    body: TokenRefresh,
    request: Request = None,
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service),
):
    ip_address = _get_client_ip(request) if request else None
    auth_service.logout(
        access_token=token,
        refresh_token=body.refresh_token,
        ip_address=ip_address,
    )
    return {"msg": "Successfully logged out"}


@router.get("/me", response_model=UserRead)
def read_current_user(
    current_user=Depends(get_current_user),
):
    return current_user


@router.put("/me", response_model=UserRead)
def update_current_user(
    user_in: UserUpdate,
    request: Request = None,
    current_user=Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    ip_address = _get_client_ip(request) if request else None
    try:
        return user_service.update_user(
            user_id=current_user.id,
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


@router.post("/change-password")
def change_password(
    body: PasswordChange,
    request: Request = None,
    current_user=Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    ip_address = _get_client_ip(request) if request else None
    try:
        auth_service.change_password(
            user_id=current_user.id,
            old_password=body.old_password,
            new_password=body.new_password,
            ip_address=ip_address,
        )
        return {"msg": "Password updated successfully"}
    except InvalidPassword:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password",
        )
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )


@router.post("/forgot-password")
def forgot_password(
    body: ForgotPasswordRequest,
    request: Request = None,
    auth_service: AuthService = Depends(get_auth_service),
):
    ip_address = _get_client_ip(request) if request else None
    auth_service.forgot_password(email=body.email, ip_address=ip_address)
    return {"msg": "If the email exists, a reset link has been sent"}


@router.post("/reset-password")
def reset_password(
    body: ResetPasswordRequest,
    request: Request = None,
    auth_service: AuthService = Depends(get_auth_service),
):
    ip_address = _get_client_ip(request) if request else None
    try:
        auth_service.reset_password(
            token=body.token,
            new_password=body.new_password,
            ip_address=ip_address,
        )
        return {"msg": "Password has been reset"}
    except InvalidToken:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )


@router.post("/verify-email")
def verify_email(
    body: VerifyEmailRequest,
    request: Request = None,
    auth_service: AuthService = Depends(get_auth_service),
):
    ip_address = _get_client_ip(request) if request else None
    try:
        auth_service.verify_email(token=body.token, ip_address=ip_address)
        return {"msg": "Email verified successfully"}
    except InvalidToken:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )


@router.post("/resend-verification")
def resend_verification(
    request: Request = None,
    current_user=Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    ip_address = _get_client_ip(request) if request else None
    try:
        token = auth_service.resend_verification(
            user_id=current_user.id,
            ip_address=ip_address,
        )
        return {"msg": "Verification email sent", "token": token}
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
