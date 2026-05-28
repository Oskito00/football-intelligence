from football_intelligence.cli import main as cli_main


def test_model_training_command_runs_current_result_model_with_arguments(monkeypatch):
    calls = []

    def fake_run_model_training(config_name, *, dry_run=False, limit=None):
        calls.append(
            {
                "config_name": config_name,
                "dry_run": dry_run,
                "limit": limit,
            }
        )
        return {"success": True, "model_path": "models/result_model"}

    monkeypatch.setattr(cli_main, "run_model_training", fake_run_model_training)

    exit_code = cli_main.main(["model-training", "--dry-run", "--limit", "12"])

    assert exit_code == 0
    assert calls == [
        {
            "config_name": "result_model_early",
            "dry_run": True,
            "limit": 12,
        }
    ]


def test_prediction_refresh_command_does_not_invoke_model_training(monkeypatch):
    calls = []

    def fail_model_training(*args, **kwargs):
        raise AssertionError("Prediction Refresh must not run Model Training")

    def fake_run_prediction_refresh():
        calls.append("prediction-refresh")

    monkeypatch.setattr(cli_main, "run_model_training", fail_model_training)
    monkeypatch.setattr(cli_main, "run_prediction_refresh", fake_run_prediction_refresh)

    exit_code = cli_main.main(["prediction-refresh"])

    assert exit_code == 0
    assert calls == ["prediction-refresh"]


def test_model_training_command_returns_failure_exit_code(monkeypatch):
    calls = []

    def fake_run_model_training(config_name, *, dry_run=False, limit=None):
        calls.append(
            {
                "config_name": config_name,
                "dry_run": dry_run,
                "limit": limit,
            }
        )
        return {"success": False, "error": "training failed"}

    monkeypatch.setattr(cli_main, "run_model_training", fake_run_model_training)

    exit_code = cli_main.main(["model-training", "result_model_late"])

    assert exit_code == 1
    assert calls == [
        {
            "config_name": "result_model_late",
            "dry_run": False,
            "limit": None,
        }
    ]
