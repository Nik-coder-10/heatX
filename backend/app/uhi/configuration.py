from dataclasses import dataclass, field
from typing import Any

from .exceptions import ConfigurationError


@dataclass
class UHIDetectionConfig:
    method: str = "hybrid"
    adaptive_k: float = 1.5
    zscore_threshold: float = 2.0
    percentile: float = 90.0
    dbscan_eps: float = 30.0
    dbscan_min_samples: int = 5
    hybrid_weights: dict[str, float] | None = None
    min_hotspot_area_m2: float = 900.0
    max_hotspot_area_m2: float = 1e12
    morphology_opening_pixels: int = 2
    morphology_closing_pixels: int = 3
    fill_holes: bool = True
    remove_small_objects: bool = True
    smooth_boundary: bool = True
    smooth_sigma: float = 1.0
    severity_classes: list[tuple[str, float, float]] | None = None
    confidence_method: str = "ensemble"
    compute_spatial_metrics: bool = True
    compute_morphology: bool = True
    window_size: int = 2048
    parallel: bool = False
    n_workers: int = 4
    crs: str | None = None
    resolution: float = 30.0
    verbose: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "UHIDetectionConfig":
        valid = set(cls.__dataclass_fields__)
        for k in d:
            if k not in valid:
                raise ConfigurationError(f"Unknown config key: {k}")
        return cls(**{k: v for k, v in d.items() if k in valid})

    @classmethod
    def defaults(cls) -> "UHIDetectionConfig":
        return cls()
