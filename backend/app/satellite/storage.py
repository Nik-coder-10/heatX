"""Storage manager for organizing satellite imagery files on disk.

Hierarchy::

    {base_dir}/{provider}/{mission}/{year}/{month}/{scene_id}/{band}.tif

Never overwrites existing imagery — files are immutable once written.
"""

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from app.satellite.exceptions import StorageError

logger = logging.getLogger("app.satellite.storage")

_DEFAULT_BASE_DIR = "/app/data/satellite"


class StorageManager:
    """Manages file storage for downloaded satellite imagery.

    Args:
        base_dir: Root directory for satellite image storage.
    """

    def __init__(self, base_dir: str | None = None) -> None:
        self.base_dir = Path(base_dir or os.getenv(
            "SATELLITE_STORAGE_DIR", _DEFAULT_BASE_DIR
        ))
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def scene_path(
        self,
        provider: str,
        mission: str,
        acquisition_date: str,
        scene_id: str,
    ) -> Path:
        """Return the directory path for a scene (creates intermediate dirs).

        Path: ``{base_dir}/{provider}/{mission}/{year}/{month}/{scene_id}/``
        """
        dt = self._parse_date(acquisition_date)
        path = (
            self.base_dir
            / provider
            / mission
            / f"{dt.year:04d}"
            / f"{dt.month:02d}"
            / scene_id
        )
        path.mkdir(parents=True, exist_ok=True)
        return path

    def band_path(
        self,
        provider: str,
        mission: str,
        acquisition_date: str,
        scene_id: str,
        band: str,
        extension: str = ".tif",
    ) -> Path:
        """Return the full file path for a specific band.

        Never overwrites existing files.
        """
        scene_dir = self.scene_path(provider, mission, acquisition_date, scene_id)
        return scene_dir / f"{scene_id}_{band}{extension}"

    def exists(self, provider: str, scene_id: str) -> bool:
        """Check whether a scene directory already exists."""
        import fnmatch

        scenes_dir = self.base_dir / provider
        if not scenes_dir.is_dir():
            return False

        for root, _dirs, _files in os.walk(str(scenes_dir)):
            if os.path.basename(root) == scene_id:
                return True
        return False

    def write_file(
        self,
        provider: str,
        mission: str,
        acquisition_date: str,
        scene_id: str,
        band: str,
        data: bytes,
        extension: str = ".tif",
    ) -> Path:
        """Write band data to storage.

        Raises:
            StorageError: If the file already exists or write fails.
        """
        dest = self.band_path(provider, mission, acquisition_date, scene_id, band, extension)
        if dest.exists():
            raise StorageError(
                f"File already exists, refusing to overwrite: {dest}"
            )
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            dest.write_bytes(data)
            logger.info("Wrote %d bytes to %s", len(data), dest)
        except OSError as exc:
            raise StorageError(f"Failed to write {dest}: {exc}") from exc
        return dest

    def move_file(
        self,
        source: str,
        provider: str,
        mission: str,
        acquisition_date: str,
        scene_id: str,
        band: str,
        extension: str = ".tif",
    ) -> Path:
        """Move a file into the storage hierarchy.

        Raises:
            StorageError: If the destination already exists.
        """
        dest = self.band_path(provider, mission, acquisition_date, scene_id, band, extension)
        if dest.exists():
            raise StorageError(
                f"Destination already exists, refusing to overwrite: {dest}"
            )
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(source), str(dest))
            logger.info("Moved '%s' to '%s'", source, dest)
        except OSError as exc:
            raise StorageError(f"Failed to move {source} to {dest}: {exc}") from exc
        return dest

    def delete_scene(self, provider: str, scene_id: str) -> bool:
        """Delete a scene directory and all its contents.

        Returns True if the scene existed and was deleted.
        """
        for root, _dirs, _files in os.walk(str(self.base_dir / provider)):
            if os.path.basename(root) == scene_id:
                shutil.rmtree(root)
                logger.info("Deleted scene directory: %s", root)
                return True
        return False

    def scene_size(self, provider: str, scene_id: str) -> int:
        """Return total size in bytes for a scene."""
        total = 0
        for root, _dirs, files in os.walk(str(self.base_dir / provider)):
            if os.path.basename(root) == scene_id:
                for f in files:
                    total += os.path.getsize(os.path.join(root, f))
                return total
        return 0

    def disk_usage(self) -> dict[str, Any]:
        """Return disk usage statistics for the storage directory."""
        total_bytes = 0
        file_count = 0
        provider_sizes: dict[str, int] = {}

        for provider_dir in self.base_dir.iterdir():
            if not provider_dir.is_dir():
                continue
            prov_size = 0
            for root, _dirs, files in os.walk(str(provider_dir)):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        sz = os.path.getsize(fp)
                        total_bytes += sz
                        prov_size += sz
                        file_count += 1
                    except OSError:
                        pass
            provider_sizes[provider_dir.name] = prov_size

        usage = shutil.disk_usage(str(self.base_dir))
        return {
            "base_dir": str(self.base_dir),
            "total_bytes": total_bytes,
            "file_count": file_count,
            "provider_sizes": provider_sizes,
            "disk_total": usage.total,
            "disk_used": usage.used,
            "disk_free": usage.free,
            "usage_percent": (usage.used / usage.total * 100) if usage.total > 0 else 0,
        }

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        """Parse an ISO-8601 date string."""
        for fmt in (
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        raise StorageError(f"Cannot parse date: '{date_str}'")
