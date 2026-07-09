class PreprocessingError(Exception):
    pass


class InvalidInputError(PreprocessingError):
    pass


class CloudMaskError(PreprocessingError):
    pass


class NoDataError(PreprocessingError):
    pass


class ResamplingError(PreprocessingError):
    pass


class AlignmentError(PreprocessingError):
    pass


class NormalizationError(PreprocessingError):
    pass


class MosaicError(PreprocessingError):
    pass


class QualityError(PreprocessingError):
    pass


class BandMathError(PreprocessingError):
    pass


class ConfigurationError(PreprocessingError):
    pass


class PipelineExecutionError(PreprocessingError):
    pass
