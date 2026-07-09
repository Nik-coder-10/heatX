"""LRU cache for satellite imagery with expiration, statistics, and invalidation.

Prevents duplicate downloads of the same scene.
Uses an in-memory LRU dict with optional TTL per entry.
"""

import logging
import time
from collections import OrderedDict
from threading import Lock
from typing import Any

from app.satellite.exceptions import CacheError

logger = logging.getLogger("app.satellite.cache")


class CacheEntry:
    """A single cache entry with metadata."""

    def __init__(self, key: str, value: Any, ttl_seconds: int = 0) -> None:
        self.key = key
        self.value = value
        self.created_at = time.monotonic()
        self.ttl_seconds = ttl_seconds
        self.access_count = 0

    @property
    def is_expired(self) -> bool:
        if self.ttl_seconds <= 0:
            return False
        return (time.monotonic() - self.created_at) > self.ttl_seconds

    def record_access(self) -> None:
        self.access_count += 1


class SatelliteCache:
    """Thread-safe LRU cache for satellite scene metadata and file records.

    Features:
        - LRU eviction when max size is reached
        - Per-entry TTL expiration
        - Statistics tracking (hits, misses, evictions)
        - Manual invalidation by key or pattern
        - Duplicate detection via scene_id
    """

    def __init__(self, max_size: int = 500, default_ttl: int = 3600) -> None:
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._data: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
            "invalidations": 0,
        }

    # ---- Public API ----

    def get(self, key: str) -> Any | None:
        """Retrieve a value from the cache.

        Returns None if not found or expired (expired entries are removed).
        """
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                self._stats["misses"] += 1
                logger.debug("Cache MISS for '%s'", key)
                return None

            if entry.is_expired:
                del self._data[key]
                self._stats["expirations"] += 1
                self._stats["misses"] += 1
                logger.debug("Cache EXPIRED for '%s'", key)
                return None

            self._data.move_to_end(key)
            entry.record_access()
            self._stats["hits"] += 1
            logger.debug("Cache HIT for '%s'", key)
            return entry.value

    def set(
        self, key: str, value: Any, ttl_seconds: int | None = None
    ) -> None:
        """Store a value in the cache.

        If the key already exists, it is updated and moved to the front.
        """
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)

            self._data[key] = CacheEntry(key, value, ttl)

            while len(self._data) > self._max_size:
                self._data.popitem(last=False)
                self._stats["evictions"] += 1
                logger.debug("Cache EVICTED oldest entry")

    def has(self, key: str) -> bool:
        """Check if a key exists and is not expired."""
        return self.get(key) is not None

    def contains_scene(self, scene_id: str) -> bool:
        """Check whether a scene_id is already cached (duplicate detection).

        Checks for keys starting with ``scene:{scene_id}``.
        """
        prefix = f"scene:{scene_id}"
        with self._lock:
            for k in self._data:
                if k.startswith(prefix):
                    entry = self._data[k]
                    if not entry.is_expired:
                        return True
        return False

    def invalidate(self, key: str) -> bool:
        """Remove a specific key from the cache.

        Returns True if the key existed.
        """
        with self._lock:
            if key in self._data:
                del self._data[key]
                self._stats["invalidations"] += 1
                logger.debug("Cache INVALIDATED '%s'", key)
                return True
            return False

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys containing the given pattern.

        Returns the number of invalidated entries.
        """
        count = 0
        with self._lock:
            keys_to_delete = [k for k in self._data if pattern in k]
            for k in keys_to_delete:
                del self._data[k]
                count += 1
            self._stats["invalidations"] += count
        if count > 0:
            logger.debug("Cache INVALIDATED %d entries matching '%s'", count, pattern)
        return count

    def clear(self) -> None:
        """Remove all entries from the cache."""
        with self._lock:
            self._data.clear()
        logger.info("Cache cleared")

    @property
    def size(self) -> int:
        """Current number of entries in the cache."""
        with self._lock:
            return len(self._data)

    @property
    def keys(self) -> list[str]:
        """Return all current cache keys."""
        with self._lock:
            return list(self._data.keys())

    # ---- Statistics ----

    @property
    def stats(self) -> dict[str, int]:
        """Return a copy of the cache statistics."""
        with self._lock:
            return dict(self._stats)

    @property
    def hit_rate(self) -> float:
        """Cache hit rate as a float 0.0-1.0."""
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            if total == 0:
                return 0.0
            return self._stats["hits"] / total

    def reset_stats(self) -> None:
        """Reset all cache statistics to zero (does not clear data)."""
        with self._lock:
            for k in self._stats:
                self._stats[k] = 0
        logger.debug("Cache stats reset")
