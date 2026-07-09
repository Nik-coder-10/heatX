import logging
import numpy as np

from .exceptions import ExportError
from .feature_cube import GeoFeatureCube

logger = logging.getLogger("app.features.exporters")


def to_parquet(cube, path, compression="zstd"):
    import pandas as pd
    df = pd.DataFrame({k: v.ravel() for k, v in cube.features.items()})
    df.to_parquet(path, compression=compression, index=False)
    return path

def to_arrow(cube, path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    arrays = [pa.array(v.ravel().astype(str) if v.dtype.kind == "U" else v.ravel()) 
              for v in cube.features.values()]
    table = pa.table(dict(zip(cube.feature_names, arrays)))
    pq.write_table(table, path)
    return path

def to_csv(cube, path):
    import pandas as pd
    df = pd.DataFrame({k: v.ravel() for k, v in cube.features.items()})
    df.to_csv(path, index=False)
    return path

def to_geojson(cube, path):
    import json
    features_list = []
    names = cube.feature_names
    flat = {k: v.ravel() for k, v in cube.features.items()}
    n = cube.n_pixels
    for i in range(min(n, 10000)):
        props = {k: float(flat[k][i]) if hasattr(flat[k][i], "item") else flat[k][i] for k in names}
        feat = {"type": "Feature", "properties": props}
        if cube.geometry is not None and len(cube.geometry) > i:
            feat["geometry"] = cube.geometry[i]
        features_list.append(feat)
    geojson = {"type": "FeatureCollection", "features": features_list}
    with open(path, "w") as f:
        json.dump(geojson, f)
    return path

def to_numpy(cube, path=None):
    arr = cube.to_flat_array()
    if path:
        np.save(path, arr)
    return arr

def to_pytorch(cube):
    try:
        import torch
        arr = cube.to_flat_array()
        arr = np.nan_to_num(arr, nan=0.0)
        return torch.from_numpy(arr).float()
    except ImportError:
        raise ExportError("PyTorch not installed")

def to_tensorflow(cube):
    try:
        import tensorflow as tf
        arr = cube.to_flat_array()
        arr = np.nan_to_num(arr, nan=0.0)
        return tf.convert_to_tensor(arr, dtype=tf.float32)
    except ImportError:
        raise ExportError("TensorFlow not installed")

def to_xgboost(cube, label=None):
    try:
        import xgboost as xgb
        arr = cube.to_flat_array()
        arr = np.nan_to_num(arr, nan=0.0)
        if label is not None:
            return xgb.DMatrix(arr, label=label)
        return xgb.DMatrix(arr)
    except ImportError:
        raise ExportError("XGBoost not installed")

def to_lightgbm(cube, label=None):
    try:
        import lightgbm as lgb
        arr = cube.to_flat_array()
        arr = np.nan_to_num(arr, nan=0.0)
        if label is not None:
            return lgb.Dataset(arr, label=label)
        return lgb.Dataset(arr)
    except ImportError:
        raise ExportError("LightGBM not installed")

EXPORT_FORMATS = {
    "parquet": to_parquet,
    "arrow": to_arrow,
    "csv": to_csv,
    "geojson": to_geojson,
    "numpy": to_numpy,
}

def export_cube(cube, path, format="parquet", **kwargs):
    if format not in EXPORT_FORMATS:
        raise ExportError(f"Unsupported format: {format}. Available: {list(EXPORT_FORMATS)}")
    logger.info("Exporting feature cube to %s (%s)", path, format)
    return EXPORT_FORMATS[format](cube, path, **kwargs)
