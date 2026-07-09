import pytest
from app.database.enums import (
    UserRole,
    ProjectStatus,
    Visibility,
    ReportType,
    SatelliteProvider,
    ProcessingStatus,
    RecommendationType,
    SeverityLevel,
    PredictionModel,
)


def test_user_role_enum():
    """Test UserRole enum values and uniqueness."""
    assert UserRole.ADMIN.value == "administrator"
    assert UserRole.RESEARCHER.value == "researcher"
    assert UserRole.PLANNER.value == "planner"
    assert UserRole.VIEWER.value == "viewer"
    assert UserRole.GUEST.value == "guest"

    # Test that all values are unique
    values = [role.value for role in UserRole]
    assert len(values) == len(set(values))

    # Test that we have exactly the expected roles
    expected_roles = {"administrator", "researcher", "planner", "viewer", "guest"}
    actual_roles = set(values)
    assert actual_roles == expected_roles


def test_project_status_enum():
    """Test ProjectStatus enum values and uniqueness."""
    assert ProjectStatus.DRAFT.value == "draft"
    assert ProjectStatus.ACTIVE.value == "active"
    assert ProjectStatus.PROCESSING.value == "processing"
    assert ProjectStatus.COMPLETED.value == "completed"
    assert ProjectStatus.FAILED.value == "failed"
    assert ProjectStatus.ARCHIVED.value == "archived"

    # Test that all values are unique
    values = [status.value for status in ProjectStatus]
    assert len(values) == len(set(values))

    # Test that we have exactly the expected statuses
    expected_statuses = {"draft", "active", "processing", "completed", "failed", "archived"}
    actual_statuses = set(values)
    assert actual_statuses == expected_statuses


def test_visibility_enum():
    """Test Visibility enum values and uniqueness."""
    assert Visibility.PRIVATE.value == "private"
    assert Visibility.TEAM.value == "team"
    assert Visibility.PUBLIC.value == "public"

    # Test that all values are unique
    values = [visibility.value for visibility in Visibility]
    assert len(values) == len(set(values))

    # Test that we have exactly the expected visibility levels
    expected_visibilities = {"private", "team", "public"}
    actual_visibilities = set(values)
    assert actual_visibilities == expected_visibilities


def test_report_type_enum():
    """Test ReportType enum values and uniqueness."""
    assert ReportType.SUMMARY.value == "summary"
    assert ReportType.TECHNICAL.value == "technical"
    assert ReportType.HEATMAP.value == "heatmap"
    assert ReportType.GIS.value == "gis"
    assert ReportType.PREDICTION.value == "prediction"
    assert ReportType.MITIGATION.value == "mitigation"

    # Test that all values are unique
    values = [report_type.value for report_type in ReportType]
    assert len(values) == len(set(values))

    # Test that we have exactly the expected report types
    expected_types = {"summary", "technical", "heatmap", "gis", "prediction", "mitigation"}
    actual_types = set(values)
    assert actual_types == expected_types




def test_satellite_provider_enum():
    """Test SatelliteProvider enum values and uniqueness."""
    assert SatelliteProvider.LANDSAT_8.value == "landsat_8"
    assert SatelliteProvider.LANDSAT_9.value == "landsat_9"
    assert SatelliteProvider.SENTINEL_2.value == "sentinel_2"
    assert SatelliteProvider.MODIS.value == "modis"
    assert SatelliteProvider.ISRO_BHUVAN.value == "isro_bhuvan"
    assert SatelliteProvider.OTHER.value == "other"

    # Test that all values are unique
    values = [provider.value for provider in SatelliteProvider]
    assert len(values) == len(set(values))

    # Test that we have exactly the expected providers
    expected_providers = {
        "landsat_8",
        "landsat_9",
        "sentinel_2",
        "modis",
        "isro_bhuvan",
        "other",
    }
    actual_providers = set(values)
    assert actual_providers == expected_providers


def test_processing_status_enum():
    """Test ProcessingStatus enum values and uniqueness."""
    assert ProcessingStatus.PENDING.value == "pending"
    assert ProcessingStatus.QUEUED.value == "queued"
    assert ProcessingStatus.RUNNING.value == "running"
    assert ProcessingStatus.COMPLETED.value == "completed"
    assert ProcessingStatus.FAILED.value == "failed"
    assert ProcessingStatus.CANCELLED.value == "cancelled"

    # Test that all values are unique
    values = [status.value for status in ProcessingStatus]
    assert len(values) == len(set(values))

    # Test that we have exactly the expected statuses
    expected_statuses = {
        "pending",
        "queued",
        "running",
        "completed",
        "failed",
        "cancelled",
    }
    actual_statuses = set(values)
    assert actual_statuses == expected_statuses


def test_recommendation_type_enum():
    """Test RecommendationType enum values and uniqueness."""
    assert RecommendationType.TREE_PLANTATION.value == "tree_plantation"
    assert RecommendationType.COOL_ROOF.value == "cool_roof"
    assert RecommendationType.GREEN_ROOF.value == "green_roof"
    assert RecommendationType.REFLECTIVE_PAVEMENT.value == "reflective_pavement"
    assert (
        RecommendationType.WATER_BODY_RESTORATION.value == "water_body_restoration"
    )
    assert RecommendationType.URBAN_GREEN_SPACE.value == "urban_green_space"

    # Test that all values are unique
    values = [rec_type.value for rec_type in RecommendationType]
    assert len(values) == len(set(values))

    # Test that we have exactly the expected recommendation types
    expected_types = {
        "tree_plantation",
        "cool_roof",
        "green_roof",
        "reflective_pavement",
        "water_body_restoration",
        "urban_green_space",
    }
    actual_types = set(values)
    assert actual_types == expected_types


def test_severity_level_enum():
    """Test SeverityLevel enum values and uniqueness."""
    assert SeverityLevel.VERY_LOW.value == "very_low"
    assert SeverityLevel.LOW.value == "low"
    assert SeverityLevel.MODERATE.value == "moderate"
    assert SeverityLevel.HIGH.value == "high"
    assert SeverityLevel.VERY_HIGH.value == "very_high"
    assert SeverityLevel.EXTREME.value == "extreme"

    # Test that all values are unique
    values = [level.value for level in SeverityLevel]
    assert len(values) == len(set(values))

    # Test that we have exactly the expected severity levels
    expected_levels = {
        "very_low",
        "low",
        "moderate",
        "high",
        "very_high",
        "extreme",
    }
    actual_levels = set(values)
    assert actual_levels == expected_levels


def test_prediction_model_enum():
    """Test PredictionModel enum values and uniqueness."""
    assert PredictionModel.RANDOM_FOREST.value == "random_forest"
    assert PredictionModel.XGBOOST.value == "xgboost"
    assert PredictionModel.LIGHTGBM.value == "lightgbm"
    assert PredictionModel.CNN.value == "cnn"
    assert PredictionModel.LSTM.value == "lstm"
    assert PredictionModel.HYBRID.value == "hybrid"

    # Test that all values are unique
    values = [model.value for model in PredictionModel]
    assert len(values) == len(set(values))

    # Test that we have exactly the expected prediction models
    expected_models = {
        "random_forest",
        "xgboost",
        "lightgbm",
        "cnn",
        "lstm",
        "hybrid",
    }
    actual_models = set(values)
    assert actual_models == expected_models


