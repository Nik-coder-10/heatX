import logging
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

from .exceptions import VisualizationError

logger = logging.getLogger("app.indices.visualization")


_COLORMAPS: dict[str, list[tuple[float, tuple[int, int, int]]]] = {
    "ndvi": [
        (-1.0, (0, 0, 255)),
        (0.0, (139, 90, 43)),
        (0.15, (240, 230, 140)),
        (0.30, (144, 238, 144)),
        (0.50, (34, 139, 34)),
        (1.0, (0, 100, 0)),
    ],
    "ndbi": [
        (-1.0, (34, 139, 34)),
        (0.0, (255, 255, 255)),
        (0.15, (255, 165, 0)),
        (0.30, (255, 69, 0)),
        (1.0, (139, 0, 0)),
    ],
    "ndwi": [
        (-1.0, (139, 90, 43)),
        (0.0, (255, 255, 255)),
        (0.20, (135, 206, 250)),
        (0.40, (70, 130, 180)),
        (1.0, (0, 0, 139)),
    ],
}


def get_colormap(index_name: str) -> list[tuple[float, tuple[int, int, int]]]:
    key = index_name.lower()
    if key in _COLORMAPS:
        return _COLORMAPS[key]
    return [(-1.0, (0, 0, 255)), (0.0, (128, 128, 128)), (1.0, (255, 0, 0))]


def apply_colormap(
    array: np.ndarray,
    colormap: list[tuple[float, tuple[int, int, int]]],
    nodata: float | None = None,
) -> np.ndarray:
    h, w = array.shape[-2:]
    rgb = np.zeros((3, h, w), dtype=np.uint8)

    valid = np.ones((h, w), dtype=bool)
    if array.ndim == 2:
        arr_2d = array
    else:
        arr_2d = array[0]

    if nodata is not None:
        if np.isnan(nodata):
            valid &= ~np.isnan(arr_2d)
        else:
            valid &= np.abs(arr_2d.astype(np.float64) - nodata) > 1e-8
    valid &= ~np.isnan(arr_2d) & ~np.isinf(arr_2d)

    values = arr_2d[valid]
    if len(values) == 0:
        return rgb

    vmin = colormap[0][0]
    vmax = colormap[-1][0]

    for i in range(3):
        rgb[i][valid] = np.interp(
            values,
            [c[0] for c in colormap],
            [c[1][i] for c in colormap],
        ).astype(np.uint8)

    return rgb


def write_geotiff(
    array: np.ndarray,
    path: str | Path,
    profile: dict,
    index_name: str = "",
    tags: dict[str, str] | None = None,
) -> str:
    path = Path(path)
    out_profile = profile.copy()
    out_profile.update(
        dtype="float32",
        compress="lzw",
        bigtiff="IF_SAFER",
        nodata=-9999.0,
    )
    with rasterio.open(path, "w", **out_profile) as dst:
        write_data = array.astype(np.float32)
        if write_data.ndim == 2:
            write_data = write_data[np.newaxis, ...]
        dst.write(write_data)
        dst.update_tags(
            algorithm=index_name,
            **({} if tags is None else tags),
        )
    return str(path)


def write_png(
    rgb_array: np.ndarray,
    path: str | Path,
) -> str:
    path = Path(path)
    if path.suffix.lower() not in (".png",):
        path = path.with_suffix(".png")

    try:
        from PIL import Image
    except ImportError:
        raise VisualizationError("Pillow (PIL) is required for PNG generation")

    if rgb_array.ndim == 3 and rgb_array.shape[0] == 3:
        arr = np.transpose(rgb_array, (1, 2, 0))
    else:
        arr = rgb_array

    img = Image.fromarray(arr, mode="RGB" if arr.ndim == 3 else "L")
    img.save(str(path), optimize=True)
    return str(path)


def write_colorized(
    array: np.ndarray,
    path: str | Path,
    index_name: str,
    profile: dict,
    nodata: float | None = None,
    include_legend: bool = False,
) -> dict[str, str]:
    path = Path(path)
    colormap = get_colormap(index_name)
    rgb = apply_colormap(array, colormap, nodata)

    results = {}

    png_path = path.parent / f"{path.stem}_colorized.png"
    results["png"] = write_png(rgb, png_path)

    geotiff_path = path.parent / f"{path.stem}_colorized.tif"
    rgb_profile = profile.copy()
    rgb_profile.update(dtype="uint8", count=3, compress="lzw", nodata=None)
    with rasterio.open(geotiff_path, "w", **rgb_profile) as dst:
        dst.write(rgb)
        dst.update_tags(algorithm=f"{index_name}_colorized")
    results["geotiff"] = str(geotiff_path)

    return results


def write_legend(output_path: str | Path, index_name: str) -> str:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        raise VisualizationError("Pillow (PIL) is required for legend generation")

    colormap = get_colormap(index_name)
    legend_height = len(colormap) * 30 + 40
    legend_width = 300

    img = Image.new("RGB", (legend_width, legend_height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.text((10, 5), f"{index_name.upper()} Legend", fill=(0, 0, 0))

    for i, (value, color) in enumerate(colormap):
        y0 = 30 + i * 30
        draw.rectangle([10, y0, 50, y0 + 20], fill=color)
        draw.text((60, y0 + 2), f"{value:+.2f}", fill=(0, 0, 0))

    out_path = Path(str(output_path).rsplit(".", 1)[0] + "_legend.png")
    img.save(str(out_path), optimize=True)
    return str(out_path)
