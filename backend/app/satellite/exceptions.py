"""Custom exceptions for the satellite data acquisition subsystem."""


class SatelliteError(Exception):
    """Base exception for all satellite acquisition errors."""


class ProviderError(SatelliteError):
    """Raised when a provider operation fails."""


class ProviderNotFoundError(ProviderError):
    """Raised when a requested provider is not registered."""


class ProviderConfigurationError(ProviderError):
    """Raised when a provider is misconfigured."""


class SearchError(SatelliteError):
    """Raised when a search operation fails."""


class InvalidSearchParameterError(SearchError):
    """Raised when search parameters are invalid."""


class DownloadError(SatelliteError):
    """Raised when a download operation fails."""


class DownloadInterruptedError(DownloadError):
    """Raised when a download is interrupted and cannot resume."""


class DownloadCancelledError(DownloadError):
    """Raised when a download is explicitly cancelled."""


class DownloadQuotaExceededError(DownloadError):
    """Raised when disk quota is exceeded."""


class ValidationError(SatelliteError):
    """Raised when file or metadata validation fails."""


class FileCorruptionError(ValidationError):
    """Raised when a file appears corrupt."""


class MissingBandError(ValidationError):
    """Raised when required bands are missing."""


class InvalidCRSError(ValidationError):
    """Raised when coordinate system is invalid or unexpected."""


class UnsupportedProductError(ValidationError):
    """Raised when a product is not supported by the provider."""


class CacheError(SatelliteError):
    """Raised when a cache operation fails."""


class StorageError(SatelliteError):
    """Raised when a storage operation fails."""


class MetadataError(SatelliteError):
    """Raised when metadata extraction or normalization fails."""


class SearchResult:
    """Represents a single search result from a provider query."""

    def __init__(
        self,
        scene_id: str,
        provider: str,
        mission: str,
        sensor: str,
        acquisition_date: str,
        cloud_cover: float,
        resolution: float,
        crs: str,
        bounding_box: list[float],
        bands: list[str],
        processing_level: str,
        size_bytes: int,
        download_urls: dict[str, str],
        checksum: str | None = None,
        metadata: dict | None = None,
    ):
        self.scene_id = scene_id
        self.provider = provider
        self.mission = mission
        self.sensor = sensor
        self.acquisition_date = acquisition_date
        self.cloud_cover = cloud_cover
        self.resolution = resolution
        self.crs = crs
        self.bounding_box = bounding_box
        self.bands = bands
        self.processing_level = processing_level
        self.size_bytes = size_bytes
        self.download_urls = download_urls
        self.checksum = checksum
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {
            "scene_id": self.scene_id,
            "provider": self.provider,
            "mission": self.mission,
            "sensor": self.sensor,
            "acquisition_date": self.acquisition_date,
            "cloud_cover": self.cloud_cover,
            "resolution": self.resolution,
            "crs": self.crs,
            "bounding_box": self.bounding_box,
            "bands": self.bands,
            "processing_level": self.processing_level,
            "size_bytes": self.size_bytes,
            "checksum": self.checksum,
        }


class DownloadTask:
    """Represents a queued or in-progress download."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    def __init__(
        self,
        task_id: str,
        scene_id: str,
        provider: str,
        download_url: str,
        destination: str,
        total_bytes: int = 0,
    ):
        self.task_id = task_id
        self.scene_id = scene_id
        self.provider = provider
        self.download_url = download_url
        self.destination = destination
        self.total_bytes = total_bytes
        self.downloaded_bytes = 0
        self.status = self.PENDING
        self.error: str | None = None
        self.retry_count = 0
        self.checksum: str | None = None

    @property
    def progress(self) -> float:
        if self.total_bytes == 0:
            return 0.0
        return (self.downloaded_bytes / self.total_bytes) * 100.0

    @property
    def is_active(self) -> bool:
        return self.status in (self.PENDING, self.DOWNLOADING, self.PAUSED)
