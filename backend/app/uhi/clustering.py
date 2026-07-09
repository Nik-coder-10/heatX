import logging
import numpy as np

from .exceptions import ClusteringError

logger = logging.getLogger("app.uhi.clustering")

DBSCAN_AVAILABLE = False
try:
    from sklearn.cluster import DBSCAN
    DBSCAN_AVAILABLE = True
except ImportError:
    pass


def cluster_dbscan(
    coords_pixel: np.ndarray,
    eps_pixels: float = 3.0,
    min_samples: int = 10,
    resolution: float = 30.0,
) -> np.ndarray:
    if not DBSCAN_AVAILABLE:
        raise ClusteringError("scikit-learn is required for DBSCAN clustering")

    if coords_pixel.shape[0] < min_samples:
        labels = np.arange(coords_pixel.shape[0])
        logger.debug("Fewer points than min_samples; assigning individual labels")
        return labels

    coords_meters = coords_pixel.astype(np.float64) * resolution
    clusterer = DBSCAN(eps=eps_pixels * resolution, min_samples=min_samples, n_jobs=-1)
    labels = clusterer.fit_predict(coords_meters)
    n_clusters = len(set(labels) - {-1})
    n_noise = int((labels == -1).sum())
    logger.debug("DBSCAN: %d clusters, %d noise points", n_clusters, n_noise)
    return labels


def merge_clusters_by_overlap(
    labeled_mask: np.ndarray,
    overlap_threshold: float = 0.5,
) -> np.ndarray:
    labels = np.unique(labeled_mask)
    labels = labels[labels > 0]
    if len(labels) < 2:
        return labeled_mask

    result = labeled_mask.copy()
    changed = True
    while changed:
        changed = False
        for i in range(1, len(labels) + 1):
            for j in range(i + 1, len(labels) + 1):
                mask_i = result == i
                mask_j = result == j
                if mask_i.sum() == 0 or mask_j.sum() == 0:
                    continue
                from scipy.ndimage import binary_dilation
                dilated = binary_dilation(mask_i, iterations=1)
                overlap = dilated & mask_j
                if overlap.sum() / min(mask_i.sum(), mask_j.sum()) > overlap_threshold:
                    result[mask_j] = i
                    changed = True
        if changed:
            relabeled, _ = result.copy(), 0
            from scipy.ndimage import label as nd_label
            result, _ = nd_label(result > 0)
    return result


def filter_small_clusters(
    labeled_mask: np.ndarray,
    min_pixels: int = 10,
) -> np.ndarray:
    ids, counts = np.unique(labeled_mask, return_counts=True)
    for cid, cnt in zip(ids, counts):
        if cid == 0:
            continue
        if cnt < min_pixels:
            labeled_mask[labeled_mask == cid] = 0
    return labeled_mask


def recluster_noise_points(
    binary_mask: np.ndarray,
    min_pixels: int = 5,
    connectivity: int = 2,
) -> np.ndarray:
    from scipy.ndimage import label as nd_label
    labeled, _ = nd_label(binary_mask, structure=np.ones((connectivity + 1,) * 2))
    return labeled
