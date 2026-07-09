from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class GeoFeatureCube:
    features: dict[str, np.ndarray]
    geometry: np.ndarray | None = None
    metadata: dict | None = None
    quality: np.ndarray | None = None
    timestamps: np.ndarray | None = None
    crs: str | None = None
    transform: Any | None = None
    shape: tuple[int, int] | None = None
    feature_names: list[str] | None = None
    n_pixels: int = 0

    def __post_init__(self):
        if self.feature_names is None:
            self.feature_names = list(self.features.keys())
        first_key = next(iter(self.features))
        arr = self.features[first_key]
        if self.shape is None and arr.ndim >= 2:
            self.shape = arr.shape[:2]
        if self.n_pixels == 0 and arr.ndim >= 2:
            self.n_pixels = int(np.prod(arr.shape[:2]))

    def get(self, name: str) -> np.ndarray:
        return self.features[name]

    def to_flat_array(self) -> np.ndarray:
        rows = []
        for name in self.feature_names:
            arr = self.features[name]
            rows.append(arr.ravel())
        return np.column_stack(rows)

    def feature_names_for_category(self, category: str, registry: "FeatureRegistry" = None) -> list[str]:
        if registry is None:
            from .registry import list_feature_names
            all_in_cat = list_feature_names(category)
            return [n for n in self.feature_names if n in all_in_cat]
        return [n for n in self.feature_names if n in list_feature_names(category)]

    def subset(self, names: list[str]) -> "GeoFeatureCube":
        new_features = {n: self.features[n] for n in names if n in self.features}
        return GeoFeatureCube(
            features=new_features,
            geometry=self.geometry,
            metadata=self.metadata,
            quality=self.quality,
            timestamps=self.timestamps,
            crs=self.crs,
            transform=self.transform,
            shape=self.shape,
            feature_names=list(new_features.keys()),
        )

    def to_dict(self) -> dict:
        return {
            "features": {k: v.tolist() if hasattr(v, "tolist") else v for k, v in self.features.items()},
            "feature_names": self.feature_names,
            "shape": self.shape,
            "n_pixels": self.n_pixels,
            "crs": self.crs,
            "metadata": self.metadata,
        }
