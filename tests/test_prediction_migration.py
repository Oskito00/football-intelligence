import sys
from pathlib import Path

import yaml

from football_intelligence.predictions import (
    ResultFeatureLoader,
    infer_result_model,
    run_model_training,
    run_prediction_inference,
    train_result_model,
)
from tests.import_audit import find_imports_matching, is_module_or_child


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_prediction_namespace_owns_inference_training_and_feature_loading():
    assert run_prediction_inference.__module__.startswith("football_intelligence.predictions")
    assert infer_result_model.__module__.startswith("football_intelligence.predictions")
    assert run_model_training.__module__.startswith("football_intelligence.predictions")
    assert train_result_model.__module__.startswith("football_intelligence.predictions")
    assert ResultFeatureLoader.__module__.startswith("football_intelligence.predictions")


def test_formation_inference_validates_future_feature_table():
    loader = ResultFeatureLoader(
        object(),
        {"feature_requirements": {"formations": True}},
        mode="inference",
    )

    required_tables = loader.get_required_tables()

    assert "formation_future" in required_tables
    assert "formation_history" not in required_tables


def test_prediction_refresh_runs_product_inference_entrypoint(monkeypatch):
    from football_intelligence.predictions import refresh
    from football_intelligence.predictions import inference_entrypoint

    calls = []
    connection = object()
    original_argv = sys.argv[:]

    def fake_main(conn):
        calls.append((conn, tuple(sys.argv)))

    monkeypatch.setattr(inference_entrypoint, "main", fake_main)

    refresh.run_result_model_inference(connection, "result_model_late")

    assert calls == [
        (
            connection,
            ("prediction-inference", "result_model_late", "--mode", "inference"),
        )
    ]
    assert sys.argv == original_argv


def test_prediction_configs_and_saved_models_use_product_paths():
    config_dir = PROJECT_ROOT / "football_intelligence" / "predictions" / "configs"
    model_dir = PROJECT_ROOT / "models"

    assert (config_dir / "result_model_early.yaml").exists()
    assert (model_dir / "result_model_early_20250617_160510" / "model.pkl").exists()
    assert (model_dir / "result_model_early_latest").exists()

    with (config_dir / "result_model_early.yaml").open() as config_file:
        config = yaml.safe_load(config_file)

    assert config["output"]["model_dir"] == "models"
    assert "ml_pipeline" not in str(config)


def test_active_prediction_runtime_no_longer_imports_ml_pipeline():
    active_roots = (
        PROJECT_ROOT / "football_intelligence",
        PROJECT_ROOT / "tests",
    )

    offenders = find_imports_matching(
        active_roots,
        _is_retired_ml_pipeline_module,
        PROJECT_ROOT,
    )

    assert offenders == []


def test_migrated_old_prediction_pipeline_files_are_deleted():
    assert not (PROJECT_ROOT / "ml_pipeline").exists()


def _is_retired_ml_pipeline_module(module_name: str) -> bool:
    return is_module_or_child(module_name, "ml_pipeline")
