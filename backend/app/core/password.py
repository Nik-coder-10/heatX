"""Password hashing and verification service.

Uses bcrypt via passlib with constant-time comparison.
Supports automatic algorithm upgrade detection via ``needs_rehash()``.

Usage:
    >>> from app.core.password import hash_password, verify_password
    >>> hashed = hash_password("SecureP@ss1234")
    >>> verify_password("SecureP@ss1234", hashed)
    True
    >>> verify_password("wrong", hashed)
    False
"""

import hmac
from typing import Optional

from passlib.context import CryptContext
from passlib.exc import UnknownHashError

from app.core.exceptions import InvalidPassword

# Default context: bcrypt (with deprecated="auto" to support future upgrades)
# Round count of 12 provides a good balance of security and performance (~250ms).
_pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain-text password.

    Returns:
        bcrypt hash string (``$2b$12$...``).

    Raises:
        ValueError: If password is empty.

    Example:
        >>> hash_password("SecureP@ss1234")
        '$2b$12$...'
    """
    if not password:
        raise ValueError("Password cannot be empty")
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash using constant-time comparison.

    Args:
        plain_password: Plain-text password to check.
        hashed_password: Stored bcrypt hash.

    Returns:
        ``True`` if the password matches, ``False`` otherwise.

    Note:
        Uses constant-time comparison internally (passlib / bcrypt).
        Invalid hashes are safely rejected without raising.

    Example:
        >>> h = hash_password("MyP@ssword1")
        >>> verify_password("MyP@ssword1", h)
        True
        >>> verify_password("wrong", h)
        False
    """
    try:
        return _pwd_context.verify(plain_password, hashed_password)
    except (UnknownHashError, ValueError, TypeError):
        return False


def needs_rehash(hashed_password: str) -> bool:
    """Check whether a password hash needs to be rehashed.

    Returns ``True`` if the hash uses an older/deprecated algorithm or
    parameters (e.g. fewer bcrypt rounds) than the current configuration.
    Services should call this on login and re-hash if needed.

    Args:
        hashed_password: The stored password hash to inspect.

    Returns:
        ``True`` if the hash should be upgraded.

    Example:
        >>> needs_rehash("$2b$12$...")  # current config
        False
        >>> needs_rehash("$2a$08$...")  # old hash, low rounds
        True
    """
    try:
        return _pwd_context.needs_update(hashed_password)
    except (UnknownHashError, ValueError, TypeError):
        return True


def get_password_hash(password: str) -> str:
    """Alias for :func:`hash_password` — backward compatibility.

    Args:
        password: Plain-text password.

    Returns:
        bcrypt hash string.
    """
    return hash_password(password)
