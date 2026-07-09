import logging
import numpy as np
from scipy import ndimage, stats

from .exceptions import DetectionError, MissingFeatureError
from .configuration import UHIDetectionConfig

logger = logging.getLogger("app.uhi.detector")


def detect_adaptive_threshold(
    lst_celsius, mask=None, config=None, rural_mask=None
):
    cfg = config or UHIDetectionConfig.defaults()
    data = lst_celsius.astype(np.float64).copy()
    if mask is not None:
        data[~mask] = np.nan
    valid = np.isfinite(data)
    if not valid.any():
        raise DetectionError("No valid data for adaptive threshold detection")

    vals = data[valid]
    if rural_mask is not None:
        rural = lst_celsius.astype(np.float64).copy()
        rural[~rural_mask] = np.nan
        rural_vals = rural[np.isfinite(rural)]
        if len(rural_vals) > 0:
            rural_mean = np.mean(rural_vals)
            rural_std = np.std(rural_vals)
            threshold = rural_mean + cfg.adaptive_k * rural_std
        else:
            threshold = np.percentile(vals, cfg.percentile)
    else:
        threshold = np.percentile(vals, cfg.percentile)

    binary = np.zeros(data.shape, dtype=np.uint8)
    binary[valid & (data > threshold)] = 1

    return {
        "binary_mask": binary,
        "threshold": float(threshold),
        "method": "adaptive_threshold",
        "n_hot_pixels": int(binary.sum()),
    }


def detect_zscore(lst_celsius, mask=None, config=None):
    cfg = config or UHIDetectionConfig.defaults()
    data = lst_celsius.astype(np.float64).copy()
    if mask is not None:
        data[~mask] = np.nan

    local_mean = ndimage.uniform_filter(data, size=15, mode="reflect")
    local_std = ndimage.generic_filter(data, np.nanstd, size=15, mode="reflect")
    local_std = np.maximum(local_std, 0.01)

    zscore = (data - local_mean) / local_std
    binary = np.zeros(data.shape, dtype=np.uint8)
    valid = np.isfinite(zscore)
    binary[valid & (zscore > cfg.zscore_threshold)] = 1

    return {
        "binary_mask": binary,
        "zscore_map": zscore.astype(np.float32),
        "threshold": float(cfg.zscore_threshold),
        "method": "zscore",
        "n_hot_pixels": int(binary.sum()),
    }


def detect_percentile(lst_celsius, mask=None, config=None):
    cfg = config or UHIDetectionConfig.defaults()
    data = lst_celsius.astype(np.float64).copy()
    if mask is not None:
        data[~mask] = np.nan
    valid = np.isfinite(data)
    if not valid.any():
        raise DetectionError("No valid data for percentile detection")

    threshold = np.percentile(data[valid], cfg.percentile)
    binary = np.zeros(data.shape, dtype=np.uint8)
    binary[valid & (data > threshold)] = 1

    return {
        "binary_mask": binary,
        "threshold": float(threshold),
        "method": "percentile",
        "n_hot_pixels": int(binary.sum()),
    }


def detect_morans_i(lst_celsius, mask=None, config=None):
    cfg = config or UHIDetectionConfig.defaults()
    data = lst_celsius.astype(np.float64).copy()
    if mask is not None:
        data[~mask] = np.nan

    try:
        import libpysal
        import esda
        from libpysal.weights import lat2W
        has_pysal = True
    except ImportError:
        has_pysal = False

    if has_pysal:
        h, w = data.shape
        W = lat2W(h, w)
        flat = data.ravel()
        nan_mask = np.isnan(flat)
        if nan_mask.sum() > 0.5 * flat.size:
            raise DetectionError("Too many NaN values for Moran's I")
        valid_idx = np.where(~nan_mask)[0]
        flat_valid = flat[~nan_mask]
        if len(valid_idx) < 100:
            raise DetectionError("Insufficient valid pixels for Moran's I")
        W_sub = libpysal.weights.W_subset(W, valid_idx.tolist())
        li = esda.Moran_Local(flat_valid, W_sub)
        moran_map = np.full(h * w, np.nan)
        moran_map[valid_idx] = li.Is
        moran_map = moran_map.reshape(h, w)
        p_map = np.full(h * w, 1.0)
        p_map[valid_idx] = li.p_sim
        p_map = p_map.reshape(h, w)
        binary = np.zeros(data.shape, dtype=np.uint8)
        sig_high = (moran_map > 0) & (p_map < 0.05) & (data > np.nanmean(data))
        binary[sig_high] = 1
        return {
            "binary_mask": binary,
            "morans_i_map": moran_map.astype(np.float32),
            "p_value_map": p_map.astype(np.float32),
            "method": "morans_i",
            "n_hot_pixels": int(binary.sum()),
        }
    else:
        logger.warning("PySAL not available, using percentile fallback")
        return detect_percentile(lst_celsius, mask, config)


