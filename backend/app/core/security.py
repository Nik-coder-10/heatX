"""Backward-compatible security module — re-exports from specialized sub-modules.

Keeps the same function signatures that existing services import:
    - ``verify_password``
    - ``get_password_hash``
    - ``create_access_token``
    - ``create_refresh_token``
    - ``decode_token``

New code should import directly from ``app.core.password`` or ``app.core.jwt``.
"""

from datetime import timedelta
from typing import Any, Optional, Union

from jose import JWTError  # noqa: F401  — re-export for existing services

from app.core.jwt import create_access_token as _create_access_token
from app.core.jwt import create_refresh_token as _create_refresh_token
from app.core.jwt import decode_token as _decode_token
from app.core.password import get_password_hash
from app.core.password import hash_password
from app.core.password import needs_rehash
from app.core.password import verify_password


def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Backward-compatible wrapper for :func:`app.core.jwt.create_access_token`.

    See :func:`app.core.jwt.create_access_token` for full documentation.
    """
    return _create_access_token(subject, expires_delta)


def create_refresh_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Backward-compatible wrapper for :func:`app.core.jwt.create_refresh_token`.

    See :func:`app.core.jwt.create_refresh_token` for full documentation.
    """
    return _create_refresh_token(subject, expires_delta)


def decode_token(token: str) -> dict:
    """Backward-compatible wrapper for :func:`app.core.jwt.decode_token`.

    See :func:`app.core.jwt.decode_token` for full documentation.
    """
    return _decode_token(token)


def authenticate_user(
    username: str, password: str, db_session: Any
) -> Optional[Any]:
    """Placeholder for user authentication (not yet implemented).

    Existing services call this but it is not part of the security layer.
    Will be replaced by service-layer authentication logic.

    Returns:
        Always ``None``.
    """
    return None
