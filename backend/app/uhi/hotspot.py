import logging
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .classification import DEFAULT_SEVERITY_CLASSES, classify_severity
from .spatial_analysis import compute_compactness, compute_elongation, compute_nearest_neighbor_distance
from .severity import SEVERITY_RECOMMENDATIONS

logger = logging.getLogger("app.uhi.hotspot")


@dataclass
class Hotspot:
    id: str
    severity: str
    confidence: float
    geometry: dict
    area_sq_km: float
    perimeter_km: float
    centroid: tuple[float, float]
    bbox: tuple[float, float, float, float]
    mean_temperature_c: float
    max_temperature_c: float
    min_temperature_c: float
    mean_ndvi: float = 0.0
    mean_ndbi: float = 0.0
    mean_ndwi: float = 0.0
    detection_method: str = ""
    dominant_landcover: str = "Unknown"
    vegetation_fraction: float = 0.0
    builtup_fraction: float = 0.0
    compactness: float = 0.0
    elongation: float = 0.0
    nearest_hotspot_distance_km: float | None = None
    recommended_actions: list[str] = field(default_factory=list)
    creation_timestamp: str = ""
    quality_metrics: dict[str, Any] = field(default_factory=dict)
    severity_score: float = 0.0
    pixel_count: int = 0

    def __post_init__(self):
        if not self.creation_timestamp:
            self.creation_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def summary(self) -> dict:
        return {
            "id": self.id,
            "severity": self.severity,
            "mean_temperature_c": round(self.mean_temperature_c, 1),
            "max_temperature_c": round(self.max_temperature_c, 1),
            "area_sq_km": round(self.area_sq_km, 2),
            "dominant_landcover": self.dominant_landcover,
            "vegetation_fraction": round(self.vegetation_fraction, 2),
            "builtup_fraction": round(self.builtup_fraction, 2),
            "confidence": round(self.confidence, 2),
            "recommended_actions": self.recommended_actions,
        }

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "severity": self.severity,
            "severity_score": round(self.severity_score, 2),
            "confidence": round(self.confidence, 4),
            "geometry": self.geometry,
            "area_sq_km": round(self.area_sq_km, 4),
            "perimeter_km": round(self.perimeter_km, 4),
            "centroid": [round(c, 6) for c in self.centroid],
            "bbox": [round(b, 6) for b in self.bbox],
            "mean_temperature_c": round(self.mean_temperature_c, 2),
            "max_temperature_c": round(self.max_temperature_c, 2),
            "min_temperature_c": round(self.min_temperature_c, 2),
            "mean_ndvi": round(self.mean_ndvi, 4),
            "mean_ndbi": round(self.mean_ndbi, 4),
            "mean_ndwi": round(self.mean_ndwi, 4),
            "detection_method": self.detection_method,
            "dominant_landcover": self.dominant_landcover,
            "vegetation_fraction": round(self.vegetation_fraction, 4),
            "builtup_fraction": round(self.builtup_fraction, 4),
            "compactness": round(self.compactness, 4),
            "elongation": round(self.elongation, 4),
            "nearest_hotspot_distance_km": (
                round(self.nearest_hotspot_distance_km, 4)
                if self.nearest_hotspot_distance_km is not None
                else None
            ),
            "recommended_actions": self.recommended_actions,
            "pixel_count": self.pixel_count,
            "creation_timestamp": self.creation_timestamp,
            "quality_metrics": self.quality_metrics,
        }


@dataclass
class UHIResult:
    hotspots: list[Hotspot]
    metadata: dict[str, Any]
    statistics: dict[str, Any]
    detection_mask: np.ndarray | None = None
    severity_map: np.ndarray | None = None
    quality_report: dict[str, Any] | None = None

    def summary(self) -> dict:
        return {
            "n_hotspots": len(self.hotspots),
            "statistics": self.statistics,
            "metadata": {k: v for k, v in self.metadata.items()
                        if k not in ("full_metadata",)},
        }

    def to_geojson(self) -> dict:
        features = []
        for hs in self.hotspots:
            feat = {
                "type": "Feature",
                "geometry": hs.geometry,
                "properties": hs.summary(),
            }
            features.append(feat)
        return {"type": "FeatureCollection", "features": features}


