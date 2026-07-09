class UHIError(Exception):
    pass

class DetectionError(UHIError):
    pass

class SegmentationError(UHIError):
    pass

class InvalidMethodError(UHIError):
    pass

class MissingFeatureError(UHIError):
    pass

class GeometryError(UHIError):
    pass

class QualityError(UHIError):
    pass

class ClusteringError(UHIError):
    pass

class ConfigurationError(UHIError):
    pass
