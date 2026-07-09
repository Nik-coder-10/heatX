import logging
import time
from pathlib import Path

import numpy as np
import rasterio

from .exceptions import CloudMaskError
from .configuration import CloudMaskConfig

logger = logging.getLogger("app.preprocessing.cloud_mask")


def parse_sentinel2_qa60(
    qa_array: np.ndarray,
    cloud_threshold: int = 2,
    cirrus_threshold: int = 2,
    snow_threshold: int = 2,
) -> dict[str, np.ndarray]:
    if qa_array.ndim == 3:
        qa_array = qa_array[0]
    qa = qa_array.astype(np.uint16)

    cloud = ((qa >> 2) & 0x3) >= cloud_threshold
    cirrus = ((qa >> 4) & 0x3) >= cirrus_threshold
    snow = ((qa >> 6) & 0x3) >= snow_threshold
    nodata = ((qa >> 0) & 0x3) != 0

    combined = cloud | cirrus
    return {
        "cloud": cloud,
        "cirrus": cirrus,
        "snow": snow,
        "nodata": nodata,
        "combined": combined,
    }


def parse_landsat_qa_pixel(
    qa_array: np.ndarray,
    cloud_threshold: int = 1,
    shadow_threshold: int = 1,
    cirrus_threshold: int = 1,
    snow_threshold: int = 1,
) -> dict[str, np.ndarray]:
    if qa_array.ndim == 3:
        qa_array = qa_array[0]
    qa = qa_array.astype(np.uint16)

    fill = (qa & 0x1) != 0
    dilated_cloud = ((qa >> 1) & 0x1) != 0
    cirrus = ((qa >> 2) & 0x1) != 0
    cloud = ((qa >> 3) & 0x1) != 0
    shadow = ((qa >> 4) & 0x1) != 0
    snow = ((qa >> 5) & 0x1) != 0
    clear = ((qa >> 6) & 0x1) != 0

    cloud_final = cloud | dilated_cloud
    if cloud_threshold > 1:
        cloud_conf = (qa >> 8) & 0x3
        cloud_final = cloud_final | (cloud_conf >= cloud_threshold)

    if shadow_threshold > 1:
        shadow_conf = (qa >> 10) & 0x3
        shadow = shadow | (shadow_conf >= shadow_threshold)

    if cirrus_threshold > 1:
        cirrus_conf = (qa >> 14) & 0x3
        cirrus = cirrus | (cirrus_conf >= cirrus_threshold)

    combined = cloud_final | cirrus | shadow | fill
    shadow_or_cloud = cloud_final | shadow
    return {
        "cloud": cloud_final,
        "cirrus": cirrus,
        "shadow": shadow,
        "snow": snow,
        "fill": fill,
        "clear": clear,
        "combined": combined,
        "shadow_or_cloud": shadow_or_cloud,
    }


def compute_cloud_coverage(mask: np.ndarray) -> float:
    total = mask.size
    if total == 0:
        return 0.0
    clouded = int(mask.sum())
    return float(clouded) / float(total) * 100.0


def write_mask(
    mask: np.ndarray,
    path: str | Path,
    profile: dict,
    dtype: str = "uint8",
) -> str:
    path = Path(path)
    out_profile = profile.copy()
    out_profile.update(
        dtype=dtype,
        count=1,
        compress="lzw",
        nodata=255,
    )
    with rasterio.open(path, "w", **out_profile) as dst:
        dst.write(mask.astype(np.dtype(dtype)), 1)
    return str(path)


def load_qa_band(qa_path: str | Path) -> tuple[np.ndarray, dict]:
    with rasterio.open(qa_path) as src:
        qa_data = src.read()
        profile = src.profile
    return qa_data, profile


class CloudMaskStage:
    def __init__(self, config: CloudMaskConfig | None = None):
        self.config = config or CloudMaskConfig()

    @property
    def name(self) -> str:
        return "CloudMask"

    def execute(
        self,
        input_paths: dict[str, str],
        output_dir: str,
        profiles: dict[str, dict] | None = None,
    ) -> dict[str, Any]:
        import time
        t0 = time.time()
        logger.info("CloudMask stage started")

        qa_path = None
        for key, path in input_paths.items():
            key_lower = key.lower()
            if "qa60" in key_lower or key == self.config.sentinel_qa60_band:
                qa_path = path
                qa_type = "sentinel2"
                break
            if "qa_pixel" in key_lower or key == self.config.landsat_qa_pixel_band:
                qa_path = path
                qa_type = "landsat"
                break
        if qa_path is None:
            for key, path in input_paths.items():
                if key.lower() in ("qa", "quality", "quality_assurance"):
                    qa_path = path
                    qa_type = "sentinel2"
                    break

        if qa_path is None:
            raise CloudMaskError(
                "No QA band found in input paths. Expected QA60 (Sentinel-2) or QA_PIXEL (Landsat)."
            )

        qa_data, qa_profile = load_qa_band(qa_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if qa_type == "sentinel2":
            masks = parse_sentinel2_qa60(
                qa_data,
                cloud_threshold=self.config.cloud_confidence_threshold,
                cirrus_threshold=self.config.cirrus_confidence_threshold,
                snow_threshold=self.config.snow_confidence_threshold,
            )
        else:
            masks = parse_landsat_qa_pixel(
                qa_data,
                cloud_threshold=self.config.cloud_confidence_threshold,
                shadow_threshold=self.config.shadow_confidence_threshold,
                cirrus_threshold=self.config.cirrus_confidence_threshold,
                snow_threshold=self.config.snow_confidence_threshold,
            )

        cloud_pct = compute_cloud_coverage(masks["combined"])
        logger.info("Cloud coverage: %.2f%%", cloud_pct)

        output_paths = {}
        if self.config.output_cloud_mask:
            path = write_mask(
                masks["cloud"], output_dir / "cloud_mask.tif", qa_profile, self.config.mask_dtype
            )
            output_paths["cloud_mask"] = path
            logger.info("Cloud mask written: %s", path)

        if "shadow" in masks and self.config.output_cloud_shadow_mask:
            path = write_mask(
                masks["shadow"], output_dir / "shadow_mask.tif", qa_profile, self.config.mask_dtype
            )
            output_paths["shadow_mask"] = path

        if self.config.output_cirrus_mask:
            path = write_mask(
                masks["cirrus"], output_dir / "cirrus_mask.tif", qa_profile, self.config.mask_dtype
            )
            output_paths["cirrus_mask"] = path

        if self.config.output_snow_mask and "snow" in masks:
            path = write_mask(
                masks["snow"], output_dir / "snow_mask.tif", qa_profile, self.config.mask_dtype
            )
            output_paths["snow_mask"] = path

        combined_path = write_mask(
            masks["combined"],
            output_dir / "combined_cloud_mask.tif",
            qa_profile,
            self.config.mask_dtype,
        )
        output_paths["combined_cloud_mask"] = combined_path

        elapsed = time.time() - t0
        logger.info("CloudMask stage completed in %.2fs", elapsed)

        return {
            "output_paths": output_paths,
            "cloud_coverage_pct": cloud_pct,
            "masks": masks,
            "elapsed_s": elapsed,
        }


from typing import Any  
