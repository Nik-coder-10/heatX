"""JWT token creation, decoding, and validation service.

Generates access and refresh tokens with full claim validation
(issuer, audience, expiration, not-before, JWT ID, token type).

Usage:
    >>> from app.core.jwt import create_access_token, decode_token
    >>> token = create_access_token(subject="user-uuid-here")
    >>> payload = decode_token(token)
    >>> payload["sub"]
    'user-uuid-here'
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import ExpiredToken, InvalidToken, TokenRevoked
from app.core.token_blacklist import is_blacklisted


def _now() -> datetime:
    """Return current UTC datetime with timezone info (used in JWT claims)."""
    return datetime.now(timezone.utc)


def _create_token(
    subject: Union[str, Any],
    token_type: str,
    expires_delta: Optional[timedelta] = None,
    **extra_claims: Any,
) -> str:
    """Internal helper to create a signed JWT.

    Args:
        subject: Token subject (typically user UUID as string).
        token_type: ``"access"`` or ``"refresh"``.
        expires_delta: Custom expiration duration. Falls back to config defaults.
        extra_claims: Additional claims to include in the payload.

    Returns:
        Encoded JWT string.

    Raises:
        SecurityConfigurationError: If ``SECRET_KEY`` or ``ALGORITHM`` is empty.
    """
    now = _now()

    if not settings.SECRET_KEY:
        raise ValueError("SECRET_KEY is not configured")
    if not settings.ALGORITHM:
        raise ValueError("JWT algorithm is not configured")

    if expires_delta is None:
        if token_type == "access":
            expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        else:
            expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    expire = now + expires_delta

    payload = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "nbf": now,
        "jti": str(uuid.uuid4()),
        "type": token_type,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }
    payload.update(extra_claims)

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    **extra_claims: Any,
) -> str:
    """Create a short-lived JWT access token.

    Args:
        subject: User identifier (UUID as string).
        expires_delta: Optional custom lifetime. Defaults to ``ACCESS_TOKEN_EXPIRE_MINUTES``.
        extra_claims: Additional claims to embed.

    Returns:
        Signed JWT string.

    Example:
        >>> token = create_access_token(subject="550e8400-e29b-41d4-a716-446655440000")
        >>> len(token.split(".")) == 3
        True
    """
    return _create_token(subject, "access", expires_delta, **extra_claims)


def create_refresh_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    **extra_claims: Any,
) -> str:
    """Create a long-lived JWT refresh token.

    Args:
        subject: User identifier (UUID as string).
        expires_delta: Optional custom lifetime. Defaults to ``REFRESH_TOKEN_EXPIRE_DAYS``.
        extra_claims: Additional claims to embed.

    Returns:
        Signed JWT string.

    Example:
        >>> token = create_refresh_token(subject="550e8400-e29b-41d4-a716-446655440000")
        >>> len(token.split(".")) == 3
        True
    """
    return _create_token(subject, "refresh", expires_delta, **extra_claims)


def decode_token(
    token: str,
    verify_exp: bool = True,
    audience: Optional[str] = None,
    issuer: Optional[str] = None,
) -> dict:
    """Decode and validate a JWT token.

    Performs full validation: signature, expiration, issuer, audience,
    token type. Checks the token blacklist.

    Args:
        token: The JWT string to decode.
        verify_exp: Whether to verify expiration (default ``True``).
        audience: Expected audience. Falls back to ``settings.JWT_AUDIENCE``.
        issuer: Expected issuer. Falls back to ``settings.JWT_ISSUER``.

    Returns:
        Decoded payload dict.

    Raises:
        InvalidToken: If the token is malformed, has bad signature,
            wrong issuer/audience, or missing required claims.
        ExpiredToken: If the token has expired.
        TokenRevoked: If the token has been blacklisted.

    Example:
        >>> token = create_access_token(subject="user-id")
        >>> payload = decode_token(token)
        >>> payload["sub"]
        'user-id'
    """
    if not token:
        raise InvalidToken("Token is empty")

    options = {
        "verify_signature": True,
        "verify_exp": verify_exp,
        "verify_nbf": True,
        "verify_iat": True,
        "verify_aud": True,
        "require": ["exp", "iat", "nbf", "jti", "type", "sub"],
    }

    aud = audience or settings.JWT_AUDIENCE
    iss = issuer or settings.JWT_ISSUER

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience=aud,
            issuer=iss,
            options=options,
        )
    except jwt.ExpiredSignatureError:
        raise ExpiredToken("Token has expired")
    except jwt.JWTClaimsError as e:
        raise InvalidToken(f"Token claim validation failed: {e}")
    except JWTError as e:
        raise InvalidToken(f"Token is invalid: {e}")

    # Check blacklist
    jti = payload.get("jti")
    if jti and is_blacklisted(jti):
        raise TokenRevoked("Token has been revoked")

    return payload


def decode_token_unsafe(token: str) -> dict:
    """Decode a JWT without any signature or claim validation.

    **Only use for debugging or inspecting token contents.**
    Does NOT verify signature, expiration, or any claims.

    Args:
        token: The JWT string to decode.

    Returns:
        Decoded payload dict (unverified).

    Raises:
        InvalidToken: If the token is malformed.

    Example:
        >>> decode_token_unsafe(token)["type"]
        'access'
    """
    try:
        return jwt.get_unverified_claims(token)
    except JWTError as e:
        raise InvalidToken(f"Cannot decode token: {e}")
