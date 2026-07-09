import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from .exceptions import ConfigurationError


@dataclass
class CloudMaskConfig:
    enabled: bool = True
    sentinel_qa60_band: str = "QA60"
    landsat_qa_pixel_band: str = "QA_PIXEL"
    cloud_confidence_threshold: int = 2
    cirrus_confidence_threshold: int = 2
    shadow_confidence_threshold: int = 2
    snow_confidence_threshold: int = 2
    mask_dtype: str = "uint8"
    output_cloud_mask: bool = True
    output_cloud_shadow_mask: bool = True
    output_cirrus_mask: bool = True
    output_snow_mask: bool = False


@dataclass
class NoDataConfig:
    enabled: bool = True
    nodata_values: dict[str, float | None] = field(default_factory=dict)
    fill_strategy: str = "interpolate"
    interpolation_method: str = "linear"
    constant_fill_value: float = 0.0
    max_interpolation_distance: int = 100
    propagate_mask: bool = True
    output_nodata_mask: bool = True


@dataclass
class ResamplingConfig:
    enabled: bool = True
    method: str = "bilinear"
    target_resolution: tuple[float, float] | None = None
    target_width: int | None = None
    target_height: int | None = None


@dataclass
class AlignmentConfig:
    enabled: bool = True
    target_crs: str | None = None
    target_resolution: tuple[float, float] | None = None
    target_extent: tuple[float, float, float, float] | None = None
    resampling_method: str = "bilinear"
    align_pixels: bool = True


@dataclass
class NormalizationConfig:
    enabled: bool = True
    method: str = "min_max"
    scale_factor: float | None = None
    scale_offset: float | None = None
    percentile_low: float = 2.0
    percentile_high: float = 98.0
    per_band: bool = True
    dtype: str = "float32"


@dataclass
class MosaicConfig:
    enabled: bool = True
    strategy: str = "cloud_priority"
    target_crs: str | None = None
    target_resolution: tuple[float, float] | None = None
    resampling_method: str = "bilinear"
    blend_width: int = 0


@dataclass
class QualityConfig:
    enabled: bool = True
    compute_cloud_pct: bool = True
    compute_nodata_pct: bool = True
    compute_statistics: bool = True
    compute_band_consistency: bool = True
    compute_spatial_consistency: bool = True
    cloud_weight: float = 0.30
    nodata_weight: float = 0.25
    band_consistency_weight: float = 0.15
    spatial_consistency_weight: float = 0.15
    radiometric_weight: float = 0.15


@dataclass
class PipelineConfig:
    cloud_mask: CloudMaskConfig = field(default_factory=CloudMaskConfig)
    nodata: NoDataConfig = field(default_factory=NoDataConfig)
    resampling: ResamplingConfig = field(default_factory=ResamplingConfig)
    alignment: AlignmentConfig = field(default_factory=AlignmentConfig)
    normalization: NormalizationConfig = field(default_factory=NormalizationConfig)
    mosaic: MosaicConfig = field(default_factory=MosaicConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)

    work_dir: str = ""
    preserve_intermediate: bool = False
    log_level: str = "INFO"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PipelineConfig":
        config = cls()
        if "cloud_mask" in data:
            config.cloud_mask = CloudMaskConfig(**data["cloud_mask"])
        if "nodata" in data:
            config.nodata = NoDataConfig(**data["nodata"])
        if "resampling" in data:
            config.resampling = ResamplingConfig(**data["resampling"])
        if "alignment" in data:
            config.alignment = AlignmentConfig(**data["alignment"])
        if "normalization" in data:
            config.normalization = NormalizationConfig(**data["normalization"])
        if "mosaic" in data:
            config.mosaic = MosaicConfig(**data["mosaic"])
        if "quality" in data:
            config.quality = QualityConfig(**data["quality"])
        if "work_dir" in data:
            config.work_dir = data["work_dir"]
        if "preserve_intermediate" in data:
            config.preserve_intermediate = data["preserve_intermediate"]
        if "log_level" in data:
            config.log_level = data["log_level"]
        return config

    @classmethod
    def from_json(cls, path: str | Path) -> "PipelineConfig":
        path = Path(path)
        if not path.exists():
            raise ConfigurationError(f"Configuration file not found: {path}")
        with open(path) as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "PipelineConfig":
        try:
            import yaml
        except ImportError:
            raise ConfigurationError("PyYAML not installed. Use from_json or install pyyaml.")
        path = Path(path)
        if not path.exists():
            raise ConfigurationError(f"Configuration file not found: {path}")
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, path: str | Path) -> None:
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
