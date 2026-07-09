import logging
import numpy as np

from .exceptions import ValidationError
from .registry import get, list_feature_names

logger = logging.getLogger("app.features.validator")


def validate_feature_cube(cube: "GeoFeatureCube") -> list[str]:
    warnings = []
    for name in cube.feature_names:
        arr = cube.features.get(name)
        if arr is None:
            warnings.append(f"Missing feature array: {name}")
            continue
        try:
            fd = get(name)
        except Exception:
            warnings.append(f"Unknown feature: {name}")
            continue

        if np.issubdtype(arr.dtype, np.floating):
            finite = np.isfinite(arr).sum()
            total = arr.size
            if finite < total:
                warnings.append(
                    f"Feature '{name}': {total - finite}/{total} non-finite values"
                )

    if cube.shape:
        for name in cube.feature_names:
            arr = cube.features.get(name)
            if arr is not None and arr.shape[:2] != cube.shape:
                warnings.append(
                    f"Feature '{name}' shape {arr.shape[:2]} != cube shape {cube.shape}"
                )

    return warnings


def validate_features_consistency(
    features: dict[str, np.ndarray],
    require_all: list[str] | None = None,
) -> None:
    if not features:
        raise ValidationError("Empty feature dict")
    if require_all:
        for name in require_all:
            if name not in features:
                raise ValidationError(f"Required feature missing: {name}")
    shapes = [(k, v.shape) for k, v in features.items()]
    ref_shape = shapes[0][1]
    for name, shape in shapes[1:]:
        if shape != ref_shape:
            raise ValidationError(
                f"Shape mismatch: '{name}' {shape} != '{shapes[0][0]}' {ref_shape}"
            )
