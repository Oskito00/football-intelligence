from datetime import datetime

from football_intelligence.cli import main as cli_main
from football_intelligence.value_backtest import (
    ValueBacktestConfig,
    ValueBacktestService,
)


def test_value_backtest_settles_chronological_full_kelly_paper_stakes():
    class FakeQueries:
        def get_value_backtest_matches(self):
            return [
                {
                    "match_id": 2,
                    "start_time": datetime(2026, 5, 30, 15, 0),
                    "home_team": "Liverpool",
                    "away_team": "Everton",
                    "home_score": 0,
                    "away_score": 1,
                    "prediction": {
                        "prediction_date": datetime(2026, 5, 30, 9, 0),
                        "prob_home_win": 0.20,
                        "prob_draw": 0.30,
                        "prob_away_win": 0.50,
                    },
                    "odds": [
                        {
                            "outcome": "Home Win",
                            "odds_value": 2.10,
                            "bookmaker_name": "Book A",
                            "retrieved_at": datetime(2026, 5, 30, 8, 0),
                        },
                        {
                            "outcome": "Away Win",
                            "odds_value": 2.50,
                            "bookmaker_name": "Book A",
                            "retrieved_at": datetime(2026, 5, 30, 8, 0),
                        },
                    ],
                },
                {
                    "match_id": 1,
                    "start_time": datetime(2026, 5, 29, 20, 0),
                    "home_team": "Arsenal",
                    "away_team": "Chelsea",
                    "home_score": 1,
                    "away_score": 1,
                    "prediction": {
                        "prediction_date": datetime(2026, 5, 29, 10, 0),
                        "prob_home_win": 0.50,
                        "prob_draw": 0.40,
                        "prob_away_win": 0.10,
                    },
                    "odds": [
                        {
                            "outcome": "Home Win",
                            "odds_value": 2.40,
                            "bookmaker_name": "Book A",
                            "retrieved_at": datetime(2026, 5, 29, 9, 0),
                        },
                        {
                            "outcome": "Home Win",
                            "odds_value": 2.60,
                            "bookmaker_name": "Book B",
                            "retrieved_at": datetime(2026, 5, 29, 9, 5),
                        },
                        {
                            "outcome": "Draw",
                            "odds_value": 3.00,
                            "bookmaker_name": "Book A",
                            "retrieved_at": datetime(2026, 5, 29, 9, 0),
                        },
                        {
                            "outcome": "Draw",
                            "odds_value": 3.20,
                            "bookmaker_name": "Book B",
                            "retrieved_at": datetime(2026, 5, 29, 9, 5),
                        },
                        {
                            "outcome": "Away Win",
                            "odds_value": 4.00,
                            "bookmaker_name": "Book A",
                            "retrieved_at": datetime(2026, 5, 29, 9, 0),
                        },
                        {
                            "outcome": "Home Win",
                            "odds_value": 3.00,
                            "bookmaker_name": "Late Book",
                            "retrieved_at": datetime(2026, 5, 29, 21, 0),
                        },
                    ],
                },
            ]

    result = ValueBacktestService(FakeQueries()).run()

    assert result.to_dict()["summary"] == {
        "starting_bankroll": 100.0,
        "final_bankroll": 136.57,
        "profit_loss": 36.57,
        "roi": 0.3657,
        "eligible_match_count": 2,
        "paper_bet_count": 3,
        "wins": 2,
        "losses": 1,
        "hit_rate": 0.6667,
        "max_drawdown": 0.0,
        "average_odds": 2.7667,
        "average_expected_value": 0.2767,
    }
    assert [
        (bet["match_id"], bet["outcome"], bet["stake"], bet["result"])
        for bet in result.to_dict()["paper_bets"]
    ] == [
        (1, "Home Win", 18.75, "loss"),
        (1, "Draw", 12.73, "win"),
        (2, "Away Win", 18.21, "win"),
    ]
    assert result.to_dict()["configuration"] == {
        "starting_bankroll": 100.0,
        "kelly_multiplier": 1.0,
        "min_expected_value": 0.0,
        "odds_mode": "best",
        "strict_pre_kickoff_odds": True,
        "strict_prediction_timing": True,
    }