def build_hotspots_from_mask(
    labeled_mask: np.ndarray,
    lst_celsius: np.ndarray,
    transform,
    crs: str | None = None,
    config=None,
    ndvi: np.ndarray | None = None,
    ndbi: np.ndarray | None = None,
    ndwi: np.ndarray | None = None,
    land_cover: np.ndarray | None = None,
    rural_mean: float | None = None,
) -> list[Hotspot]:
    lst = lst_celsius.astype(np.float64)
    resolution = getattr(config, "resolution", 30.0)
    severity_classes = getattr(config, "severity_classes", None) or DEFAULT_SEVERITY_CLASSES

    hotspots = []
    labels = np.unique(labeled_mask)
    labels = labels[labels > 0]

    if rural_mean is None:
        valid = np.isfinite(lst)
        if valid.any():
            rural_mean = float(np.percentile(lst[valid], 50))
        else:
            rural_mean = 25.0

    sigma = float(np.std(lst[np.isfinite(lst)]))
    if sigma == 0:
        sigma = 1.0

    all_centroids = []
    for lbl in labels:
        mask = labeled_mask == lbl
        ys, xs = np.where(mask)
        if len(ys) < 2:
            continue
        centroid = (float(xs.mean()), float(ys.mean()))
        all_centroids.append(centroid)

    for idx, lbl in enumerate(labels):
        mask = labeled_mask == lbl
        ys, xs = np.where(mask)

        pixel_area_m2 = resolution ** 2
        area_sq_km = len(ys) * pixel_area_m2 / 1_000_000.0

        hot_data = lst[mask]
        valid_data = hot_data[np.isfinite(hot_data)]
        if len(valid_data) == 0:
            continue

        mean_t = float(valid_data.mean())
        max_t = float(valid_data.max())
        min_t = float(valid_data.min())

        centroid_px = (float(xs.mean()), float(ys.mean()))

        if transform is not None:
            cx, cy = transform * (centroid_px[0], centroid_px[1])
            centroid = (cx, cy)
        else:
            centroid = centroid_px

        if transform is not None:
            from affine import Affine
            if isinstance(transform, Affine):
                col_off, row_off = centroid_px[0] - 0.5, centroid_px[1] - 0.5
                width_px = float(xs.max() - xs.min() + 1)
                height_px = float(ys.max() - ys.min() + 1)
                left = transform.c + transform.a * col_off + transform.b * row_off
                top = transform.f + transform.d * col_off + transform.e * row_off
                right = left + width_px * resolution
                bottom = top - height_px * resolution
                bbox = (left, bottom, right, top)
            else:
                bbox = (0.0, 0.0, 0.0, 0.0)
        else:
            bbox = (0.0, 0.0, 0.0, 0.0)

        n_valid = len(valid_data)
        severity_label, severity_score = classify_severity(
            lst, mask, rural_mean, config,
        )

        ndvi_mean = float(ndvi[mask][np.isfinite(ndvi[mask])].mean()) if ndvi is not None else 0.0
        ndbi_mean = float(ndbi[mask][np.isfinite(ndbi[mask])].mean()) if ndbi is not None else 0.0
        ndwi_mean = float(ndwi[mask][np.isfinite(ndwi[mask])].mean()) if ndwi is not None else 0.0

        if land_cover is not None:
            lc_vals = land_cover[mask]
            lc_valid = lc_vals[lc_vals >= 0]
            dominant = str(np.bincount(lc_valid.astype(np.int64)).argmax()) if len(lc_valid) > 0 else "Unknown"
        else:
            dominant = "builtup" if ndbi_mean > 0 else "vegetation"

        veg_frac = max(0.0, min(1.0, ndvi_mean))
        built_frac = max(0.0, min(1.0, ndbi_mean))

        compactness = compute_compactness(area_sq_km, 4 * np.sqrt(area_sq_km / np.pi))
        elongation = compute_elongation(mask.astype(np.uint8), resolution)

        nearest_dist = compute_nearest_neighbor_distance(all_centroids, idx)

        sev_low = severity_classes[0][1] if severity_classes else 0
        sev_high = severity_classes[-2][2] if len(severity_classes) > 1 else float("inf")
        if severity_score >= sev_high:
            recommendations = SEVERITY_RECOMMENDATIONS.get("Extreme", [])
        elif severity_score >= 4.0:
            recommendations = SEVERITY_RECOMMENDATIONS.get("Very High", [])
        elif severity_score >= 3.0:
            recommendations = SEVERITY_RECOMMENDATIONS.get("High", [])
        elif severity_score >= 2.0:
            recommendations = SEVERITY_RECOMMENDATIONS.get("Moderate", [])
        elif severity_score >= 1.0:
            recommendations = SEVERITY_RECOMMENDATIONS.get("Low", [])
        else:
            recommendations = []

        hotspot_id = f"UHI-{lbl:04d}"

        hs = Hotspot(
            id=hotspot_id,
            severity=severity_label,
            confidence=0.5,
            geometry={"type": "Polygon", "coordinates": [[]]},
            area_sq_km=area_sq_km,
            perimeter_km=4 * np.sqrt(area_sq_km / np.pi),
            centroid=centroid,
            bbox=bbox,
            mean_temperature_c=mean_t,
            max_temperature_c=max_t,
            min_temperature_c=min_t,
            pixel_count=n_valid,
            mean_ndvi=ndvi_mean,
            mean_ndbi=ndbi_mean,
            mean_ndwi=ndwi_mean,
            detection_method="",
            dominant_landcover=dominant,
            vegetation_fraction=veg_frac,
            builtup_fraction=built_frac,
            compactness=compactness,
            elongation=elongation,
            nearest_hotspot_distance_km=nearest_dist,
            recommended_actions=recommendations,
            severity_score=severity_score,
        )
        hotspots.append(hs)

    logger.debug("Built %d hotspots from labeled mask", len(hotspots))
    return hotspots
