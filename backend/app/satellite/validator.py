"""Validation utilities for satellite imagery files and metadata.

Validates GeoTIFF integrity, band completeness, CRS, file corruption,
and product support.
"""

import hashlib
import logging
import os
import struct
from typing import Any

from app.satellite.exceptions import (
    FileCorruptionError,
    InvalidCRSError,
    MissingBandError,
    UnsupportedProductError,
    ValidationError,
)

logger = logging.getLogger("app.satellite.validator")

_KNOWN_CRS_PREFIXES = ["EPSG:", "ESRI:", "SR-ORG:", "IAU_", "EPSG"]

_GEOTIFF_MAGIC_BYTES = {
    b"II\x2a\x00",  # Little-endian TIFF
    b"MM\x00\x2a",  # Big-endian TIFF
}


class SatelliteValidator:
    """Validates satellite image files for integrity and completeness."""

    @staticmethod
    def validate_geotiff(file_path: str) -> bool:
        """Check that a file is a valid GeoTIFF.

        Verifies:
            - File exists and is non-empty
            - Starts with valid TIFF magic bytes
            - First IFD header is readable

        Raises:
            FileCorruptionError: If the file is not a valid GeoTIFF.
        """
        if not os.path.isfile(file_path):
            raise FileCorruptionError(f"File not found: {file_path}")

        size = os.path.getsize(file_path)
        if size == 0:
            raise FileCorruptionError(f"File is empty: {file_path}")
        if size < 8:
            raise FileCorruptionError(
                f"File too small to be a valid GeoTIFF: {file_path} ({size} bytes)"
            )

        with open(file_path, "rb") as f:
            header = f.read(8)

        magic = header[:4]
        if magic not in _GEOTIFF_MAGIC_BYTES:
            raise FileCorruptionError(
                f"File does not have a valid TIFF header: {file_path} "
                f"(magic: {magic.hex()})"
            )

        offset_bytes = header[4:8]
        try:
            if magic == b"II\x2a\x00":
                ifd_offset = struct.unpack("<I", offset_bytes)[0]
            else:
                ifd_offset = struct.unpack(">I", offset_bytes)[0]
        except struct.error as exc:
            raise FileCorruptionError(
                f"Cannot read IFD offset in {file_path}: {exc}"
            ) from exc

        if ifd_offset < 8 or ifd_offset >= size:
            raise FileCorruptionError(
                f"Invalid IFD offset in {file_path}: {ifd_offset}"
            )

        logger.debug("GeoTIFF validation passed for '%s'", file_path)
        return True

    @staticmethod
    def validate_band_completeness(
        required_bands: list[str], actual_bands: list[str], provider: str
    ) -> bool:
        """Check that all required bands are present.

        Args:
            required_bands: Bands expected for this provider/product.
            actual_bands: Bands that were actually downloaded/found.

        Raises:
            MissingBandError: If one or more required bands are missing.
        """
        required_set = set(required_bands)
        actual_set = set(actual_bands)
        missing = required_set - actual_set
        if missing:
            raise MissingBandError(
                f"Missing bands for {provider}: {sorted(missing)}. "
                f"Expected {len(required_bands)}, got {len(actual_bands)}."
            )
        return True

    @staticmethod
    def validate_crs(crs: str, expected_prefix: str = "EPSG:") -> bool:
        """Validate a Coordinate Reference System string.

        Args:
            crs: The CRS string to validate.
            expected_prefix: Expected CRS authority prefix.

        Raises:
            InvalidCRSError: If the CRS is empty, unknown, or unexpected.
        """
        if not crs or not crs.strip():
            raise InvalidCRSError("CRS is empty")

        crs_clean = crs.strip().upper()

        if not any(crs_clean.startswith(p) for p in _KNOWN_CRS_PREFIXES):
            raise InvalidCRSError(
                f"Unknown CRS authority: '{crs}'. "
                f"Expected one of: {_KNOWN_CRS_PREFIXES}"
            )

        if not crs_clean.startswith(expected_prefix.upper()):
            logger.warning(
                "CRS '%s' does not match expected prefix '%s'",
                crs, expected_prefix,
            )

        logger.debug("CRS validation passed for '%s'", crs)
        return True

    @staticmethod
    def validate_file_not_corrupt(file_path: str, expected_size: int | None = None) -> bool:
        """Check a file for basic corruption indicators.

        Args:
            file_path: Path to the file.
            expected_size: Optional expected file size in bytes.

        Raises:
            FileCorruptionError: If the file appears corrupt.
        """
        if not os.path.isfile(file_path):
            raise FileCorruptionError(f"File not found: {file_path}")

        actual_size = os.path.getsize(file_path)
        if actual_size == 0:
            raise FileCorruptionError(f"File is empty: {file_path}")

        if expected_size is not None and actual_size != expected_size:
            raise FileCorruptionError(
                f"File size mismatch for '{file_path}': "
                f"expected {expected_size} bytes, got {actual_size} bytes"
            )

        return True

    @staticmethod
    def validate_checksum(
        file_path: str, expected_checksum: str, algorithm: str = "sha256"
    ) -> bool:
        """Validate a file's checksum against an expected value.

        Args:
            file_path: Path to the file.
            expected_checksum: Expected hex digest.
            algorithm: Hash algorithm (sha256, md5, sha1).

        Raises:
            FileCorruptionError: If checksum does not match.
        """
        if not os.path.isfile(file_path):
            raise FileCorruptionError(f"File not found: {file_path}")

        h = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)

        actual = h.hexdigest()
        if actual != expected_checksum:
            raise FileCorruptionError(
                f"Checksum mismatch for '{file_path}': "
                f"expected {expected_checksum}, got {actual}"
            )

        logger.debug("Checksum passed for '%s' (%s)", file_path, algorithm)
        return True

    @staticmethod
    def validate_product_support(
        product: str, supported_products: list[str], provider: str
    ) -> bool:
        """Check that a product is supported by the provider.

        Raises:
            UnsupportedProductError: If the product is not supported.
        """
        if product not in supported_products:
            raise UnsupportedProductError(
                f"Product '{product}' is not supported by {provider}. "
                f"Supported: {supported_products}"
            )
        return True

    @staticmethod
    def validate_all(
        file_paths: dict[str, str],
        required_bands: list[str] | None = None,
        provider: str | None = None,
        product: str | None = None,
        supported_products: list[str] | None = None,
        expected_crs: str | None = None,
    ) -> dict[str, Any]:
        """Run all applicable validations and return a report.

        Args:
            file_paths: Dict mapping band -> file path.
            required_bands: Bands that must be present.
            provider: Provider name (for error messages).
            product: Product to validate support for.
            supported_products: List of supported products.
            expected_crs: Expected CRS string.

        Returns:
            Dict with keys: valid (bool), errors (list), warnings (list).
        """
        errors: list[str] = []
        warnings: list[str] = []

        if provider and product is not None and supported_products is not None:
            try:
                SatelliteValidator.validate_product_support(
                    product, supported_products, provider
                )
            except UnsupportedProductError as e:
                errors.append(str(e))

        if required_bands:
            try:
                SatelliteValidator.validate_band_completeness(
                    required_bands, list(file_paths.keys()), provider or "unknown"
                )
            except MissingBandError as e:
                errors.append(str(e))

        for band, path in file_paths.items():
            try:
                SatelliteValidator.validate_geotiff(path)
            except FileCorruptionError as e:
                errors.append(f"{band}: {e}")

            try:
                SatelliteValidator.validate_file_not_corrupt(path)
            except FileCorruptionError as e:
                warnings.append(f"{band}: {e}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
