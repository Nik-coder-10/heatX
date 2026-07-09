import logging
import numpy as np
from datetime import datetime, timezone
from typing import Any

from .configuration import UHIDetectionConfig
from .exceptions import MissingFeatureError, DetectionError
from .registry import DETECTORS
from .hotspot import build_hotspots_from_mask, UHIResult
from .morphology import apply_morphology
from .segmentation import label_connected_components, mask_to_polygons
from .classification import classify_severity, classify_severity_map
from .quality import compute_confidence, compute_data_completeness
from .quality import compute_boundary_confidence, hotspot_confidence_from_mask
from .quality import compute_overall_quality_score
from .statistics import compute_uhi_statistics
from .metadata import build_uhi_metadata
from .validator import validate_feature_cube

logger = logging.getLogger("app.uhi.engine")


class UHIDetectionEngine:
    def __init__(self, config: UHIDetectionConfig | dict | None = None):
        if config is None:
            self.config = UHIDetectionConfig.defaults()
        elif isinstance(config, dict):
            self.config = UHIDetectionConfig.from_dict(config)
        else:
            self.config = config
        self._result: UHIResult | None = None

    def detect(self, cube) -> UHIResult:
        self._result = self.run_pipeline(cube)
        return self._result

    def run_pipeline(self, cube) -> UHIResult:
        logger.info("Starting UHI detection pipeline")

        lst = cube.features.get("lst_celsius")
        if lst is None:
            raise MissingFeatureError("lst_celsius not found in feature cube")

        lst = lst.astype(np.float64)
        valid = np.isfinite(lst)
        if not valid.any():
            raise DetectionError("No valid LST data in feature cube")

        quality_flags = cube.features.get("quality_flags")
        ndvi = cube.features.get("ndvi")
        ndbi = cube.features.get("ndbi")
        ndwi = cube.features.get("ndwi")
        land_cover = cube.features.get("land_cover")

        detection_mask = run_detection(
            lst_celsius=lst,
            config=self.config,
            quality_flags=quality_flags,
        )

        clean_mask = apply_morphology(detection_mask, self.config)

        labeled_mask, n_components = label_connected_components(clean_mask)

        transform = cube.transform
        crs = cube.crs

        if transform is not None:
            polygons = mask_to_polygons(labeled_mask, transform, self.config.min_hotspot_area_m2, crs)
        else:
            polygons = []

        rural_mean = float(np.percentile(lst[valid], 50))

        severity_map = classify_severity_map(lst, rural_mean, self.config)

        hotspots = build_hotspots_from_mask(
            labeled_mask=labeled_mask,
            lst_celsius=lst,
            transform=transform,
            crs=crs,
            config=self.config,
            ndvi=ndvi,
            ndbi=ndbi,
            ndwi=ndwi,
            land_cover=land_cover,
            rural_mean=rural_mean,
        )

        data_completeness = compute_data_completeness(lst, quality_flags)
        boundary_conf = compute_boundary_confidence(clean_mask)
        confidence_map = compute_confidence(clean_mask, lst, quality_mask=quality_flags)
        for hs in hotspots:
            hotspot_conf = hotspot_confidence_from_mask(confidence_map, _hotspot_mask(labeled_mask, hs.id))
            hs.confidence = hotspot_conf
            hs.quality_metrics["overall_score"] = compute_overall_quality_score(
                hs, data_completeness, boundary_conf, hotspot_conf,
            )

        stats = compute_uhi_statistics(hotspots)
        meta = build_uhi_metadata(
            detection_method=self.config.method,
            config=self.config.__dict__.copy(),
            n_hotspots=len(hotspots),
            crs=crs,
            resolution=self.config.resolution,
        )

        self._result = UHIResult(
            hotspots=hotspots,
            metadata=meta,
            statistics=stats,
            detection_mask=clean_mask,
            severity_map=severity_map,
        )
        logger.info("UHI detection complete: %d hotspots found", len(hotspots))
        return self._result

    @property
    def result(self) -> UHIResult | None:
        return self._result


def run_detection(
    lst_celsius: np.ndarray,
    config: UHIDetectionConfig | None = None,
    quality_flags: np.ndarray | None = None,
) -> np.ndarray:
    cfg = config or UHIDetectionConfig.defaults()
    method = cfg.method

    if method not in DETECTORS:
        raise DetectionError(f"Unknown detection method: {method}. Available: {list(DETECTORS.keys())}")

    detector_fn = DETECTORS[method]["function"]
    logger.info("Running detection with method: %s", method)

    result = detector_fn(lst_celsius, config=cfg)
    if isinstance(result, dict):
        mask = result.get("binary_mask", np.zeros_like(lst_celsius, dtype=np.uint8))
    else:
        mask = result
    mask = (mask > 0).astype(np.uint8)

    if quality_flags is not None:
        cloud_mask = (quality_flags & 1) > 0
        mask[cloud_mask] = 0

    return mask


def _hotspot_mask(labeled_mask: np.ndarray, hotspot_id: int) -> np.ndarray:
    return (labeled_mask == hotspot_id).astype(np.uint8)
