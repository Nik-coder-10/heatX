import logging
import numpy as np

logger = logging.getLogger("app.uhi.quality")


def compute_confidence(
    binary_mask: np.ndarray,
    lst_celsius: np.ndarray | None = None,
    sub_results: dict | None = None,
    quality_mask: np.ndarray | None = None,
    method: str = "ensemble",
) -> np.ndarray:
    confidence = np.zeros(binary_mask.shape, dtype=np.float32)

    if method == "ensemble" and sub_results:
        n_methods = len(sub_results)
        if n_methods > 0:
            for method_name, mask_list in sub_results.items():
                mask = np.array(mask_list, dtype=np.float32).reshape(binary_mask.shape)
                confidence += mask
            confidence /= n_methods
    elif lst_celsius is not None:
        data = lst_celsius.astype(np.float64)
        valid = np.isfinite(data)
        if valid.any():
            norm = (data - np.nanmin(data)) / (np.nanmax(data) - np.nanmin(data) + 1e-10)
            confidence = np.clip(norm, 0.0, 1.0).astype(np.float32) * 0.8 + 0.2

    if quality_mask is not None:
        qa_penalty = ((quality_mask & 1) > 0).astype(np.float32) * 0.3
        confidence = np.clip(confidence - qa_penalty, 0.0, 1.0)

    confidence[binary_mask == 0] = 0.0
    return confidence


def hotspot_confidence_from_mask(confidence_map: np.ndarray, hotspot_mask: np.ndarray) -> float:
    mask = hotspot_mask > 0
    if mask.sum() == 0:
        return 0.0
    return float(np.mean(confidence_map[mask]))


def compute_boundary_confidence(
    binary_mask: np.ndarray,
    lst_gradient: np.ndarray | None = None,
) -> float:
    from scipy.ndimage import binary_dilation, binary_erosion
    boundary = binary_dilation(binary_mask) & ~binary_erosion(binary_mask)
    if boundary.sum() == 0:
        return 0.5
    if lst_gradient is not None:
        grad_at_boundary = lst_gradient[boundary]
        mean_grad = float(np.mean(grad_at_boundary))
        conf = min(1.0, mean_grad / 5.0)
        return conf
    return 0.7


def compute_data_completeness(
    lst_celsius: np.ndarray,
    quality_mask: np.ndarray | None = None,
) -> float:
    valid = np.isfinite(lst_celsius)
    if quality_mask is not None:
        cloud = (quality_mask & 1) > 0
        valid = valid & ~cloud
    return float(valid.sum()) / lst_celsius.size if lst_celsius.size > 0 else 0.0


def compute_overall_quality_score(
    hotspot,
    data_completeness: float,
    boundary_conf: float,
    hotspot_conf: float,
    missing_pct: float = 0.0,
) -> float:
    score = (
        hotspot_conf * 0.4
        + boundary_conf * 0.2
        + data_completeness * 0.2
        + (1.0 - missing_pct) * 0.2
    )
    return float(np.clip(score, 0.0, 1.0))
