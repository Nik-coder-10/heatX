class LSTError(Exception):
    pass


class SatelliteNotSupportedError(LSTError):
    pass


class MissingThermalBandError(LSTError):
    pass


class MissingSupportBandError(LSTError):
    pass


class RadianceConversionError(LSTError):
    pass


class BrightnessTemperatureError(LSTError):
    pass


class EmissivityError(LSTError):
    pass


class AtmosphericError(LSTError):
    pass


class AlgorithmNotAvailableError(LSTError):
    pass


class UncertaintyError(LSTError):
    pass


class ValidationError(LSTError):
    pass


class ComputationError(LSTError):
    pass
