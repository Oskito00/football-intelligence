import subprocess
import sys
from pathlib import Path

import pandas as pd
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
GENERATED_ARTIFACT_IGNORE_RULES = (
    "models/*",
    "!models/.gitkeep",
    "!models/README.md",
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
    assert tracked_model_files == ["models/.gitkeep", "models/README.md"]

    with (config_dir / "result_model_early.yaml").open() as config_file:
        config = yaml.safe_load(config_file)

    assert config["output"]["model_dir"] == "models"
    assert "ml_pipeline" not in str(config)


def test_model_training_uses_configured_local_model_artifact_home():
    from football_intelligence.predictions.training import _model_artifact_dir

    assert _model_artifact_dir({"output": {"model_dir": "models"}}) == "models"
    assert _model_artifact_dir({}) == "models"


def test_generated_model_and_data_outputs_are_ignored_by_git():
    assert_ignore_rules(
        PROJECT_ROOT / ".gitignore",
        GENERATED_ARTIFACT_IGNORE_RULES,
    )


def test_generated_model_and_data_outputs_are_ignored_by_docker_context():
    assert_ignore_rules(
        PROJECT_ROOT / ".dockerignore",
        GENERATED_ARTIFACT_IGNORE_RULES,
    )


def assert_ignore_rules(ignore_file: Path, required_ignore_rules: tuple[str, ...]) -> None:
    ignored_paths = ignore_file.read_text(encoding="utf-8").splitlines()

    for rule in required_ignore_rules:
        assert rule in ignored_paths


def test_missing_model_artifact_error_explains_local_model_training_path(tmp_path):
    from football_intelligence.predictions.model_io import ModelIO

    model_io = ModelIO(tmp_path / "models")

    with pytest.raises(FileNotFoundError) as error:
        model_io.load_model("result_model_early")

    message = str(error.value)
    assert "models/result_model_early_latest" in message
    assert "Model Training" in message
    assert "python -m football_intelligence.cli model-training" in message


def test_prediction_inference_entrypoint_assumes_predictions_table_exists(monkeypatch):
    from football_intelligence.predictions import inference_entrypoint

    connection = object()
    original_argv = sys.argv[:]

    monkeypatch.setattr(
        inference_entrypoint.config_manager,
        "load_config",
        lambda config_name: {"model": {"name": "result_model_early"}},
    )
    monkeypatch.setattr(
        inference_entrypoint,
        "create_match_result_predictions_table",
        lambda conn: (_ for _ in ()).throw(
            AssertionError("Prediction inference must not create schema")
        ),
        raising=False,
    )
    monkeypatch.setattr(
        inference_entrypoint,
        "get_inferrer",
        lambda model_name: (
            lambda *args, **kwargs: {"success": True, "num_predictions": 0}
        ),
    )

    try:
        sys.argv = ["prediction-inference", "result_model_early"]
        inference_entrypoint.main(connection)
    finally:
        sys.argv = original_argv


def test_saving_predictions_assumes_database_setup_prepared_destination(monkeypatch):
    from football_intelligence.database import football

    calls = []
    predictions = pd.DataFrame(
        [
            {
                "match_id": 1,
                "predicted_result": 2,
                "start_time": "2026-05-29T12:00:00",
                "home_team_name": "Home",
                "away_team_name": "Away",
                "prob_home_win": 0.5,
                "prob_draw": 0.25,
                "prob_away_win": 0.25,
                "prediction_timestamp": "2026-05-29T12:01:00",
            }
        ]
    )

    monkeypatch.setattr(
        football,
        "create_match_result_predictions_table",
        lambda conn: (_ for _ in ()).throw(
            AssertionError("Prediction Refresh must not create schema")
        ),
    )
    monkeypatch.setattr(
        football,
        "upsert_records",
        lambda **kwargs: calls.append(kwargs),
    )

    assert football.save_predictions_to_db(object(), predictions) is True
    assert calls[0]["table_name"] == "match_result_predictions"


def test_prediction_inference_missing_model_is_reported_before_feature_loading(monkeypatch):
    from football_intelligence.predictions import inference

    class UnexpectedFeatureLoader:
        def __init__(self, *args, **kwargs):
            raise AssertionError("Missing model should be handled before database reads")

    monkeypatch.setattr(inference, "ResultFeatureLoader", UnexpectedFeatureLoader)
    monkeypatch.setattr(
        inference.model_io,
        "load_model",
        lambda model_name, version=None: (_ for _ in ()).throw(
            FileNotFoundError(
                "No latest model artifact found for result_model_early. Run Model Training."
            )
        ),
    )

    result = inference.infer_result_model(
        object(),
        {"model": {"name": "result_model_early"}, "data": {}},
    )

    assert result["success"] is False
    assert "Model Training" in result["error"]


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
