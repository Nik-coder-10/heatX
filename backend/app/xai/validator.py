import logging

import numpy as np

from .exceptions import ValidationError

logger = logging.getLogger("app.xai.validator")


def validate_prediction_exists(model, X) -> bool:
    try:
        pred = model.predict(X[:1])
        return pred is not None and len(pred) > 0
    except Exception as e:
        raise ValidationError(f"Cannot make prediction: {e}")


def validate_required_features(
    X: np.ndarray,
    feature_names: list[str],
    required: list[str] | None = None,
) -> bool:
    if required is None:
        required = ["lst_celsius", "ndvi", "ndbi", "ndwi"]
    missing = [f for f in required if f not in feature_names]
    if missing:
        raise ValidationError(f"Missing required features: {missing}")
    return True


def validate_feature_names_consistent(
    X: np.ndarray,
    feature_names: list[str],
    model_feature_names: list[str] | None = None,
) -> bool:
    if model_feature_names is not None:
        if set(feature_names) != set(model_feature_names):
            missing_in_model = set(feature_names) - set(model_feature_names)
            missing_in_data = set(model_feature_names) - set(feature_names)
            msg = []
            if missing_in_model:
                msg.append(f"Features missing from model: {missing_in_model}")
            if missing_in_data:
                msg.append(f"Features missing from data: {missing_in_data}")
            if msg:
                raise ValidationError("; ".join(msg))
    if X.shape[1] != len(feature_names):
        raise ValidationError(
            f"Feature count mismatch: X has {X.shape[1]} columns but "
            f"feature_names has {len(feature_names)} entries"
        )
    return True


def validate_model_compatibility(model) -> bool:
    if not hasattr(model, "predict"):
        raise ValidationError("Model must have a predict method")
    return True


def validate_missing_values(X: np.ndarray, max_nan_fraction: float = 0.1) -> bool:
    if X.size == 0:
        raise ValidationError("Empty input data")
    nan_frac = float(np.isnan(X).mean())
    if nan_frac > max_nan_fraction:
        raise ValidationError(
            f"Too many missing values: {nan_frac:.1%} > {max_nan_fraction:.1%}"
        )
    return True


def validate_geo_feature_cube(cube) -> bool:
    if not hasattr(cube, "features"):
        raise ValidationError("Input must have a 'features' dict")
    if not hasattr(cube, "feature_names"):
        raise ValidationError("Input must have 'feature_names'")
    if len(cube.features) == 0:
        raise ValidationError("Feature cube is empty")
    return True


def validate_hotspot(hotspot) -> bool:
    if not hasattr(hotspot, "id"):
        raise ValidationError("Hotspot must have an id")
    if not hasattr(hotspot, "severity"):
        raise ValidationError("Hotspot must have a severity")
    return True
