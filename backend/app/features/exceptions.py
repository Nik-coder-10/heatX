class FeatureError(Exception):
    pass

class FeatureNotFoundError(FeatureError):
    pass

class ExtractionError(FeatureError):
    pass

class FeatureCubeError(FeatureError):
    pass

class ExportError(FeatureError):
    pass

class ValidationError(FeatureError):
    pass

class ConfigurationError(FeatureError):
    pass

class CacheError(FeatureError):
    pass

class MissingDependencyError(FeatureError):
    pass

class DimensionMismatchError(FeatureError):
    pass

class CRSMismatchError(FeatureError):
    pass
