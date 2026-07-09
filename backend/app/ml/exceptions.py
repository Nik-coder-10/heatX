class MLError(Exception):
    pass

class TrainingError(MLError):
    pass

class PredictionError(MLError):
    pass

class ModelNotSupportedError(MLError):
    pass

class ConfigurationError(MLError):
    pass

class ValidationError(MLError):
    pass

class DriftDetectedError(MLError):
    pass

class SerializationError(MLError):
    pass

class ModelNotFoundError(MLError):
    pass

class FeaturePipelineError(MLError):
    pass

class EnsembleError(MLError):
    pass
