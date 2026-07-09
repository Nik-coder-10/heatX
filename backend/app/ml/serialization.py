import logging
import os
from typing import Any

from .exceptions import SerializationError

logger = logging.getLogger("app.ml.serialization")


def save_joblib(model: Any, path: str) -> str:
    import joblib
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    joblib.dump(model, path)
    logger.info("Model saved to %s (joblib)", path)
    return path


def load_joblib(path: str) -> Any:
    import joblib
    if not os.path.exists(path):
        raise SerializationError(f"Model file not found: {path}")
    model = joblib.load(path)
    logger.info("Model loaded from %s (joblib)", path)
    return model


def save_pickle(model: Any, path: str) -> str:
    import pickle
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(model, f)
    logger.info("Model saved to %s (pickle)", path)
    return path


def load_pickle(path: str) -> Any:
    import pickle
    if not os.path.exists(path):
        raise SerializationError(f"Model file not found: {path}")
    with open(path, "rb") as f:
        model = pickle.load(f)
    logger.info("Model loaded from %s (pickle)", path)
    return model


def save_onnx(model: Any, path: str, X_sample: Any) -> str:
    try:
        import onnx
        from skl2onnx import convert_sklearn
        from skl2onnx.common.data_types import FloatTensorType
    except ImportError:
        raise SerializationError("skl2onnx required for ONNX export")

    n_features = X_sample.shape[1] if hasattr(X_sample, "shape") else 1
    initial_type = [("float_input", FloatTensorType([None, n_features]))]

    onnx_model = convert_sklearn(model, initial_types=initial_type)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(onnx_model.SerializeToString())
    logger.info("Model saved to %s (ONNX)", path)
    return path


def save_torchscript(model: Any, path: str, example_input: Any) -> str:
    try:
        import torch
    except ImportError:
        raise SerializationError("torch required for TorchScript export")

    model.eval()
    traced = torch.jit.trace(model, example_input)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    traced.save(path)
    logger.info("Model saved to %s (TorchScript)", path)
    return path


def save_savedmodel(model: Any, path: str) -> str:
    try:
        import tensorflow as tf
    except ImportError:
        raise SerializationError("tensorflow required for SavedModel export")

    model.save(path)
    logger.info("Model saved to %s (SavedModel)", path)
    return path


def serialize_model(
    model: Any,
    path: str,
    format: str = "joblib",
    X_sample: Any = None,
) -> str:
    exporters = {
        "joblib": lambda: save_joblib(model, path),
        "pickle": lambda: save_pickle(model, path),
        "onnx": lambda: save_onnx(model, path, X_sample),
    }

    if format not in exporters:
        raise SerializationError(f"Unsupported serialization format: {format}")

    return exporters[format]()


def deserialize_model(path: str, format: str = "joblib") -> Any:
    loaders = {
        "joblib": load_joblib,
        "pickle": load_pickle,
    }

    if format not in loaders:
        raise SerializationError(f"Unsupported deserialization format: {format}")

    return loaders[format](path)
