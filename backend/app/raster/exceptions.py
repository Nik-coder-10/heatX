"""Custom exceptions for the Raster Management subsystem."""


class RasterError(Exception):
    """Base exception for all raster management errors."""


class RasterNotFoundError(RasterError):
    """Raised when a raster file does not exist."""


class RasterReadError(RasterError):
    """Raised when reading a raster file fails."""


class RasterWriteError(RasterError):
    """Raised when writing a raster file fails."""


class RasterValidationError(RasterError):
    """Raised when raster validation fails."""


class InvalidCRSError(RasterValidationError):
    """Raised when a CRS string is invalid or unrecognized."""


class RasterCRSError(RasterValidationError):
    """Raised when CRS is missing, invalid, or inconsistent."""


class RasterTransformError(RasterError):
    """Raised when a raster transformation operation fails."""


class RasterCompressionError(RasterError):
    """Raised when compression or decompression fails."""


class RasterPreviewError(RasterError):
    """Raised when preview generation fails."""


class UnsupportedFormatError(RasterError):
    """Raised when the raster format is not supported."""


class CorruptedRasterError(RasterValidationError):
    """Raised when a raster file appears corrupted."""


class MemoryLimitError(RasterError):
    """Raised when an operation would exceed the memory limit."""


class RasterStatisticsError(RasterError):
    """Raised when statistics computation fails."""


class RasterTilingError(RasterError):
    """Raised when tiling operations fail."""
