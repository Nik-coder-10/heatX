"""Download manager for queued, resumable, parallel satellite image downloads.

Features:
    - Queued downloads with progress tracking
    - Resume interrupted downloads via Range headers
    - Retry with exponential backoff
    - Parallel downloads (configurable concurrency)
    - Checksum validation when available
    - Disk quota awareness
    - Download cancellation
"""

import hashlib
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from queue import Queue
from threading import Event, Lock, Thread
from typing import Any, Callable

from app.satellite.cache import SatelliteCache
from app.satellite.exceptions import (
    DownloadCancelledError,
    DownloadError,
    DownloadInterruptedError,
    DownloadQuotaExceededError,
)
from app.satellite.storage import StorageManager

logger = logging.getLogger("app.satellite.download_manager")

_ProgressCallback = Callable[[str, str, int, int], None] | None

_RETRY_BASE_DELAY = 2.0
_RETRY_MAX_DELAY = 120.0
_RETRY_BACKOFF_FACTOR = 2.0
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_MAX_CONCURRENT = 4
_DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024


class DownloadTaskRecord:
    """Internal record for tracking download state."""

    def __init__(
        self,
        task_id: str,
        scene_id: str,
        provider: str,
        download_urls: dict[str, str],
        destination: str,
        bands: list[str] | None = None,
        checksum: str | None = None,
    ) -> None:
        self.task_id = task_id
        self.scene_id = scene_id
        self.provider = provider
        self.download_urls = download_urls
        self.destination = destination
        self.bands = bands or list(download_urls.keys())
        self.checksum = checksum
        self.status = "pending"
        self.progress: dict[str, float] = {b: 0.0 for b in self.bands}
        self.downloaded_bytes: dict[str, int] = {b: 0 for b in self.bands}
        self.total_bytes: dict[str, int] = {b: 0 for b in self.bands}
        self.error: str | None = None
        self.retry_count = 0
        self.max_retries = _DEFAULT_MAX_RETRIES
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None
        self.cancelled = Event()
        self._lock = Lock()

    @property
    def overall_progress(self) -> float:
        if not self.total_bytes or sum(self.total_bytes.values()) == 0:
            return 0.0
        total = sum(self.total_bytes.values())
        downloaded = sum(self.downloaded_bytes.values())
        return (downloaded / total) * 100.0 if total > 0 else 0.0

    def cancel(self) -> None:
        self.cancelled.set()