def test_value_backtest_average_odds_mode_and_fractional_kelly_change_default():
    class FakeQueries:
        def get_value_backtest_matches(self):
            return [
                {
                    "match_id": 1,
                    "start_time": datetime(2026, 5, 29, 20, 0),
                    "home_team": "Arsenal",
                    "away_team": "Chelsea",
                    "home_score": 2,
                    "away_score": 0,
                    "prediction": {
                        "prediction_date": datetime(2026, 5, 29, 10, 0),
                        "prob_home_win": 0.50,
                        "prob_draw": 0.25,
                        "prob_away_win": 0.25,
                    },
                    "odds": [
                        {
                            "outcome": "Home Win",
                            "odds_value": 2.00,
                            "bookmaker_name": "Book A",
                            "retrieved_at": datetime(2026, 5, 29, 9, 0),
                        },
                        {
                            "outcome": "Home Win",
                            "odds_value": 3.00,
                            "bookmaker_name": "Book B",
                            "retrieved_at": datetime(2026, 5, 29, 9, 5),
                        },
                    ],
                }
            ]

    best_result = ValueBacktestService(FakeQueries()).run()
    average_result = ValueBacktestService(FakeQueries()).run(
        ValueBacktestConfig(odds_mode="average", kelly_multiplier=0.5)
    )

    best_bet = best_result.to_dict()["paper_bets"][0]
    average_bet = average_result.to_dict()["paper_bets"][0]
    assert best_bet["odds"] == 3.0
    assert best_bet["stake"] == 25.0
    assert average_bet["odds"] == 2.5
    assert average_bet["stake"] == 8.33
    assert average_result.to_dict()["summary"]["final_bankroll"] == 112.5


def test_value_backtest_min_expected_value_filters_paper_bets():
    class FakeQueries:
        def get_value_backtest_matches(self):
            return [
                {
                    "match_id": 1,
                    "start_time": datetime(2026, 5, 29, 20, 0),
                    "home_team": "Arsenal",
                    "away_team": "Chelsea",
                    "home_score": 1,
                    "away_score": 1,
                    "prediction": {
                        "prediction_date": datetime(2026, 5, 29, 10, 0),
                        "prob_home_win": 0.50,
                        "prob_draw": 0.35,
                        "prob_away_win": 0.15,
                    },
                    "odds": [
                        {
                            "outcome": "Home Win",
                            "odds_value": 2.20,
                            "bookmaker_name": "Book A",
                            "retrieved_at": datetime(2026, 5, 29, 9, 0),
                        },
                        {
                            "outcome": "Draw",
                            "odds_value": 4.00,
                            "bookmaker_name": "Book A",
                            "retrieved_at": datetime(2026, 5, 29, 9, 0),
                        },
                    ],
                }
            ]

    default_result = ValueBacktestService(FakeQueries()).run()
    strict_result = ValueBacktestService(FakeQueries()).run(
        ValueBacktestConfig(min_expected_value=0.2)
    )

    assert [
        (bet["outcome"], bet["expected_value"])
        for bet in default_result.to_dict()["paper_bets"]
    ] == [("Home Win", 0.1), ("Draw", 0.4)]
    assert [
        (bet["outcome"], bet["expected_value"])
        for bet in strict_result.to_dict()["paper_bets"]
    ] == [("Draw", 0.4)]


def test_value_backtest_excludes_post_kickoff_odds():
    class FakeQueries:
        def get_value_backtest_matches(self):
            return [
                {
                    "match_id": 1,
                    "start_time": datetime(2026, 5, 29, 20, 0),
                    "home_team": "Arsenal",
                    "away_team": "Chelsea",
                    "home_score": 2,
                    "away_score": 0,
                    "prediction": {
                        "prediction_date": datetime(2026, 5, 29, 10, 0),
                        "prob_home_win": 0.50,
                        "prob_draw": 0.25,
                        "prob_away_win": 0.25,
                    },
                    "odds": [
                        {
                            "outcome": "Home Win",
                            "odds_value": 2.20,
                            "bookmaker_name": "Pre Kickoff",
                            "retrieved_at": datetime(2026, 5, 29, 19, 0),
                        },
                        {
                            "outcome": "Home Win",
                            "odds_value": 4.00,
                            "bookmaker_name": "Post Kickoff",
                            "retrieved_at": datetime(2026, 5, 29, 21, 0),
                        },
                    ],
                }
            ]

    result = ValueBacktestService(FakeQueries()).run()

    assert [
        (bet["outcome"], bet["odds"], bet["bookmaker"])
        for bet in result.to_dict()["paper_bets"]
    ] == [("Home Win", 2.2, "Pre Kickoff")]


