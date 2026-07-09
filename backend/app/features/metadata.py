import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("app.features.metadata")


def build_feature_metadata(
    n_features: int,
    n_categories: int,
    feature_names: list[str],
    categories: list[str],
    crs: str | None = None,
    sensor: str | None = None,
    resolution: float | None = None,
    algorithm: str = "GeoFeatureEngine v1.0",
    additional: dict[str, Any] | None = None,
) -> dict:
    meta = {
        "algorithm": algorithm,
        "n_features": n_features,
        "n_categories": n_categories,
        "feature_names": feature_names,
        "categories": categories,
        "crs": crs,
        "sensor": sensor,
        "resolution_m": resolution,
        "processing_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "processing_steps": [
            {"step": "feature_extraction", "method": "windowed parallel extraction"},
            {"step": "feature_cube_assembly", "method": "GeoFeatureCube construction"},
            {"step": "validation", "method": "consistency and quality checks"},
        ],
        "version": "1.0.0",
    }
    if additional:
        meta["additional"] = additional
    return meta
