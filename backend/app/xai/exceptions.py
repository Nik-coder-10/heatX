class XAIError(Exception):
    pass

class ExplainabilityError(XAIError):
    pass

class ModelNotSupportedError(XAIError):
    pass

class MissingFeaturesError(XAIError):
    pass

class ExplanationError(XAIError):
    pass

class CounterfactualError(XAIError):
    pass

class VisualizationError(XAIError):
    pass

class ConfigurationError(XAIError):
    pass

class UncertaintyError(XAIError):
    pass

class ConfidenceError(XAIError):
    pass

class ValidationError(XAIError):
    pass
