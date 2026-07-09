import logging
import time
from pathlib import Path
from typing import Any

import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.warp import reproject, calculate_default_transform

from .exceptions import AlignmentError
from .configuration import AlignmentConfig

logger = logging.getLogger("app.preprocessing.alignment")


def _resolve_crs(crs_input: str | CRS | None) -> CRS | None:
    if crs_input is None:
        return None
    if isinstance(crs_input, CRS):
        return crs_input
    return CRS.from_string(crs_input)


def align_bands(
    input_paths: dict[str, str],
    output_dir: str | Path,
    target_crs: str | CRS | None = None,
    target_resolution: tuple[float, float] | None = None,
    target_extent: tuple[float, float, float, float] | None = None,
    resampling_method: str = "bilinear",
    align_pixels: bool = True,
) -> dict[str, str]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths_list = list(input_paths.items())
    if not paths_list:
        raise AlignmentError("No input paths provided")

    first_name, first_path = paths_list[0]
    with rasterio.open(first_path) as ref_src:
        ref_crs = ref_src.crs
        ref_bounds = ref_src.bounds
        ref_transform = ref_src.transform
        ref_width = ref_src.width
        ref_height = ref_src.height
        ref_nodata = ref_src.nodata

    target_crs_obj = _resolve_crs(target_crs) or ref_crs

    if target_extent:
        dst_left, dst_bottom, dst_right, dst_top = target_extent
    else:
        dst_left, dst_bottom, dst_right, dst_top = ref_bounds

    if target_resolution:
        dst_res_x, dst_res_y = target_resolution
    else:
        dst_res_x = abs(ref_transform.a)
        dst_res_y = abs(ref_transform.e)

    if align_pixels:
        dst_left = dst_left - (dst_left % dst_res_x)
        dst_bottom = dst_bottom - (dst_bottom % dst_res_y)

    dst_width = max(1, int(round((dst_right - dst_left) / dst_res_x)))
    dst_height = max(1, int(round((dst_top - dst_bottom) / dst_res_y)))

    from rasterio.transform import from_bounds

    dst_transform = from_bounds(
        dst_left, dst_bottom, dst_right, dst_top, dst_width, dst_height
    )

    logger.info(
        "Alignment target: %dx%d, CRS=%s, resolution=(%.8f, %.8f), extent=(%.6f, %.6f, %.6f, %.6f)",
        dst_width,
        dst_height,
        target_crs_obj,
        dst_res_x,
        dst_res_y,
        dst_left,
        dst_bottom,
        dst_right,
        dst_top,
    )

    rio_resampling = Resampling[resampling_method.lower()]

    output_paths = {}
    for band_name, band_path in paths_list:
        dst_path = output_dir / f"{band_name}_aligned.tif"
        with rasterio.open(band_path) as src:
            dst_profile = src.profile.copy()
            dst_profile.update(
                crs=target_crs_obj,
                transform=dst_transform,
                width=dst_width,
                height=dst_height,
                compress="lzw",
                bigtiff="IF_SAFER",
            )

            with rasterio.open(dst_path, "w", **dst_profile) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=dst_transform,
                        dst_crs=target_crs_obj,
                        resampling=rio_resampling,
                        src_nodata=src.nodata,
                        dst_nodata=src.nodata,
                    )

        output_paths[band_name] = str(dst_path)
        logger.info("Aligned band '%s' -> %s", band_name, dst_path)

    return output_paths


def check_alignment(paths: dict[str, str]) -> dict[str, Any]:
    CRS = rasterio.crs.CRS
    infos = {}
    for name, path in paths.items():
        with rasterio.open(path) as src:
            infos[name] = {
                "crs": src.crs,
                "width": src.width,
                "height": src.height,
                "transform": src.transform,
                "bounds": src.bounds,
            }

    ref = next(iter(infos.values()))
    issues = []
    for name, info in infos.items():
        if info["crs"] != ref["crs"]:
            issues.append(f"Band '{name}' has different CRS: {info['crs']} vs {ref['crs']}")
        if info["width"] != ref["width"] or info["height"] != ref["height"]:
            issues.append(
                f"Band '{name}' has different dimensions: "
                f"({info['width']}x{info['height']}) vs ({ref['width']}x{ref['height']})"
            )

    return {
        "aligned": len(issues) == 0,
        "issues": issues,
        "band_info": infos,
    }


class AlignmentStage:
    def __init__(self, config: AlignmentConfig | None = None):
        self.config = config or AlignmentConfig()

    @property
    def name(self) -> str:
        return "Alignment"

    def execute(
        self,
        input_paths: dict[str, str],
        output_dir: str,
    ) -> dict[str, Any]:
        t0 = time.time()
        logger.info("Alignment stage started")

        output_paths = align_bands(
            input_paths,
            output_dir,
            target_crs=self.config.target_crs,
            target_resolution=self.config.target_resolution,
            target_extent=self.config.target_extent,
            resampling_method=self.config.resampling_method,
            align_pixels=self.config.align_pixels,
        )

        alignment_check = check_alignment(output_paths)

        elapsed = time.time() - t0
        logger.info("Alignment stage completed in %.2fs", elapsed)

        return {
            "output_paths": output_paths,
            "alignment_check": alignment_check,
            "elapsed_s": elapsed,
        }
