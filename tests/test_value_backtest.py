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


def test_value_backtest_average_odds_mode_and_fractional_kelly():
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

    result = ValueBacktestService(FakeQueries()).run(
        ValueBacktestConfig(odds_mode="average", kelly_multiplier=0.5)
    )

    bet = result.to_dict()["paper_bets"][0]
    assert bet["odds"] == 2.5
    assert bet["stake"] == 8.33
    assert result.to_dict()["summary"]["final_bankroll"] == 112.5


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
    assert "Odds Mode: best" in output
    assert "Paper Stake" in output
