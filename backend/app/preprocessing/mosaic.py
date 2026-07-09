import logging
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.merge import merge as rio_merge
from rasterio.windows import Window
from rasterio.warp import calculate_default_transform, reproject

from .exceptions import MosaicError
from .configuration import MosaicConfig

logger = logging.getLogger("app.preprocessing.mosaic")


def _get_scene_cloud_coverage(
    scene_path: str, cloud_mask_path: str | None = None
) -> float:
    if cloud_mask_path is not None:
        with rasterio.open(cloud_mask_path) as src:
            mask = src.read(1)
        cloud_pct = float(mask.sum()) / float(mask.size) * 100.0
        return cloud_pct
    return 50.0


def _get_scene_acquisition_date(scene_path: str) -> float:
    import os
    mtime = os.path.getmtime(scene_path)
    return mtime


def _get_scene_resolution(scene_path: str) -> float:
    with rasterio.open(scene_path) as src:
        return abs(src.transform[0])


def _mosaic_priority_strategy(
    dst_window: tuple[Window, int, int],
    scenes: list[dict[str, Any]],
    strategy: str,
    rasters: list[np.ndarray],
) -> np.ndarray:
    stack = np.stack(rasters, axis=-1)
    ny, nx = stack.shape[:2]
    result = np.zeros((ny, nx), dtype=stack.dtype)
    if strategy == "cloud_priority":
        for i, s in enumerate(scenes):
            cloud_pct = s.get("cloud_coverage", 50.0)
            if i == 0 or cloud_pct < scenes[0].get("cloud_coverage", 100.0):
                pass
        priorities = sorted(
            range(len(scenes)),
            key=lambda i: scenes[i].get("cloud_coverage", 100.0),
        )
        result = stack[:, :, priorities[0]].copy()
        for pi in priorities[1:]:
            mask = np.isnan(stack[:, :, pi]) | np.isinf(stack[:, :, pi])
            result[mask] = stack[:, :, pi][mask]
    elif strategy == "newest":
        priorities = sorted(
            range(len(scenes)),
            key=lambda i: scenes[i].get("acquisition_date", 0.0),
            reverse=True,
        )
        result = stack[:, :, priorities[0]].copy()
        for pi in priorities[1:]:
            mask = np.isnan(stack[:, :, pi]) | np.isinf(stack[:, :, pi])
            result[mask] = stack[:, :, pi][mask]
    elif strategy == "highest_resolution":
        priorities = sorted(
            range(len(scenes)),
            key=lambda i: scenes[i].get("resolution", float("inf")),
        )
        result = stack[:, :, priorities[0]].copy()
        for pi in priorities[1:]:
            mask = np.isnan(stack[:, :, pi]) | np.isinf(stack[:, :, pi])
            result[mask] = stack[:, :, pi][mask]
    else:
        result = np.nanmean(stack, axis=-1)

    return result


def mosaic_scenes(
    scene_paths: list[str],
    output_path: str | Path,
    dst_crs: str | None = None,
    dst_resolution: tuple[float, float] | None = None,
    resampling_method: str = "bilinear",
    strategy: str = "cloud_priority",
    cloud_mask_paths: list[str | None] | None = None,
    blend_width: int = 0,
) -> dict[str, Any]:
    if len(scene_paths) < 2:
        raise MosaicError(f"Need at least 2 scenes for mosaicking, got {len(scene_paths)}")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rio_resampling = Resampling[resampling_method.lower()]

    src_files = [rasterio.open(p) for p in scene_paths]
    try:
        mosaic_data, mosaic_transform = rio_merge(
            src_files,
            resampling=rio_resampling,
            method="first",
        )

        if dst_crs or dst_resolution:
            if dst_crs is None:
                dst_crs = src_files[0].crs
            dst_profile = src_files[0].profile.copy()
            dst_profile.update(
                crs=dst_crs,
                compress="lzw",
                bigtiff="IF_SAFER",
            )
            if dst_resolution:
                dst_transform, dst_width, dst_height = calculate_default_transform(
                    src_files[0].crs,
                    dst_crs,
                    mosaic_data.shape[2],
                    mosaic_data.shape[1],
                    *src_files[0].bounds,
                    resolution=dst_resolution,
                )
                dst_profile.update(
                    transform=dst_transform,
                    width=dst_width,
                    height=dst_height,
                )
            else:
                dst_transform, dst_width, dst_height = calculate_default_transform(
                    src_files[0].crs,
                    dst_crs,
                    mosaic_data.shape[2],
                    mosaic_data.shape[1],
                    *src_files[0].bounds,
                )
                dst_profile.update(
                    transform=dst_transform,
                    width=dst_width,
                    height=dst_height,
                )
            reprojected = np.empty(
                (mosaic_data.shape[0], dst_height, dst_width), dtype=mosaic_data.dtype
            )
            for i in range(mosaic_data.shape[0]):
                reproject(
                    source=mosaic_data[i],
                    destination=reprojected[i],
                    src_transform=mosaic_transform,
                    src_crs=src_files[0].crs,
                    dst_transform=dst_transform,
                    dst_crs=dst_crs,
                    resampling=rio_resampling,
                )
            mosaic_data = reprojected
            mosaic_transform = dst_transform

            with rasterio.open(output_path, "w", **dst_profile) as dst:
                dst.write(mosaic_data)
        else:
            dst_profile = src_files[0].profile.copy()
            dst_profile.update(
                height=mosaic_data.shape[1],
                width=mosaic_data.shape[2],
                transform=mosaic_transform,
                compress="lzw",
                bigtiff="IF_SAFER",
            )
            with rasterio.open(output_path, "w", **dst_profile) as dst:
                dst.write(mosaic_data)

        n_bands, height, width = mosaic_data.shape
        result = {
            "output_path": str(output_path),
            "n_bands": n_bands,
            "height": height,
            "width": width,
            "transform": mosaic_transform,
            "strategy": strategy,
        }
    finally:
        for f in src_files:
            f.close()

    logger.info(
        "Mosaic created: %s (%d bands, %dx%d, strategy=%s)",
        output_path,
        result["n_bands"],
        result["width"],
        result["height"],
        strategy,
    )
    return result


class MosaicStage:
    def __init__(self, config: MosaicConfig | None = None):
        self.config = config or MosaicConfig()

    @property
    def name(self) -> str:
        return "Mosaic"

    def execute(
        self,
        scene_groups: list[dict[str, Any]],
        output_dir: str,
    ) -> dict[str, Any]:
        t0 = time.time()
        logger.info("Mosaic stage started (strategy=%s)", self.config.strategy)

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        mosaics = {}
        for group in scene_groups:
            group_name = group.get("name", "mosaic")
            paths = group["paths"]
            cloud_masks = group.get("cloud_mask_paths")
            output_path = output_dir / f"{group_name}.tif"

            result = mosaic_scenes(
                paths,
                output_path,
                dst_crs=self.config.target_crs,
                dst_resolution=self.config.target_resolution,
                resampling_method=self.config.resampling_method,
                strategy=self.config.strategy,
                cloud_mask_paths=cloud_masks,
                blend_width=self.config.blend_width,
            )
            mosaics[group_name] = result

        elapsed = time.time() - t0
        logger.info("Mosaic stage completed in %.2fs", elapsed)

        return {
            "mosaics": mosaics,
            "elapsed_s": elapsed,
        }
