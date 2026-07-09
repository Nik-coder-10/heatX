class IndicesError(Exception):
    pass


class IndexNotFoundError(IndicesError):
    pass


class MissingBandError(IndicesError):
    pass


class DimensionMismatchError(IndicesError):
    pass


class NoDataPropagationError(IndicesError):
    pass


class CRSMismatchError(IndicesError):
    pass


class ResolutionMismatchError(IndicesError):
    pass


class InvalidRangeError(IndicesError):
    pass


class ComputationError(IndicesError):
    pass


class ClassificationError(IndicesError):
    pass


class VisualizationError(IndicesError):
    pass


class StatisticsError(IndicesError):
    pass
