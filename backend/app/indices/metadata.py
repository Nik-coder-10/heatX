import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import rasterio

from .registry import get_index

logger = logging.getLogger("app.indices.metadata")


def generate_metadata(
    index_name: str,
    input_paths: dict[str, str],
    band_map: dict[str, str] | None = None,
    output_path: str | None = None,
    additional_tags: dict[str, str] | None = None,
    processing_history: str | None = None,
) -> dict[str, Any]:
    index_def = get_index(index_name)

    source_bands = {}
    for canonical, path in input_paths.items():
        source_bands[canonical] = path

    ref_info = {}
    first_path = next(iter(input_paths.values()))
    with rasterio.open(first_path) as src:
        ref_info = {
            "crs": str(src.crs) if src.crs else None,
            "width": src.width,
            "height": src.height,
            "transform": list(src.transform) if src.transform else None,
            "bounds": {
                "left": float(src.bounds.left),
                "bottom": float(src.bounds.bottom),
                "right": float(src.bounds.right),
                "top": float(src.bounds.top),
            },
            "resolution": (abs(src.transform.a), abs(src.transform.e)) if src.transform else None,
            "driver": src.driver,
        }

    meta: dict[str, Any] = {
        "algorithm": index_def.name,
        "formula": index_def.formula,
        "description": index_def.description,
        "required_bands": index_def.required_bands,
        "source_bands": source_bands,
        "source_band_count": len(source_bands),
        "value_range": list(index_def.value_range),
        "unit": index_def.unit,
        "date_created": datetime.now(timezone.utc).isoformat(),
        "crs": ref_info.get("crs"),
        "width": ref_info.get("width"),
        "height": ref_info.get("height"),
        "bounds": ref_info.get("bounds"),
        "resolution": ref_info.get("resolution"),
        "driver": ref_info.get("driver"),
        "reference": index_def.reference,
        "provider_independent": True,
    }

    if band_map:
        meta["band_mapping"] = band_map
    if output_path:
        meta["output_path"] = str(Path(output_path).absolute())
    if processing_history:
        meta["processing_history"] = processing_history
    else:
        meta["processing_history"] = (
            f"Computed {index_def.name} from {len(input_paths)} input bands "
            f"using formula: {index_def.formula}"
        )
    if additional_tags:
        meta.update(additional_tags)

    return meta


def write_metadata_to_tags(
    output_path: str | Path,
    metadata: dict[str, Any],
) -> None:
    path = Path(output_path)
    if not path.exists():
        logger.warning("Cannot write metadata tags: file not found %s", path)
        return

    tags: dict[str, str] = {}
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)):
            tags[str(key)] = str(value)
        elif isinstance(value, list):
            tags[str(key)] = ", ".join(str(v) for v in value)
        elif isinstance(value, dict):
            tags[str(key)] = str(value)

    try:
        with rasterio.open(path, "r+") as dst:
            dst.update_tags(**tags)
    except Exception as exc:
        logger.warning("Failed to write metadata tags to %s: %s", path, exc)
