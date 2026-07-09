import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestMLTrainingRoutes:
    def test_list_endpoint(self):
        r = client.get("/api/v1/ml/training/")
        assert r.status_code == 200
        data = r.json()
        assert "endpoints" in data

    def test_train_endpoint(self):
        r = client.post("/api/v1/ml/training/train", json={
            "X": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0], [9.0, 10.0],
                   [2.0, 3.0], [4.0, 5.0], [6.0, 7.0], [8.0, 9.0], [10.0, 11.0]],
            "y": [10.0, 20.0, 30.0, 40.0, 50.0, 15.0, 25.0, 35.0, 45.0, 55.0],
            "model_type": "random_forest",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "success"
        assert data["model_type"] == "random_forest"

    def test_train_invalid_model(self):
        r = client.post("/api/v1/ml/training/train", json={
            "X": [[1.0]],
            "y": [1.0],
            "model_type": "nonexistent_model",
        })
        assert r.status_code == 400

    def test_cross_validate(self):
        r = client.post("/api/v1/ml/training/cross-validate", json={
            "X": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
            "y": [10.0, 20.0, 30.0],
            "model_type": "random_forest",
            "strategy": "kfold",
            "n_folds": 3,
            "task": "regression",
        })
        assert r.status_code == 200

    def test_hyperparameter_optimization(self):
        r = client.post("/api/v1/ml/training/hyperparameter-optimization", json={
            "X": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0], [9.0, 10.0]],
            "y": [10.0, 20.0, 30.0, 40.0, 50.0],
            "model_type": "random_forest",
            "method": "grid",
            "n_trials": 1,
            "task": "regression",
        })
        assert r.status_code == 200


class TestMLInferenceRoutes:
    def test_list_endpoint(self):
        r = client.get("/api/v1/ml/inference/")
        assert r.status_code == 200

    def test_predict(self):
        r = client.post("/api/v1/ml/inference/predict", json={
            "X": [[1.0, 2.0], [3.0, 4.0]],
        })
        assert r.status_code == 200
        data = r.json()
        assert "predictions" in data

    def test_forecast(self):
        r = client.post("/api/v1/ml/inference/forecast", json={
            "X": [[1.0, 2.0], [3.0, 4.0]],
            "delta_years": 10,
        })
        assert r.status_code == 200


class TestRecommendationRoutes:
    def test_list_endpoint(self):
        r = client.get("/api/v1/recommendations/")
        assert r.status_code == 200

    def test_generate(self):
        r = client.post("/api/v1/recommendations/generate", json={
            "hotspot": {
                "id": "UHI-0001",
                "severity": "high",
                "dominant_landcover": "Builtup",
                "mean_ndvi": 0.05,
                "mean_ndbi": 0.35,
                "mean_ndwi": -0.15,
                "vegetation_fraction": 0.1,
                "builtup_fraction": 0.7,
                "area_sq_km": 0.05,
                "mean_temperature_c": 42.3,
                "max_temperature_c": 47.1,
                "min_temperature_c": 38.2,
                "pixel_count": 150,
                "confidence": 0.85,
            },
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert len(data["recommendations"]) > 0

    def test_generate_batch(self):
        r = client.post("/api/v1/recommendations/generate-batch", json={
            "hotspots": [
                {
                    "id": "UHI-0001",
                    "severity": "high",
                    "dominant_landcover": "Builtup",
                    "mean_ndvi": 0.05,
                    "mean_ndbi": 0.35,
                    "mean_ndwi": -0.15,
                    "vegetation_fraction": 0.1,
                    "builtup_fraction": 0.7,
                    "area_sq_km": 0.05,
                    "mean_temperature_c": 42.3,
                },
            ],
        })
        assert r.status_code == 200

    def test_generate_no_match(self):
        r = client.post("/api/v1/recommendations/generate", json={
            "hotspot": {
                "id": "UHI-0000",
                "severity": "very_low",
                "dominant_landcover": "water",
                "mean_ndvi": -0.5,
                "vegetation_fraction": 0.0,
                "builtup_fraction": 0.0,
                "area_sq_km": 0.001,
            },
        })
        assert r.status_code in (200, 404)


class TestScenarioRoutes:
    def test_list_templates(self):
        r = client.get("/api/v1/scenarios/templates")
        assert r.status_code == 200
        data = r.json()
        assert len(data["templates"]) == 7

    def test_get_template(self):
        r = client.get("/api/v1/scenarios/templates/tree_plantation")
        assert r.status_code == 200
        assert r.json()["template"]["name"] == "tree_plantation"

    def test_get_template_not_found(self):
        r = client.get("/api/v1/scenarios/templates/nonexistent")
        assert r.status_code == 404

    def test_run_scenario(self):
        r = client.post("/api/v1/scenarios/run", json={
            "scenario_name": "tree_plantation",
            "X": [[35.0, 0.1, 0.2, 0.3, 0.1, 0.6]],
            "y": [35.0],
            "feature_names": ["lst", "ndvi", "albedo", "ndbi", "vegetation_fraction", "builtup_fraction"],
            "area_ha": 10.0,
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["result"]["scenario_name"] == "tree_plantation"

    def test_compare_scenarios(self):
        r = client.post("/api/v1/scenarios/compare", json={
            "scenario_names": ["tree_plantation", "cool_roof"],
            "X": [[35.0, 0.1, 0.2, 0.3, 0.1, 0.6]],
            "y": [35.0],
            "feature_names": ["lst", "ndvi", "albedo", "ndbi", "vegetation_fraction", "builtup_fraction"],
            "area_ha": 10.0,
        })
        assert r.status_code == 200, r.text
        assert "comparison" in r.json()

    def test_run_all_scenarios(self):
        r = client.post("/api/v1/scenarios/run-all", json={
            "X": [[35.0, 0.1, 0.2, 0.3, 0.1, 0.6]],
            "y": [35.0],
            "feature_names": ["lst", "ndvi", "albedo", "ndbi", "vegetation_fraction", "builtup_fraction"],
            "area_ha": 1.0,
        })
        assert r.status_code == 200, r.text
        assert "comparison" in r.json()


class TestXaiRoutes:
    def test_explain(self):
        r = client.post("/api/v1/ml/inference/explain", json={
            "X": [[1.0, 2.0], [3.0, 4.0]],
            "y": [10.0, 20.0],
            "method": "permutation",
        })
        assert r.status_code == 200
