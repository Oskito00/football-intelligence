import sys
import subprocess
from pathlib import Path

import pytest
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
    assert (model_dir / ".gitkeep").exists()

    tracked_model_files = subprocess.run(
        ["git", "ls-files", "models"],
        cwd=PROJECT_ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.splitlines()
    assert tracked_model_files == ["models/.gitkeep"]

    with (config_dir / "result_model_early.yaml").open() as config_file:
        config = yaml.safe_load(config_file)

    assert config["output"]["model_dir"] == "models"
    assert "ml_pipeline" not in str(config)


def test_generated_model_and_data_outputs_are_ignored():
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")

    required_ignore_rules = (
        "models/*",
        "!models/.gitkeep",
        "*.pkl",
        "*.joblib",
        "*.sqlite",
        "*.sqlite3",
        "*.db",
        "*.dump",
        "*.sql",
        "*.sql.gz",
        "*.csv",
        "*.parquet",
        "data/",
    )

    for rule in required_ignore_rules:
        assert rule in gitignore


def test_missing_model_artifact_error_explains_local_model_training_path(tmp_path):
    from football_intelligence.predictions.model_io import ModelIO

    model_io = ModelIO(tmp_path / "models")

    with pytest.raises(FileNotFoundError) as error:
        model_io.load_model("result_model_early")

    message = str(error.value)
    assert "models/result_model_early_latest" in message
    assert "Model Training" in message
    assert "python -m football_intelligence.cli model-training" in message


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
