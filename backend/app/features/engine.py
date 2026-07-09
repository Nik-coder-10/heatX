import logging
import numpy as np

from .feature_cube import GeoFeatureCube
from .registry import get, list_features, list_feature_names, list_categories
from .exceptions import FeatureError, MissingDependencyError
from .configuration import FeaturePipelineConfig
from .validator import validate_feature_cube, validate_features_consistency
from .statistics import compute_feature_statistics, compute_correlation_matrix, detect_outliers
from .selection import select_features
from .quality import dataset_quality_report
from .metadata import build_feature_metadata

logger = logging.getLogger("app.features.engine")

class GeoFeatureEngine:
    def __init__(self, config: FeaturePipelineConfig | dict | None = None):
        if config is None:
            self.config = FeaturePipelineConfig.defaults()
        elif isinstance(config, dict):
            self.config = FeaturePipelineConfig.from_dict(config)
        else:
            self.config = config
        self._cube: GeoFeatureCube | None = None
        self.cache: dict = {}

    def extract_features(
        self,
        lst_kelvin=None, brightness_temp=None, emissivity=None,
        red=None, nir=None, green=None, blue=None, swir1=None, swir2=None,
        ndvi=None, elevation=None, transform=None,
        acquisition_date=None, quality_mask=None, uncertainty=None,
        resolution=30.0,
    ) -> dict[str, np.ndarray]:
        from .extractor import extract_all_features
        logger.info("Extracting features from raster data...")
        features = extract_all_features(
            lst_kelvin=lst_kelvin, brightness_temp=brightness_temp,
            emissivity=emissivity,
            red=red, nir=nir, green=green, blue=blue,
            swir1=swir1, swir2=swir2, ndvi=ndvi,
            elevation=elevation, transform=transform,
            acquisition_date=acquisition_date,
            quality_mask=quality_mask, uncertainty=uncertainty,
            config=vars(self.config), resolution=resolution,
        )
        logger.info("Extracted %d features", len(features))
        return features

    def build_cube(
        self,
        features,
        geometry=None, crs=None, transform=None,
        quality=None, timestamps=None,
    ):
        validate_features_consistency(features)
        shape = None
        first = next(iter(features.values()))
        if first.ndim >= 2:
            shape = first.shape[:2]

        meta = build_feature_metadata(
            n_features=len(features),
            n_categories=len(list_categories()),
            feature_names=list(features.keys()),
            categories=list_categories(),
            crs=crs,
        )

        cube = GeoFeatureCube(
            features=features,
            geometry=geometry,
            metadata=meta,
            quality=quality,
            timestamps=timestamps,
            crs=crs,
            transform=transform,
            shape=shape,
        )
        self._cube = cube

        if self.config.validate_output:
            warnings = validate_feature_cube(cube)
            for w in warnings:
                logger.warning("Validation: %s", w)

        if self.config.compute_statistics:
            cube.metadata["statistics"] = compute_feature_statistics(features)

        return cube

    def run_selection(self, cube=None):
        cube = cube or self._cube
        if cube is None:
            raise FeatureError("No feature cube available")
        methods = self.config.selection_methods or ["variance", "correlation"]
        selected = select_features(cube.features, methods=methods)
        cube.metadata["feature_selection"] = selected
        return selected

    def compute_statistics(self, cube=None):
        cube = cube or self._cube
        if cube is None:
            raise FeatureError("No feature cube available")
        stats = compute_feature_statistics(cube.features, cube.feature_names)
        corr = compute_correlation_matrix(cube.features, cube.feature_names)
        outliers = detect_outliers(cube.features, cube.feature_names)
        quality = dataset_quality_report(cube)
        return {
            "statistics": stats,
            "correlation": corr,
            "outliers": outliers,
            "quality": quality,
        }

    def run_pipeline(
        self,
        lst_kelvin=None, brightness_temp=None, emissivity=None,
        red=None, nir=None, green=None, blue=None, swir1=None, swir2=None,
        ndvi=None, elevation=None, transform=None,
        acquisition_date=None, quality_mask=None, uncertainty=None,
        geometry=None, crs=None, resolution=30.0,
        export_path=None, export_format="parquet",
    ):
        features = self.extract_features(
            lst_kelvin=lst_kelvin, brightness_temp=brightness_temp,
            emissivity=emissivity,
            red=red, nir=nir, green=green, blue=blue,
            swir1=swir1, swir2=swir2, ndvi=ndvi,
            elevation=elevation, transform=transform,
            acquisition_date=acquisition_date,
            quality_mask=quality_mask, uncertainty=uncertainty,
            resolution=resolution,
        )

        cube = self.build_cube(
            features, geometry=geometry, crs=crs, transform=transform,
            quality=quality_mask,
        )

        if self.config.run_selection:
            self.run_selection(cube)

        analysis = self.compute_statistics(cube)
        cube.metadata["analysis"] = analysis

        if export_path:
            from .exporters import export_cube
            export_cube(cube, export_path, format=export_format)

        return cube

