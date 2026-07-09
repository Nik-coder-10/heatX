"""Metadata extraction and normalization for satellite imagery.

Normalizes provider-specific metadata into a uniform schema
compatible with the ``SatelliteImage`` database model.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any

from app.satellite.exceptions import MetadataError

logger = logging.getLogger("app.satellite.metadata")

_NORMALIZED_FIELDS = {
    "scene_id": str,
    "provider": str,
    "mission": str,
    "sensor": str,
    "acquisition_date": str,
    "processing_level": str,
    "cloud_cover": float,
    "crs": str,
    "resolution": float,
    "bands": list,
    "bounding_box": list,
    "file_size_bytes": int,
    "provider_name": str,
}


class MetadataExtractor:
    """Extracts and normalizes metadata from provider responses and files.

    The normalized output can be directly mapped to a ``SatelliteImage``
    create payload.
    """

    BAND_ALIASES: dict[str, str] = {
        "coastal": "coastal_aerosol",
        "blue": "B02",
        "green": "B03",
        "red": "B04",
        "nir": "B08",
        "swir1": "B11",
        "swir2": "B12",
        "pan": "panchromatic",
        "cirrus": "B09",
        "tirs1": "thermal_1",
        "tirs2": "thermal_2",
    }

    @staticmethod
    def normalize(raw: dict) -> dict:
        """Normalize a provider metadata dict into the standard schema.

        Args:
            raw: Raw metadata dict from a provider's ``extract_metadata()``.

        Returns:
            Normalized dict with keys:
                scene_id, provider, mission, sensor, acquisition_date,
                processing_level, cloud_cover, crs, resolution, bands,
                bounding_box, file_size_bytes, provider_name.
        """
        normalized: dict[str, Any] = {}

        for field, expected_type in _NORMALIZED_FIELDS.items():
            value = raw.get(field)
            if value is None and field == "file_size_bytes":
                normalized[field] = 0
                continue
            if value is None:
                raise MetadataError(
                    f"Missing required metadata field '{field}'"
                )
            if not isinstance(value, expected_type):
                try:
                    if expected_type is float:
                        value = float(value)
                    elif expected_type is int:
                        value = int(value)
                    elif expected_type is list and isinstance(value, str):
                        value = [v.strip() for v in value.split(",")]
                    elif expected_type is str:
                        value = str(value)
                except (ValueError, TypeError) as exc:
                    raise MetadataError(
                        f"Cannot coerce field '{field}' to {expected_type.__name__}: {exc}"
                    ) from exc
            normalized[field] = value

        normalized["bands"] = sorted(set(normalized["bands"]))

        return normalized

    @staticmethod
    def normalize_band_name(band: str) -> str:
        """Normalize a band name to a canonical form."""
        lower = band.lower().strip()
        return MetadataExtractor.BAND_ALIASES.get(lower, lower)

    @staticmethod
    def normalize_date(date_str: str) -> str:
        """Parse and return an ISO-8601 date string."""
        for fmt in (
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
            "%Y/%m/%d",
        ):
            try:
                dt = datetime.strptime(date_str, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                continue
        raise MetadataError(f"Cannot parse date string: '{date_str}'")

    @staticmethod
    def normalize_crs(crs: str) -> str:
        """Normalize CRS string to EPSG:XXXX format."""
        crs_clean = crs.strip().upper()
        match = re.search(r"EPSG[:\s]*(\d+)", crs_clean)
        if match:
            return f"EPSG:{match.group(1)}"
        match = re.search(r"(\d{4,6})", crs_clean)
        if match:
            return f"EPSG:{match.group(1)}"
        return crs_clean

    @staticmethod
    def to_satellite_image_payload(metadata: dict) -> dict:
        """Convert normalized metadata to a SatelliteImage create payload.

        Maps normalized fields to the ``SatelliteImage`` model schema.
        """
        return {
            "scene_id": metadata["scene_id"],
            "provider": metadata["provider"],
            "sensor": metadata.get("sensor", "unknown"),
            "capture_date": MetadataExtractor.normalize_date(
                metadata["acquisition_date"]
            ),
            "resolution": metadata["resolution"],
            "cloud_coverage": metadata["cloud_cover"],
            "bands_available": ",".join(metadata["bands"]),
            "crs": MetadataExtractor.normalize_crs(metadata["crs"]),
            "storage_path": "",
            "status": "pending",
            "metadata": {
                "mission": metadata.get("mission", ""),
                "processing_level": metadata.get("processing_level", ""),
                "provider_name": metadata.get("provider_name", ""),
                "file_size_bytes": metadata.get("file_size_bytes", 0),
                "bounding_box": metadata.get("bounding_box", []),
            },
        }
