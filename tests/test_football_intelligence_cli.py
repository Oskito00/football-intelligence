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

    def fake_run_prediction_refresh_from_args(args):
        calls.append(
            {
                "command": "prediction-refresh",
                "model_config": args.model_config,
                "skip_odds": args.skip_odds,
                "only": args.only,
            }
        )
        return 0

    monkeypatch.setattr(cli_main, "run_model_training", fail_model_training)
    monkeypatch.setattr(
        cli_main,
        "run_prediction_refresh_from_args",
        fake_run_prediction_refresh_from_args,
    )

    exit_code = cli_main.main(
        [
            "prediction-refresh",
            "--model-config",
            "result_model_late",
            "--only",
            "features",
        ]
    )

    assert exit_code == 0
    assert calls == [
        {
            "command": "prediction-refresh",
            "model_config": "result_model_late",
            "skip_odds": False,
            "only": ["features"],
        }
    ]


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


def test_status_command_renders_football_data_status(monkeypatch, capsys):
    class FakeStatus:
        def to_dict(self):
            return {
                "title": "Football Data Status",
                "latest_completed_match": {
                    "home_team": "Arsenal",
                    "away_team": "Chelsea",
                    "competition": "Premier League",
                    "start_time": "2026-05-27T20:00:00",
                    "score": "2-1",
                },
                "unprocessed_completed_matches": 2,
                "latest_elo_history_date": "2026-05-26T22:00:00",
                "future_feature_set_count": 7,
                "prediction_count_next_7_days": 6,
                "odds_freshness": {
                    "latest_retrieved_at": "2026-05-28T12:00:00",
                    "matches_with_odds_next_7_days": 5,
                },
                "top_premier_league_elo_teams": [
                    {"team_name": "Arsenal", "elo": 1875},
                    {"team_name": "Liverpool", "elo": 1840},
                ],
                "warnings": [
                    {
                        "message": (
                            "2 Completed Matches have not been incorporated into "
                            "the Historical Feature Set."
                        )
                    }
                ],
            }

    monkeypatch.setattr(cli_main, "get_football_data_status", lambda: FakeStatus())

    exit_code = cli_main.main(["status"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Football Data Status" in output
    assert "Latest Completed Match: Arsenal 2-1 Chelsea" in output
    assert "Unprocessed Completed Matches: 2" in output
    assert "Future Feature Set Count: 7" in output
    assert "Next 7 Days Prediction Count: 6" in output
    assert "Odds Freshness: latest retrieved 2026-05-28T12:00:00" in output
    assert "1. Arsenal - 1875" in output
    assert "Warnings:" in output
