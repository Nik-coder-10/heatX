class SimulationError(Exception):
    pass

class ConfigurationError(SimulationError):
    pass

class ScenarioNotFoundError(SimulationError):
    pass

class InvalidParameterError(SimulationError):
    pass

class ForecastError(SimulationError):
    pass

class ComparisonError(SimulationError):
    pass