def detect_dbscan(lst_celsius, mask=None, config=None):
    cfg = config or UHIDetectionConfig.defaults()
    data = lst_celsius.astype(np.float64).copy()
    if mask is not None:
        data[~mask] = np.nan

    valid = np.isfinite(data)
    threshold = np.percentile(data[valid], cfg.percentile)
    hot_mask = valid & (data > threshold)
    if hot_mask.sum() == 0:
        return {"binary_mask": np.zeros(data.shape, dtype=np.uint8),
                "method": "dbscan", "n_hot_pixels": 0}

    ys, xs = np.where(hot_mask)
    coords = np.column_stack([xs, ys]) * cfg.resolution

    from sklearn.cluster import DBSCAN as SKDBSCAN
    clustering = SKDBSCAN(eps=cfg.dbscan_eps, min_samples=cfg.dbscan_min_samples).fit(coords)
    labels = clustering.labels_

    binary = np.zeros(data.shape, dtype=np.uint8)
    noise_mask = labels == -1
    valid_clusters = labels[~noise_mask] if (~noise_mask).sum() > 0 else np.array([])
    if len(valid_clusters) > 0:
        rows = ys[~noise_mask]
        cols = xs[~noise_mask]
        binary[rows, cols] = 1

    return {
        "binary_mask": binary,
        "method": "dbscan",
        "n_hot_pixels": int(binary.sum()),
        "n_clusters": int(len(set(valid_clusters))) if len(valid_clusters) > 0 else 0,
    }


def detect_connected_components(binary_mask):
    labeled, n_features = ndimage.label(binary_mask)
    return {
        "labeled_mask": labeled.astype(np.int32),
        "n_components": int(n_features),
        "method": "connected_components",
    }


def detect_hybrid(lst_celsius, mask=None, config=None, rural_mask=None):
    cfg = config or UHIDetectionConfig.defaults()
    weights = cfg.hybrid_weights or {
        "adaptive_threshold": 0.3,
        "zscore": 0.3,
        "percentile": 0.2,
        "dbscan": 0.2,
    }

    results = {}
    rr = detect_adaptive_threshold(lst_celsius, mask, cfg, rural_mask)
    results["adaptive_threshold"] = rr["binary_mask"]

    try:
        rz = detect_zscore(lst_celsius, mask, cfg)
        results["zscore"] = rz["binary_mask"]
    except Exception as e:
        results["zscore"] = np.zeros(lst_celsius.shape, dtype=np.uint8)
        logger.warning("Z-score failed: %s", e)

    try:
        rp = detect_percentile(lst_celsius, mask, cfg)
        results["percentile"] = rp["binary_mask"]
    except Exception as e:
        results["percentile"] = np.zeros(lst_celsius.shape, dtype=np.uint8)
        logger.warning("Percentile failed: %s", e)

    try:
        rd = detect_dbscan(lst_celsius, mask, cfg)
        results["dbscan"] = rd["binary_mask"]
    except Exception as e:
        results["dbscan"] = np.zeros(lst_celsius.shape, dtype=np.uint8)
        logger.warning("DBSCAN failed: %s", e)

    weighted = np.zeros(lst_celsius.shape, dtype=np.float64)
    for method_name, weight in weights.items():
        if method_name in results:
            weighted += results[method_name].astype(np.float64) * weight

    binary = (weighted >= 0.4).astype(np.uint8)

    return {
        "binary_mask": binary,
        "confidence_map": weighted.astype(np.float32),
        "sub_results": {k: v.tolist() for k, v in results.items()},
        "method": "hybrid",
        "n_hot_pixels": int(binary.sum()),
    }


DETECTORS = {
    "adaptive_threshold": detect_adaptive_threshold,
    "zscore": detect_zscore,
    "percentile": detect_percentile,
    "morans_i": detect_morans_i,
    "dbscan": detect_dbscan,
    "hybrid": detect_hybrid,
}

def run_detection(lst_celsius, method="hybrid", mask=None, config=None, rural_mask=None):
    if method not in DETECTORS:
        raise DetectionError(f"Unknown detection method: {method}")
    logger.info("Running UHI detection: method=%s", method)
    result = DETECTORS[method](lst_celsius, mask, config, rural_mask)
    logger.info("Detection complete: %d hotspot pixels", result.get("n_hot_pixels", 0))
    return result
