from enum import Enum


class UserRole(str, Enum):
    ADMIN = "administrator"
    RESEARCHER = "researcher"
    PLANNER = "planner"
    VIEWER = "viewer"
    GUEST = "guest"


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class SatelliteProvider(str, Enum):
    LANDSAT_8 = "landsat_8"
    LANDSAT_9 = "landsat_9"
    SENTINEL_2 = "sentinel_2"
    MODIS = "modis"
    ISRO_BHUVAN = "isro_bhuvan"
    OTHER = "other"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RecommendationType(str, Enum):
    TREE_PLANTATION = "tree_plantation"
    COOL_ROOF = "cool_roof"
    GREEN_ROOF = "green_roof"
    REFLECTIVE_PAVEMENT = "reflective_pavement"
    WATER_BODY_RESTORATION = "water_body_restoration"
    URBAN_GREEN_SPACE = "urban_green_space"


class SeverityLevel(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"
    EXTREME = "extreme"


class PredictionModel(str, Enum):
    RANDOM_FOREST = "random_forest"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    CNN = "cnn"
    LSTM = "lstm"
    HYBRID = "hybrid"


class ReportType(str, Enum):
    SUMMARY = "summary"
    TECHNICAL = "technical"
    HEATMAP = "heatmap"
    GIS = "gis"
    PREDICTION = "prediction"
    MITIGATION = "mitigation"


class Visibility(str, Enum):
    PRIVATE = "private"
    TEAM = "team"
    PUBLIC = "public"