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


def test_prediction_refresh_builds_steps_from_product_ingestion(monkeypatch):
    from football_intelligence.predictions import refresh

    calls = []
    connection = object()

    class FakeSourceDataIngestion:
        def match_data_steps(self, conn):
            assert conn is connection
            return [
                refresh.PredictionRefreshStep(
                    "refresh league catalogue",
                    lambda: calls.append("league catalogue"),
                ),
                refresh.PredictionRefreshStep(
                    "refresh current match data",
                    lambda: calls.append("current match data"),
                ),
            ]

        def odds_step(self, conn):
            assert conn is connection
            return refresh.PredictionRefreshStep(
                "refresh odds",
                lambda: calls.append("odds"),
            )

    monkeypatch.setattr(refresh, "SourceDataIngestion", FakeSourceDataIngestion)
    monkeypatch.setattr(
        refresh,
        "build_historical_feature_set",
        lambda conn: calls.append("Historical Feature Set"),
    )
    monkeypatch.setattr(
        refresh,
        "build_future_feature_set",
        lambda conn: calls.append("Future Feature Set"),
    )
    monkeypatch.setattr(
        refresh,
        "run_result_model_inference",
        lambda conn, model_config: calls.append(("Prediction inference", model_config)),
    )

    steps = refresh.build_prediction_refresh_steps(
        connection,
        model_config="result_model_late",
        include_odds=True,
    )

    assert [step.name for step in steps] == [
        "refresh league catalogue",
        "refresh current match data",
        "build Historical Feature Set",
        "build Future Feature Set",
        "run Prediction inference",
        "refresh odds",
    ]

    for step in steps:
        step.action()

    assert calls == [
        "league catalogue",
        "current match data",
        "Historical Feature Set",
        "Future Feature Set",
        ("Prediction inference", "result_model_late"),
        "odds",
    ]


def test_prediction_refresh_cli_invokes_application_workflow(monkeypatch, capsys):
    calls = []

    def fake_run_prediction_refresh(*, model_config, include_odds, selectors):
        calls.append((model_config, include_odds, selectors))
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
    assert calls == [("result_model_late", False, ())]
    assert "Prediction Refresh completed: 2 steps run" in capsys.readouterr().out


def test_prediction_refresh_cli_accepts_refresh_selectors(monkeypatch):
    calls = []

    def fake_run_prediction_refresh(*, model_config, include_odds, selectors):
        calls.append((model_config, include_odds, selectors))
        return type(
            "Result",
            (),
            {
                "steps_run": ("build Historical Feature Set",),
                "steps_failed": (),
            },
        )()

    from football_intelligence.cli import prediction_refresh

    monkeypatch.setattr(
        prediction_refresh,
        "run_prediction_refresh",
        fake_run_prediction_refresh,
    )

    exit_code = prediction_refresh.main(["--only", "historical-feature-set"])

    assert exit_code == 0
    assert calls == [("result_model_early", True, ("historical-feature-set",))]


def test_prediction_refresh_filters_steps_by_selector():
    calls = []
    connection = object()

    def make_step(name):
        return PredictionRefreshStep(name, lambda: calls.append(name))

    def step_factory(received_connection, model_config, include_odds):
        assert received_connection is connection
        assert model_config == "result_model_early"
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
        selectors=("source-data-ingestion",),
        step_factory=step_factory,
        logger=logging.getLogger("test_prediction_refresh"),
    )

    assert calls == [
        "refresh league catalogue",
        "refresh current match data",
    ]
    assert result.steps_run == tuple(calls)
