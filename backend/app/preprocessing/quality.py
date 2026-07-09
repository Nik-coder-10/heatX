import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

from .exceptions import QualityError
from .configuration import QualityConfig

logger = logging.getLogger("app.preprocessing.quality")


def compute_cloud_pct(cloud_mask_path: str | None = None) -> float:
    if cloud_mask_path is None:
        return 0.0
    with rasterio.open(cloud_mask_path) as src:
        mask = src.read(1)
    total = mask.size
    if total == 0:
        return 0.0
    return float(mask.sum()) / float(total) * 100.0


def compute_nodata_pct(
    input_paths: dict[str, str],
    nodata_values: dict[str, float | None] | None = None,
    nodata_mask_path: str | None = None,
) -> float:
    if nodata_mask_path:
        with rasterio.open(nodata_mask_path) as src:
            mask = src.read(1)
        return float(mask.sum()) / float(mask.size) * 100.0

    total_pixels = 0
    total_nodata = 0
    for band_name, band_path in input_paths.items():
        with rasterio.open(band_path) as src:
            data = src.read()
            nodata = (nodata_values or {}).get(band_name, src.nodata)
        for i in range(data.shape[0]):
            band = data[i]
            if nodata is not None:
                if np.isnan(nodata):
                    mask = np.isnan(band)
                else:
                    mask = np.isclose(band, nodata, atol=1e-8)
            else:
                mask = np.isnan(band) | np.isinf(band)
            total_pixels += band.size
            total_nodata += int(mask.sum())

    if total_pixels == 0:
        return 0.0
    return float(total_nodata) / float(total_pixels) * 100.0


def compute_band_consistency(input_paths: dict[str, str]) -> dict[str, Any]:
    infos = {}
    for name, path in input_paths.items():
        with rasterio.open(path) as src:
            infos[name] = {
                "width": src.width,
                "height": src.height,
                "count": src.count,
                "dtypes": src.dtypes,
                "crs": src.crs,
            }

    ref = next(iter(infos.values()))
    issues = []
    for name, info in infos.items():
        if info["width"] != ref["width"] or info["height"] != ref["height"]:
            issues.append(
                f"Band '{name}' dimensions differ: ({info['width']}x{info['height']}) "
                f"vs ({ref['width']}x{ref['height']})"
            )
        if info["count"] != ref["count"]:
            issues.append(
                f"Band '{name}' has {info['count']} bands vs {ref['count']}"
            )
        if info["crs"] != ref["crs"]:
            issues.append(
                f"Band '{name}' CRS differs: {info['crs']} vs {ref['crs']}"
            )

    return {
        "consistent": len(issues) == 0,
        "issues": issues,
        "band_info": infos,
    }


def compute_spatial_consistency(input_paths: dict[str, str]) -> dict[str, Any]:
    issues = []
    for name, path in input_paths.items():
        with rasterio.open(path) as src:
            data = src.read(1)
        mask = np.isnan(data) | np.isinf(data)
        if mask.any():
            pct = float(mask.sum()) / float(mask.size) * 100.0
            if pct > 50:
                issues.append(
                    f"Band '{name}' has {pct:.1f}% invalid pixels (spatial degradation)"
                )

    return {
        "consistent": len(issues) == 0,
        "issues": issues,
    }


def compute_radiometric_statistics(input_paths: dict[str, str]) -> dict[str, dict[str, float]]:
    stats: dict[str, dict[str, float]] = {}
    for name, path in input_paths.items():
        with rasterio.open(path) as src:
            data = src.read()
        band_stats: dict[str, float] = {}
        for i in range(data.shape[0]):
            band = data[i].astype(np.float64)
            valid = band[~np.isnan(band) & ~np.isinf(band)]
            if len(valid) > 0:
                band_stats[f"min_b{i}"] = float(valid.min())
                band_stats[f"max_b{i}"] = float(valid.max())
                band_stats[f"mean_b{i}"] = float(valid.mean())
                band_stats[f"std_b{i}"] = float(valid.std())
            else:
                band_stats[f"min_b{i}"] = 0.0
                band_stats[f"max_b{i}"] = 0.0
                band_stats[f"mean_b{i}"] = 0.0
                band_stats[f"std_b{i}"] = 0.0
        stats[name] = band_stats
    return stats