def test_value_backtest_excludes_late_predictions_unless_explicitly_allowed():
    class FakeQueries:
        def get_value_backtest_matches(self):
            return [
                {
                    "match_id": 1,
                    "start_time": datetime(2026, 5, 29, 20, 0),
                    "home_team": "Arsenal",
                    "away_team": "Chelsea",
                    "home_score": 2,
                    "away_score": 0,
                    "prediction": {
                        "prediction_date": datetime(2026, 5, 29, 21, 0),
                        "prob_home_win": 0.50,
                        "prob_draw": 0.25,
                        "prob_away_win": 0.25,
                    },
                    "odds": [
                        {
                            "outcome": "Home Win",
                            "odds_value": 2.50,
                            "bookmaker_name": "Book A",
                            "retrieved_at": datetime(2026, 5, 29, 19, 0),
                        }
                    ],
                },
                {
                    "match_id": 2,
                    "start_time": datetime(2026, 5, 30, 15, 0),
                    "home_team": "Liverpool",
                    "away_team": "Everton",
                    "home_score": 1,
                    "away_score": 0,
                    "prediction": {
                        "prediction_date": None,
                        "prob_home_win": 0.50,
                        "prob_draw": 0.25,
                        "prob_away_win": 0.25,
                    },
                    "odds": [
                        {
                            "outcome": "Home Win",
                            "odds_value": 2.50,
                            "bookmaker_name": "Book A",
                            "retrieved_at": datetime(2026, 5, 30, 10, 0),
                        }
                    ],
                },
            ]

    strict_result = ValueBacktestService(FakeQueries()).run()
    loose_result = ValueBacktestService(FakeQueries()).run(
        ValueBacktestConfig(strict_prediction_timing=False)
    )

    assert strict_result.to_dict()["paper_bets"] == []
    assert strict_result.to_dict()["skipped_matches"]["late_prediction"] == 2
    assert [
        (bet["match_id"], bet["outcome"], bet["stake"])
        for bet in loose_result.to_dict()["paper_bets"]
    ] == [(1, "Home Win", 16.67), (2, "Home Win", 20.83)]
    assert loose_result.to_dict()["configuration"]["strict_prediction_timing"] is False
    assert {
        warning["code"] for warning in loose_result.to_dict()["warnings"]
    } >= {"late_or_missing_prediction_timestamps_allowed"}


def test_value_backtest_surfaces_skipped_match_counts_for_data_quality():
    class FakeQueries:
        def get_value_backtest_matches(self):
            return [
                {
                    "match_id": 1,
                    "start_time": datetime(2026, 5, 29, 20, 0),
                    "home_team": "Arsenal",
                    "away_team": "Chelsea",
                    "home_score": None,
                    "away_score": None,
                    "prediction": {
                        "prediction_date": datetime(2026, 5, 29, 10, 0),
                        "prob_home_win": 0.50,
                        "prob_draw": 0.25,
                        "prob_away_win": 0.25,
                    },
                    "odds": [
                        {
                            "outcome": "Home Win",
                            "odds_value": 2.50,
                            "bookmaker_name": "Book A",
                            "retrieved_at": datetime(2026, 5, 29, 19, 0),
                        }
                    ],
                },
                {
                    "match_id": 2,
                    "start_time": datetime(2026, 5, 30, 15, 0),
                    "home_team": "Liverpool",
                    "away_team": "Everton",
                    "home_score": 1,
                    "away_score": 0,
                    "prediction": None,
                    "odds": [
                        {
                            "outcome": "Home Win",
                            "odds_value": 2.50,
                            "bookmaker_name": "Book A",
                            "retrieved_at": datetime(2026, 5, 30, 10, 0),
                        }
                    ],
                },
                {
                    "match_id": 3,
                    "start_time": datetime(2026, 5, 31, 15, 0),
                    "home_team": "Spurs",
                    "away_team": "Fulham",
                    "home_score": 1,
                    "away_score": 0,
                    "prediction": {
                        "prediction_date": datetime(2026, 5, 31, 10, 0),
                        "prob_home_win": 0.50,
                        "prob_draw": 0.25,
                        "prob_away_win": 0.25,
                    },
                    "odds": [],
                },
                {
                    "match_id": 4,
                    "start_time": datetime(2026, 6, 1, 15, 0),
                    "home_team": "Leeds",
                    "away_team": "Burnley",
                    "home_score": 1,
                    "away_score": 0,
                    "prediction": {
                        "prediction_date": datetime(2026, 6, 1, 16, 0),
                        "prob_home_win": 0.50,
                        "prob_draw": 0.25,
                        "prob_away_win": 0.25,
                    },
                    "odds": [
                        {
                            "outcome": "Home Win",
                            "odds_value": 2.50,
                            "bookmaker_name": "Book A",
                            "retrieved_at": datetime(2026, 6, 1, 10, 0),
                        }
                    ],
                },
            ]

    result = ValueBacktestService(FakeQueries()).run()

    assert result.to_dict()["skipped_matches"] == {
        "missing_prediction": 1,
        "missing_odds": 1,
        "late_prediction": 1,
        "missing_result": 1,
    }
    report = cli_main.render_value_backtest(result)
    assert "Skipped Matches:" in report
    assert "missing_prediction: 1" in report
    assert "missing_odds: 1" in report
    assert "late_prediction: 1" in report
    assert "missing_result: 1" in report
    assert "may not include all historical prediction revisions" in report


