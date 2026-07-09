import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("app.uhi.metadata")


def build_uhi_metadata(
    detection_method: str,
    config: dict[str, Any] | None = None,
    n_hotspots: int = 0,
    crs: str | None = None,
    resolution: float | None = None,
    additional: dict[str, Any] | None = None,
) -> dict:
    meta = {
        "detection_method": detection_method,
        "algorithm": "UHI Detection Engine v1.0",
        "n_hotspots": n_hotspots,
        "crs": crs,
        "resolution_m": resolution,
        "processing_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "processing_steps": [
            "feature_validation",
            f"detection_{detection_method}",
            "morphological_cleanup",
            "segmentation",
            "severity_classification",
            "quality_assessment",
            "spatial_analysis",
        ],
        "version": "1.0.0",
    }
    if config:
        meta["detection_config"] = {k: v for k, v in config.items() if not k.startswith("_")}
    if additional:
        meta["additional"] = additional
    return meta
