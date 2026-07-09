"""Satellite Data Acquisition Subsystem.

Responsible for discovering, downloading, validating, caching, and
cataloguing Earth observation imagery from multiple providers.
"""

from app.satellite.exceptions import (
    CacheError,
    DownloadCancelledError,
    DownloadError,
    DownloadInterruptedError,
    DownloadQuotaExceededError,
    DownloadTask,
    FileCorruptionError,
    InvalidCRSError,
    InvalidSearchParameterError,
    MetadataError,
    MissingBandError,
    ProviderConfigurationError,
    ProviderError,
    ProviderNotFoundError,
    SatelliteError,
    SearchError,
    SearchResult,
    StorageError,
    UnsupportedProductError,
    ValidationError,
)
from app.satellite.base_provider import BaseSatelliteProvider
from app.satellite.provider_registry import ProviderRegistry
from app.satellite.cache import SatelliteCache
from app.satellite.validator import SatelliteValidator
from app.satellite.metadata import MetadataExtractor
from app.satellite.storage import StorageManager
from app.satellite.download_manager import DownloadManager
from app.satellite.search import SatelliteSearch

__all__ = [
    "BaseSatelliteProvider",
    "CacheError",
    "DownloadCancelledError",
    "DownloadError",
    "DownloadInterruptedError",
    "DownloadManager",
    "DownloadQuotaExceededError",
    "DownloadTask",
    "FileCorruptionError",
    "InvalidCRSError",
    "InvalidSearchParameterError",
    "MetadataError",
    "MetadataExtractor",
    "MissingBandError",
    "ProviderConfigurationError",
    "ProviderError",
    "ProviderNotFoundError",
    "ProviderRegistry",
    "SatelliteCache",
    "SatelliteError",
    "SatelliteSearch",
    "SatelliteValidator",
    "SearchError",
    "SearchResult",
    "StorageError",
    "StorageManager",
    "UnsupportedProductError",
    "ValidationError",
]
