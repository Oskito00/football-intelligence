import logging

from football_intelligence.predictions.refresh import (
    PredictionRefreshStep,
    run_prediction_refresh,
)


def test_prediction_refresh_orchestrates_lifecycle_without_model_training():
    calls = []
    connection = object()

    def make_step(name):
        return PredictionRefreshStep(name, lambda: calls.append(name))

    def step_factory(received_connection, model_config, include_odds):
        assert received_connection is connection
        assert model_config == "result_model_late"
        assert include_odds is True
        return [
            make_step("refresh league catalogue"),
            make_step("refresh current match data"),
            make_step("build Historical Feature Set"),
            make_step("build Future Feature Set"),
            make_step("run Prediction inference"),
            make_step("refresh odds"),
        ]

    result = run_prediction_refresh(
        connection=connection,
        model_config="result_model_late",
        step_factory=step_factory,
        logger=logging.getLogger("test_prediction_refresh"),
    )

    assert calls == [
        "refresh league catalogue",
        "refresh current match data",
        "build Historical Feature Set",
        "build Future Feature Set",
        "run Prediction inference",
        "refresh odds",
    ]
    assert result.steps_run == tuple(calls)


def test_prediction_refresh_cli_invokes_application_workflow(monkeypatch, capsys):
    calls = []

    def fake_run_prediction_refresh(*, model_config, include_odds):
        calls.append((model_config, include_odds))
        return type(
            "Result",
            (),
            {
                "steps_run": ("refresh current match data", "run Prediction inference"),
                "steps_failed": (),
            },
        )()

    from football_intelligence.cli import prediction_refresh

    monkeypatch.setattr(
        prediction_refresh,
        "run_prediction_refresh",
        fake_run_prediction_refresh,
    )

    exit_code = prediction_refresh.main(
        ["--model-config", "result_model_late", "--skip-odds"]
    )

    assert exit_code == 0
    assert calls == [("result_model_late", False)]
    assert "Prediction Refresh completed: 2 steps run" in capsys.readouterr().out


def test_scheduler_path_delegates_to_prediction_refresh(monkeypatch):
    from scheduler import scheduler

    calls = []

    def fake_run_prediction_refresh(*, logger):
        calls.append(logger)
        return "refresh-result"

    monkeypatch.setattr(scheduler, "run_prediction_refresh", fake_run_prediction_refresh)

    assert scheduler.run_all_scripts() == "refresh-result"
    assert calls == [scheduler.logger]
