from dataclasses import dataclass, field
from typing import Any

from .exceptions import ConfigurationError

DEFAULT_WINDOW_SIZE = 2048
DEFAULT_NODATA = -9999.0
DEFAULT_CACHE_DIR = ".feature_cache"
DEFAULT_BATCH_SIZE = 100000


@dataclass
class FeaturePipelineConfig:
    window_size: int = DEFAULT_WINDOW_SIZE
    nodata: float | None = DEFAULT_NODATA
    cache_enabled: bool = False
    cache_dir: str = DEFAULT_CACHE_DIR
    batch_size: int = DEFAULT_BATCH_SIZE
    feature_subset: list[str] | None = None
    exclude_categories: list[str] | None = None
    include_categories: list[str] | None = None
    compute_thermal: bool = True
    compute_vegetation: bool = True
    compute_builtup: bool = True
    compute_water: bool = True
    compute_baresoil: bool = True
    compute_spatial: bool = True
    compute_terrain: bool = False
    compute_temporal: bool = True
    compute_quality: bool = True
    export_format: str = "parquet"
    export_compression: str = "zstd"
    validate_output: bool = True
    compute_statistics: bool = False
    run_selection: bool = False
    selection_methods: list[str] | None = None
    random_sample: int | None = None
    random_seed: int = 42
    verbose: bool = False
    parallel: bool = False
    n_workers: int = 4
    crs: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> "FeaturePipelineConfig":
        valid_keys = set(cls.__dataclass_fields__)
        for k in d:
            if k not in valid_keys:
                raise ConfigurationError(f"Unknown config key: {k}")
        return cls(**{k: v for k, v in d.items() if k in valid_keys})

    @classmethod
    def defaults(cls) -> "FeaturePipelineConfig":
        return cls()