class DownloadManager:
    """Manages concurrent, resumable satellite image downloads.

    Args:
        storage: StorageManager instance for file organization.
        cache: Optional SatelliteCache for duplicate detection.
        max_concurrent: Maximum parallel downloads.
        max_retries: Default retry count per task.
        disk_quota_bytes: Maximum total download size (-1 = unlimited).
    """

    def __init__(
        self,
        storage: StorageManager,
        cache: SatelliteCache | None = None,
        max_concurrent: int = _DEFAULT_MAX_CONCURRENT,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        disk_quota_bytes: int = -1,
    ) -> None:
        self.storage = storage
        self.cache = cache or SatelliteCache()
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        self.disk_quota_bytes = disk_quota_bytes

        self._tasks: dict[str, DownloadTaskRecord] = {}
        self._task_lock = Lock()
        self._queue: Queue = Queue()
        self._active_count = 0
        self._active_lock = Lock()
        self._shutdown = Event()
        self._worker_threads: list[Thread] = []
        self._start_workers()

    # ---- Public API ----

    def enqueue(
        self,
        scene_id: str,
        provider: str,
        download_urls: dict[str, str],
        destination: str,
        bands: list[str] | None = None,
        checksum: str | None = None,
    ) -> str:
        """Queue a scene for download.

        Returns:
            Unique task ID that can be used to track/cancel progress.
        """
        task_id = str(uuid.uuid4())

        record = DownloadTaskRecord(
            task_id=task_id,
            scene_id=scene_id,
            provider=provider,
            download_urls=download_urls,
            destination=destination,
            bands=bands,
            checksum=checksum,
        )
        record.max_retries = self.max_retries

        with self._task_lock:
            self._tasks[task_id] = record

        self._queue.put(task_id)
        logger.info(
            "Enqueued download task '%s' for scene '%s' (%d bands)",
            task_id, scene_id, len(record.bands),
        )
        return task_id

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        """Return the current state of a download task."""
        with self._task_lock:
            record = self._tasks.get(task_id)
            if record is None:
                return None
            return {
                "task_id": record.task_id,
                "scene_id": record.scene_id,
                "provider": record.provider,
                "status": record.status,
                "progress": record.overall_progress,
                "band_progress": dict(record.progress),
                "downloaded_bytes": dict(record.downloaded_bytes),
                "total_bytes": dict(record.total_bytes),
                "error": record.error,
                "retry_count": record.retry_count,
                "started_at": record.started_at.isoformat() if record.started_at else None,
                "completed_at": record.completed_at.isoformat() if record.completed_at else None,
            }

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a queued or in-progress download task.

        Returns True if the task existed.
        """
        with self._task_lock:
            record = self._tasks.get(task_id)
            if record is None:
                return False
            record.cancel()
        logger.info("Cancelled task '%s'", task_id)
        return True

    def list_tasks(
        self, status: str | None = None
    ) -> list[dict[str, Any]]:
        """List all tasks, optionally filtered by status."""
        with self._task_lock:
            tasks = list(self._tasks.values())
        result = []
        for t in tasks:
            if status and t.status != status:
                continue
            result.append({
                "task_id": t.task_id,
                "scene_id": t.scene_id,
                "provider": t.provider,
                "status": t.status,
                "progress": t.overall_progress,
            })
        return result

    def active_count(self) -> int:
        """Return the number of currently active downloads."""
        with self._active_lock:
            return self._active_count

    def shutdown(self, wait: bool = True) -> None:
        """Shut down the download manager.

        Args:
            wait: If True, wait for active downloads to finish.
        """
        self._shutdown.set()
        if wait:
            for t in self._worker_threads:
                t.join(timeout=30)
        logger.info("Download manager shut down")

    # ---- Internal ----

    def _start_workers(self) -> None:
        for _ in range(self.max_concurrent):
            t = Thread(target=self._worker_loop, daemon=True)
            t.start()
            self._worker_threads.append(t)

    def _worker_loop(self) -> None:
        while not self._shutdown.is_set():
            try:
                task_id = self._queue.get(timeout=1)
            except Exception:
                continue

            with self._task_lock:
                record = self._tasks.get(task_id)
            if record is None:
                self._queue.task_done()
                continue

            if record.cancelled.is_set():
                self._queue.task_done()
                continue

            with self._active_lock:
                self._active_count += 1
            try:
                self._execute_download(record)
            finally:
                with self._active_lock:
                    self._active_count -= 1
                self._queue.task_done()

    def _execute_download(self, record: DownloadTaskRecord) -> None:
        record.status = "downloading"
        record.started_at = datetime.now(timezone.utc)

        try:
            for band in record.bands:
                if record.cancelled.is_set():
                    record.status = "cancelled"
                    raise DownloadCancelledError(f"Task '{record.task_id}' was cancelled")

                url = record.download_urls.get(band)
                if url is None:
                    logger.warning("No URL for band '%s' in task '%s'", band, record.task_id)
                    record.progress[band] = 100.0
                    continue

                dest_path = os.path.join(record.destination, f"{record.scene_id}_{band}.tif")
                self._download_band_with_retry(record, band, url, dest_path)

            record.status = "completed"
            record.completed_at = datetime.now(timezone.utc)

            if record.checksum:
                self._verify_task_checksum(record)

            cache_key = f"scene:{record.scene_id}"
            self.cache.set(cache_key, {
                "scene_id": record.scene_id,
                "provider": record.provider,
                "destination": record.destination,
                "bands": record.bands,
            })

            logger.info(
                "Download completed: task='%s' scene='%s' progress=%.1f%%",
                record.task_id, record.scene_id, record.overall_progress,
            )

        except DownloadCancelledError:
            record.status = "cancelled"
            logger.info("Download cancelled: task='%s' scene='%s'", record.task_id, record.scene_id)
        except Exception as exc:
            record.status = "failed"
            record.error = str(exc)
            logger.error(
                "Download failed: task='%s' scene='%s' error='%s'",
                record.task_id, record.scene_id, exc,
            )

    def _download_band_with_retry(
        self, record: DownloadTaskRecord, band: str, url: str, dest_path: str
    ) -> None:
        delay = _RETRY_BASE_DELAY

        for attempt in range(record.max_retries + 1):
            if record.cancelled.is_set():
                raise DownloadCancelledError(f"Task '{record.task_id}' was cancelled")

            try:
                self._check_disk_quota()
                self._download_band(record, band, url, dest_path)
                return
            except DownloadCancelledError:
                raise
            except (DownloadError, OSError) as exc:
                record.retry_count += 1
                if attempt >= record.max_retries:
                    raise DownloadError(
                        f"Failed to download band '{band}' after {record.max_retries + 1} "
                        f"attempts: {exc}"
                    ) from exc
                logger.warning(
                    "Retry %d/%d for band '%s' in task '%s': %s",
                    attempt + 1, record.max_retries, band, record.task_id, exc,
                )
                time.sleep(delay)
                delay = min(delay * _RETRY_BACKOFF_FACTOR, _RETRY_MAX_DELAY)

    def _download_band(
        self, record: DownloadTaskRecord, band: str, url: str, dest_path: str
    ) -> None:
        temp_path = dest_path + ".tmp"
        resume_position = 0
        mode = "wb"

        if os.path.exists(temp_path):
            resume_position = os.path.getsize(temp_path)
            mode = "ab"
            logger.info("Resuming download for '%s' at byte %d", band, resume_position)

        try:
            import urllib.request

            req = urllib.request.Request(url)
            if resume_position > 0:
                req.add_header("Range", f"bytes={resume_position}-")

            with urllib.request.urlopen(req, timeout=300) as response:
                total = record.total_bytes.get(band, 0)
                if total == 0:
                    content_range = response.headers.get("Content-Range")
                    if content_range:
                        total = int(content_range.split("/")[-1])
                    else:
                        total = int(response.headers.get("Content-Length", 0))
                    record.total_bytes[band] = total

                os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                with open(temp_path, mode) as f:
                    while True:
                        if record.cancelled.is_set():
                            raise DownloadCancelledError(
                                f"Task '{record.task_id}' was cancelled"
                            )
                        chunk = response.read(_DEFAULT_CHUNK_SIZE)
                        if not chunk:
                            break
                        f.write(chunk)
                        record.downloaded_bytes[band] += len(chunk)
                        record.progress[band] = (
                            record.downloaded_bytes[band] / total * 100 if total > 0 else 0
                        )

            os.rename(temp_path, dest_path)
            record.progress[band] = 100.0

        except Exception as exc:
            if os.path.exists(temp_path):
                logger.info("Partial download preserved at '%s' for resume", temp_path)
            raise DownloadError(f"Band '{band}': {exc}") from exc

    def _verify_task_checksum(self, record: DownloadTaskRecord) -> None:
        if not record.checksum:
            return
        h = hashlib.sha256()
        for band in record.bands:
            band_path = os.path.join(record.destination, f"{record.scene_id}_{band}.tif")
            if os.path.isfile(band_path):
                with open(band_path, "rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        h.update(chunk)
        actual = h.hexdigest()
        if actual != record.checksum:
            logger.error(
                "Checksum mismatch for scene '%s': expected=%s actual=%s",
                record.scene_id, record.checksum, actual,
            )

    def _check_disk_quota(self) -> None:
        if self.disk_quota_bytes <= 0:
            return
        usage = self.storage.disk_usage()
        if usage["total_bytes"] >= self.disk_quota_bytes:
            raise DownloadQuotaExceededError(
                f"Disk quota exceeded: {usage['total_bytes']} >= {self.disk_quota_bytes}"
            )
