"""Token blacklist service for revoked JWT tracking.

Supports Redis (if ``REDIS_URL`` is configured) with an in-memory fallback
for development environments. Production deployments should configure Redis
for persistence across restarts.

Usage:
    >>> from app.core.token_blacklist import add_token, is_blacklisted
    >>> add_token("some-jti", expires_at=3600)
    >>> is_blacklisted("some-jti")
    True
    >>> is_blacklisted("unknown-jti")
    False
"""

import time
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Optional

from app.core.config import settings

# ---------------------------------------------------------------------------
# In-memory backend (fallback)
# ---------------------------------------------------------------------------
_blacklist: dict[str, float] = {}  # jti -> expiry timestamp (UTC epoch)
_lock = Lock()


def _get_redis_client():
    """Lazily import and connect to Redis if ``REDIS_URL`` is configured.

    Returns:
        ``redis.Redis`` client or ``None`` if Redis is unavailable.
    """
    try:
        import redis as redis_mod
    except ImportError:
        return None

    if not settings.REDIS_URL:
        return None

    try:
        client = redis_mod.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=2,
            socket_timeout=2,
            decode_responses=True,
        )
        client.ping()
        return client
    except Exception:
        return None


def _backend() -> str:
    """Return the active backend name for diagnostics."""
    try:
        import redis as redis_mod
        if settings.REDIS_URL:
            return "redis"
    except ImportError:
        pass
    return "memory"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_token(jti: str, expires_in: Optional[int] = None) -> None:
    """Add a JWT ID to the blacklist.

    Args:
        jti: JWT ID (unique token identifier) to revoke.
        expires_in: Time-to-live in seconds from now.
            If ``None``, uses ``settings.ACCESS_TOKEN_EXPIRE_MINUTES`` converted
            to seconds (safe upper bound for token lifetime).

    Example:
        >>> add_token("abc-123", expires_in=900)  # 15 minutes
    """
    if not jti:
        return

    if expires_in is None:
        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    expiry = time.time() + expires_in

    client = _get_redis_client()
    if client is not None:
        try:
            client.setex(f"bl:{jti}", expires_in, str(expiry))
            return
        except Exception:
            pass  # fall through to in-memory

    # In-memory fallback
    with _lock:
        _blacklist[jti] = expiry


def is_blacklisted(jti: str) -> bool:
    """Check whether a JWT ID has been blacklisted.

    Automatically removes expired entries.

    Args:
        jti: JWT ID to check.

    Returns:
        ``True`` if the token is blacklisted and not expired.

    Example:
        >>> is_blacklisted("nonexistent-jti")
        False
    """
    if not jti:
        return False

    client = _get_redis_client()
    if client is not None:
        try:
            return client.exists(f"bl:{jti}") == 1
        except Exception:
            pass  # fall through to in-memory

    # In-memory fallback
    now = time.time()
    with _lock:
        expiry = _blacklist.get(jti)
        if expiry is None:
            return False
        if now >= expiry:
            del _blacklist[jti]
            return False
        return True


def remove_expired() -> int:
    """Remove all expired entries from the blacklist.

    Redis handles TTL automatically; this only affects the in-memory store.

    Returns:
        Number of expired entries removed.

    Example:
        >>> remove_expired()
        0
    """
    now = time.time()
    count = 0
    with _lock:
        expired = [jti for jti, exp in _blacklist.items() if now >= exp]
        for jti in expired:
            del _blacklist[jti]
            count += 1
    return count


def blacklist_size() -> int:
    """Return the number of entries in the in-memory blacklist (approximate).

    Useful for monitoring.

    Returns:
        Number of entries (may include expired items until ``remove_expired`` runs).
    """
    with _lock:
        return len(_blacklist)