def test_value_backtest_cli_runs_default_report(monkeypatch, capsys):
    calls = []

    class FakeService:
        def run(self, config=None):
            calls.append(config)
            return FakeResult()

    class FakeResult:
        def to_dict(self):
            return {
                "title": "Value Backtest",
                "headline": "100.00 became 130.34",
                "configuration": {
                    "starting_bankroll": 100.0,
                    "kelly_multiplier": 1.0,
                    "min_expected_value": 0.0,
                    "odds_mode": "best",
                    "strict_pre_kickoff_odds": True,
                    "strict_prediction_timing": True,
                },
                "summary": {
                    "starting_bankroll": 100.0,
                    "final_bankroll": 130.34,
                    "profit_loss": 30.34,
                    "roi": 0.3034,
                    "eligible_match_count": 2,
                    "paper_bet_count": 3,
                    "wins": 2,
                    "losses": 1,
                    "hit_rate": 0.6667,
                    "max_drawdown": 0.2582,
                    "average_odds": 2.7667,
                    "average_expected_value": 0.2333,
                },
                "skipped_matches": {},
                "paper_bets": [],
                "warnings": [
                    {
                        "code": "retained_predictions",
                        "message": (
                            "This Value Backtest uses the retained Prediction per "
                            "Completed Match, not every historical revision."
                        ),
                    }
                ],
            }

    monkeypatch.setattr(cli_main, "get_value_backtest_service", FakeService)

    exit_code = cli_main.main(["value-backtest"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert calls == [None]
    assert "Value Backtest" in output
    assert "100.00 became 130.34" in output
    assert "Starting Bankroll: 100.00" in output
    assert "Final Bankroll: 130.34" in output
    assert "Profit/Loss: 30.34" in output
    assert "ROI: 30.3%" in output
    assert "Eligible Completed Matches: 2" in output
    assert "Paper Bets: 3" in output
    assert "Wins/Losses: 2/1" in output
    assert "Hit Rate: 66.7%" in output
    assert "Kelly Fraction: 1.0" in output
    assert "Minimum Expected Value: 0.0%" in output
    assert "Odds Mode: best" in output
    assert "Paper Stake" in output


def test_value_backtest_cli_accepts_strategy_options(monkeypatch, capsys):
    calls = []

    class FakeService:
        def run(self, config=None):
            calls.append(config)
            return FakeResult(config)

    class FakeResult:
        def __init__(self, config):
            self._config = config

        def to_dict(self):
            return {
                "title": "Value Backtest",
                "headline": "250.00 became 280.00",
                "configuration": {
                    "starting_bankroll": self._config.starting_bankroll,
                    "kelly_multiplier": self._config.kelly_multiplier,
                    "min_expected_value": self._config.min_expected_value,
                    "odds_mode": self._config.odds_mode,
                    "strict_pre_kickoff_odds": True,
                    "strict_prediction_timing": self._config.strict_prediction_timing,
                },
                "summary": {
                    "starting_bankroll": 250.0,
                    "final_bankroll": 280.0,
                    "profit_loss": 30.0,
                    "roi": 0.12,
                    "eligible_match_count": 2,
                    "paper_bet_count": 1,
                    "wins": 1,
                    "losses": 0,
                    "hit_rate": 1.0,
                    "max_drawdown": 0.0,
                    "average_odds": 3.0,
                    "average_expected_value": 0.25,
                },
                "skipped_matches": {},
                "paper_bets": [],
                "warnings": [],
            }

    monkeypatch.setattr(cli_main, "get_value_backtest_service", FakeService)

    exit_code = cli_main.main(
        [
            "value-backtest",
            "--starting-bankroll",
            "250",
            "--kelly-fraction",
            "0.25",
            "--min-expected-value",
            "0.2",
            "--odds-mode",
            "average",
            "--allow-late-predictions",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert calls == [
        ValueBacktestConfig(
            starting_bankroll=250.0,
            kelly_multiplier=0.25,
            min_expected_value=0.2,
            odds_mode="average",
            strict_prediction_timing=False,
        )
    ]
    assert "Starting Bankroll: 250.00" in output
    assert "Kelly Fraction: 0.25" in output
    assert "Minimum Expected Value: 20.0%" in output
    assert "Odds Mode: average" in output
    assert "Prediction Timing: late or missing timestamps allowed" in output
    assert "0.25x Kelly" in output
