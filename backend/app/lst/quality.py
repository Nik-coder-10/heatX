import logging
import numpy as np

logger = logging.getLogger("app.lst.quality")


CLOUD = 1 << 0
WATER = 1 << 1
SNOW = 1 << 2
LOW_EMISSIVITY = 1 << 3
MISSING_BAND = 1 << 4
INTERPOLATED = 1 << 5
HIGH_UNCERTAINTY = 1 << 6
URBAN_HOTSPOT = 1 << 7

FLAG_NAMES: dict[int, str] = {
    CLOUD: "cloud",
    WATER: "water",
    SNOW: "snow",
    LOW_EMISSIVITY: "low_emissivity_confidence",
    MISSING_BAND: "missing_band",
    INTERPOLATED: "interpolated",
    HIGH_UNCERTAINTY: "high_uncertainty",
    URBAN_HOTSPOT: "urban_hotspot",
}


def create_quality_mask(
    shape: tuple[int, ...],
    cloud_mask: np.ndarray | None = None,
    ndvi: np.ndarray | None = None,
    uncertainty: np.ndarray | None = None,
    lst: np.ndarray | None = None,
    uncertainty_threshold: float = 3.0,
    lst_percentile_threshold: float = 90.0,
) -> np.ndarray:
    qa = np.zeros(shape, dtype=np.uint8)

    if cloud_mask is not None:
        qa[cloud_mask > 0] |= CLOUD

    if ndvi is not None:
        qa[ndvi < 0] |= WATER
        qa[(ndvi > 0) & (ndvi < 0.1)] |= SNOW

    if ndvi is not None:
        emissivity_confidence = np.ones_like(ndvi, dtype=bool)
        emissivity_confidence[(ndvi >= 0) & (ndvi < 0.2)] = False
        qa[~emissivity_confidence] |= LOW_EMISSIVITY

    if uncertainty is not None:
        qa[uncertainty > uncertainty_threshold] |= HIGH_UNCERTAINTY

    if lst is not None:
        threshold = np.percentile(lst, lst_percentile_threshold)
        qa[lst > threshold] |= URBAN_HOTSPOT

    return qa


def interpret_flags(qa_value: int) -> list[str]:
    flags = []
    for mask_val, name in sorted(FLAG_NAMES.items()):
        if qa_value & mask_val:
            flags.append(name)
    return flags


def describe_qa_mask(qa: np.ndarray) -> dict[str, float]:
    total = qa.size
    description = {}
    for mask_val, name in FLAG_NAMES.items():
        count = int(np.sum((qa & mask_val) > 0))
        description[name] = round(count / total * 100, 2)
    description["clean"] = round(np.sum(qa == 0) / total * 100, 2)
    return description