def compute_quality_score(
    cloud_pct: float = 0.0,
    nodata_pct: float = 0.0,
    band_consistent: bool = True,
    spatial_consistent: bool = True,
    radiometric_stats: dict[str, dict[str, float]] | None = None,
    weights: dict[str, float] | None = None,
) -> float:
    w = weights or {
        "cloud": 0.30,
        "nodata": 0.25,
        "band_consistency": 0.15,
        "spatial_consistency": 0.15,
        "radiometric": 0.15,
    }

    cloud_score = max(0.0, 100.0 - cloud_pct)
    nodata_score = max(0.0, 100.0 - nodata_pct)
    band_score = 100.0 if band_consistent else 0.0
    spatial_score = 100.0 if spatial_consistent else 50.0

    if radiometric_stats:
        max_std = 0.0
        for band_name, band_stats in radiometric_stats.items():
            for key, val in band_stats.items():
                if "std" in key:
                    max_std = max(max_std, val)
        radiometric_score = max(0.0, 100.0 - min(100.0, max_std * 10.0))
    else:
        radiometric_score = 100.0

    score = (
        w["cloud"] * cloud_score
        + w["nodata"] * nodata_score
        + w["band_consistency"] * band_score
        + w["spatial_consistency"] * spatial_score
        + w["radiometric"] * radiometric_score
    )

    return round(score, 2)


class QualityStage:
    def __init__(self, config: QualityConfig | None = None):
        self.config = config or QualityConfig()

    @property
    def name(self) -> str:
        return "Quality"

    def execute(
        self,
        input_paths: dict[str, str],
        cloud_mask_path: str | None = None,
        nodata_mask_path: str | None = None,
        nodata_values: dict[str, float | None] | None = None,
    ) -> dict[str, Any]:
        t0 = time.time()
        logger.info("Quality stage started")

        report: dict[str, Any] = {}

        if self.config.compute_cloud_pct:
            report["cloud_coverage_pct"] = compute_cloud_pct(cloud_mask_path)
            logger.info("Cloud coverage: %.2f%%", report["cloud_coverage_pct"])

        if self.config.compute_nodata_pct:
            report["nodata_coverage_pct"] = compute_nodata_pct(
                input_paths, nodata_values, nodata_mask_path
            )
            logger.info("NoData coverage: %.2f%%", report["nodata_coverage_pct"])

        if self.config.compute_band_consistency:
            report["band_consistency"] = compute_band_consistency(input_paths)
            logger.info(
                "Band consistency: %s",
                report["band_consistency"]["consistent"],
            )

        if self.config.compute_spatial_consistency:
            report["spatial_consistency"] = compute_spatial_consistency(input_paths)
            logger.info(
                "Spatial consistency: %s",
                report["spatial_consistency"]["consistent"],
            )

        if self.config.compute_statistics:
            report["radiometric_statistics"] = compute_radiometric_statistics(
                input_paths
            )
            logger.info("Radiometric statistics computed")

        weights = {
            "cloud": self.config.cloud_weight,
            "nodata": self.config.nodata_weight,
            "band_consistency": self.config.band_consistency_weight,
            "spatial_consistency": self.config.spatial_consistency_weight,
            "radiometric": self.config.radiometric_weight,
        }

        report["quality_score"] = compute_quality_score(
            cloud_pct=report.get("cloud_coverage_pct", 0.0),
            nodata_pct=report.get("nodata_coverage_pct", 0.0),
            band_consistent=report.get("band_consistency", {}).get("consistent", True),
            spatial_consistent=report.get("spatial_consistency", {}).get("consistent", True),
            radiometric_stats=report.get("radiometric_statistics"),
            weights=weights,
        )
        logger.info("Quality score: %.2f / 100", report["quality_score"])

        elapsed = time.time() - t0
        report["elapsed_s"] = elapsed
        logger.info("Quality stage completed in %.2fs", elapsed)

        return report
