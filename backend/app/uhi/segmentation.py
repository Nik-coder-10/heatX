import logging
import numpy as np
from scipy import ndimage

from .exceptions import SegmentationError

logger = logging.getLogger("app.uhi.segmentation")


def label_connected_components(binary_mask: np.ndarray, connectivity: int = 2) -> np.ndarray:
    struct = ndimage.generate_binary_structure(binary_mask.ndim, connectivity)
    labeled, n = ndimage.label(binary_mask, structure=struct)
    logger.debug("Labeled %d connected components", n)
    return labeled, n


def mask_to_polygons(
    labeled_mask: np.ndarray,
    transform,
    min_area_m2: float = 900.0,
    crs: str | None = None,
) -> list[dict]:
    import rasterio.features
    from shapely.geometry import shape

    polygons = []
    for i in range(1, int(labeled_mask.max()) + 1):
        single_mask = (labeled_mask == i).astype(np.uint8)
        if single_mask.sum() == 0:
            continue
        for geom, val in rasterio.features.shapes(
            single_mask, transform=transform, connectivity=8,
        ):
            if val != 1:
                continue
            try:
                poly = shape(geom)
                area_m2 = poly.area
                if 0 < area_m2 < min_area_m2:
                    continue
                geom["crs"] = crs
                polygons.append(geom)
            except Exception as e:
                logger.warning("Polygon conversion failed: %s", e)
                continue
    logger.debug("Converted %d polygons from labeled mask", len(polygons))
    return polygons


def polygons_to_hotspot_geometries(polygons: list[dict]) -> list[dict]:
    return polygons
