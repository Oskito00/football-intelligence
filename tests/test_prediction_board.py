from datetime import datetime

from fastapi.testclient import TestClient

from football_intelligence.api import create_app
from football_intelligence.board import PredictionBoardService
from football_intelligence.cli import main as cli_main


class FakeBoardQueries:
    def __init__(self):
        self.calls = []

    def get_upcoming_matches_between(self, *, starts_at, ends_at):
        self.calls.append(("matches", starts_at, ends_at))
        return [
            {
                "match_id": 42,
                "start_time": "2026-05-29T20:00:00",
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "competition": "Premier League",
                "country": "England",
                "competition_id": 39,
            },
            {
                "match_id": 43,
                "start_time": "2026-05-29T21:00:00",
                "home_team": "Liverpool",
                "away_team": "Everton",
                "competition": "Premier League",
                "country": "England",
                "competition_id": 39,
            },
        ]

    def get_multiple_match_predictions(self, match_ids):
        self.calls.append(("predictions", tuple(match_ids)))
        return {
            42: {
                "match_id": 42,
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "predicted_result": "Home Win",
                "confidence": 0.61,
                "prob_home_win": 0.61,
                "prob_draw": 0.21,
                "prob_away_win": 0.18,
                "model_type": "result_model",
                "prediction_date": datetime(2026, 5, 29, 10, 0),
            }
        }

    def get_odds_freshness_for_matches(self, match_ids):
        self.calls.append(("odds_freshness", tuple(match_ids)))
        return {
            42: {
                "latest_retrieved_at": datetime(2026, 5, 29, 9, 30),
                "latest_api_last_updated": datetime(2026, 5, 29, 9, 20),
            }
        }

    def analyze_matches_for_value(self, match_ids):
        self.calls.append(("value", tuple(match_ids)))
        return {
            "all_value_bets": [
                {
                    "match_id": 42,
                    "outcome": "Home Win",
                    "model_probability": 0.61,
                    "odds_value": 2.1,
                    "implied_probability": 0.4761904762,
                    "expected_value": 0.281,
                    "bookmaker_name": "Bet365",
                    "recommended_bet_percentage": 12.4,
                }
            ]
        }


def test_prediction_board_service_builds_today_window_and_match_cards():
    queries = FakeBoardQueries()
    service = PredictionBoardService(
        queries,
        now_factory=lambda: datetime(2026, 5, 29, 12, 0),
    )

    board = service.today().to_dict()

    assert board["title"] == "Prediction Board"
    assert board["date"] == "2026-05-29"
    assert board["window"] == {
        "starts_at": "2026-05-29T12:00:00",
        "ends_at": "2026-05-30T00:00:00",
        "timezone": "local",
    }
    assert board["summary"] == {
        "upcoming_match_count": 2,
        "matches_with_predictions": 1,
        "matches_with_odds": 1,
        "market_value_signal_count": 1,
    }
    assert board["matches"][0]["prediction"]["predicted_result"] == "Home Win"
    assert board["matches"][0]["odds_freshness"] == {
        "has_odds": True,
        "latest_retrieved_at": "2026-05-29T09:30:00",
        "latest_api_last_updated": "2026-05-29T09:20:00",
    }
    assert board["matches"][0]["market_value_signals"] == [
        {
            "outcome": "Home Win",
            "model_probability": 0.61,
            "best_odds": 2.1,
            "implied_probability": 0.4761904762,
            "edge": 0.281,
            "bookmaker": "Bet365",
            "paper_stake_percentage": 12.4,
        }
    ]
    assert board["matches"][1]["prediction"] is None
    assert board["matches"][1]["odds_freshness"]["has_odds"] is False
    assert {warning["code"] for warning in board["warnings"]} == {
        "missing_predictions",
        "missing_odds",
    }
    assert queries.calls[0] == (
        "matches",
        datetime(2026, 5, 29, 12, 0),
        datetime(2026, 5, 30, 0, 0),
    )


def test_prediction_board_service_returns_empty_board_for_no_remaining_matches():
    class EmptyBoardQueries(FakeBoardQueries):
        def get_upcoming_matches_between(self, *, starts_at, ends_at):
            return []

        def get_multiple_match_predictions(self, match_ids):
            raise AssertionError("No prediction lookup needed when board is empty")

    service = PredictionBoardService(
        EmptyBoardQueries(),
        now_factory=lambda: datetime(2026, 5, 29, 23, 0),
    )

    board = service.today().to_dict()

    assert board["summary"]["upcoming_match_count"] == 0
    assert board["matches"] == []
    assert board["empty_state"] == (
        "No remaining Upcoming Matches are scheduled for today's local-date window."
    )


def test_board_today_cli_renders_prediction_board(monkeypatch, capsys):
    class FakeBoard:
        def to_dict(self):
            return {
                "title": "Prediction Board",
                "date": "2026-05-29",
                "window": {
                    "starts_at": "2026-05-29T12:00:00",
                    "ends_at": "2026-05-30T00:00:00",
                    "timezone": "local",
                },
                "summary": {
                    "upcoming_match_count": 1,
                    "matches_with_predictions": 1,
                    "matches_with_odds": 0,
                    "market_value_signal_count": 0,
                },
                "matches": [
                    {
                        "match_id": 42,
                        "start_time": "2026-05-29T20:00:00",
                        "home_team": "Arsenal",
                        "away_team": "Chelsea",
                        "competition": "Premier League",
                        "country": "England",
                        "prediction": {
                            "predicted_result": "Home Win",
                            "confidence": 0.61,
                            "probabilities": {
                                "home_win": 0.61,
                                "draw": 0.21,
                                "away_win": 0.18,
                            },
                        },
                        "odds_freshness": {
                            "has_odds": False,
                            "latest_retrieved_at": None,
                            "latest_api_last_updated": None,
                        },
                        "market_value_signals": [],
                    }
                ],
                "warnings": [],
                "empty_state": None,
            }

    monkeypatch.setattr(cli_main, "get_today_prediction_board", lambda: FakeBoard())

    exit_code = cli_main.main(["board", "today"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Prediction Board - 2026-05-29" in output
    assert "Arsenal vs Chelsea" in output
    assert "Prediction: Home Win (61.0%)" in output
    assert "Odds Freshness: missing" in output


def test_board_today_api_returns_deterministic_prediction_board_json():
    class FakeBoard:
        def to_dict(self):
            return {
                "title": "Prediction Board",
                "date": "2026-05-29",
                "window": {
                    "starts_at": "2026-05-29T12:00:00",
                    "ends_at": "2026-05-30T00:00:00",
                    "timezone": "local",
                },
                "summary": {
                    "upcoming_match_count": 0,
                    "matches_with_predictions": 0,
                    "matches_with_odds": 0,
                    "market_value_signal_count": 0,
                },
                "matches": [],
                "warnings": [],
                "empty_state": (
                    "No remaining Upcoming Matches are scheduled for today's "
                    "local-date window."
                ),
            }

    class FakeBoardService:
        def today(self):
            return FakeBoard()

    client = TestClient(create_app(board_service=FakeBoardService()))

    response = client.get("/api/board/today")

    assert response.status_code == 200
    assert response.json() == FakeBoard().to_dict()
