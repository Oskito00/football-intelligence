from datetime import datetime

import pytest

from football_intelligence.database.football import (
    FootballQueryError,
    PostgresReadOnlyRunner,
    ReadOnlyFootballQueries,
)


class FakeReadOnlyRunner:
    def __init__(self, one=None, many=None):
        self.one = one
        self.many = many or []
        self.calls = []

    def fetch_one(self, query, params=()):
        self.calls.append(("one", query, tuple(params)))
        return self.one

    def fetch_all(self, query, params=()):
        self.calls.append(("all", query, tuple(params)))
        if self.many and isinstance(self.many[0], list):
            return self.many.pop(0)
        return self.many


class FailingReadOnlyRunner:
    def fetch_one(self, query, params=()):
        raise RuntimeError("database offline")

    def fetch_all(self, query, params=()):
        raise RuntimeError("database offline")


def test_match_prediction_maps_latest_prediction_shape():
    queries = ReadOnlyFootballQueries(
        FakeReadOnlyRunner(
            one={
                "match_id": 42,
                "predicted_result": 2,
                "home_team_name": "Arsenal",
                "away_team_name": "Chelsea",
                "prob_home_win": 0.61,
                "prob_draw": 0.21,
                "prob_away_win": 0.18,
                "model_type": "result_model",
                "prediction_timestamp": datetime(2026, 5, 27, 12, 0),
            }
        )
    )

    prediction = queries.get_match_prediction(42)

    assert prediction == {
        "match_id": 42,
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "predicted_result": "Home Win",
        "confidence": 0.61,
        "prob_home_win": 0.61,
        "prob_draw": 0.21,
        "prob_away_win": 0.18,
        "model_type": "result_model",
        "prediction_date": datetime(2026, 5, 27, 12, 0),
    }


def test_match_prediction_returns_none_when_missing():
    queries = ReadOnlyFootballQueries(FakeReadOnlyRunner(one=None))

    assert queries.get_match_prediction(404) is None


def test_prediction_lookup_wraps_backend_errors():
    queries = ReadOnlyFootballQueries(FailingReadOnlyRunner())

    with pytest.raises(FootballQueryError, match="Error getting prediction"):
        queries.get_match_prediction(42)


def test_upcoming_matches_maps_stable_match_shape():
    start_time = datetime(2026, 6, 1, 20, 0)
    queries = ReadOnlyFootballQueries(
        FakeReadOnlyRunner(
            many=[
                {
                    "match_id": 12,
                    "start_time": start_time,
                    "home_team_name": "Liverpool",
                    "away_team_name": "Everton",
                    "competition_name": "Premier League",
                    "competition_country": "England",
                    "competition_id": 39,
                }
            ]
        )
    )

    matches = queries.get_upcoming_matches(
        days_ahead=5,
        competition_ids=[39],
        country="England",
        limit=3,
    )

    assert matches == [
        {
            "match_id": 12,
            "start_time": "2026-06-01T20:00:00",
            "home_team": "Liverpool",
            "away_team": "Everton",
            "competition": "Premier League",
            "country": "England",
            "competition_id": 39,
        }
    ]


def test_recent_form_returns_no_result_shape():
    queries = ReadOnlyFootballQueries(FakeReadOnlyRunner(many=[]))

    assert queries.get_recent_form(team_id=7) == {
        "success": False,
        "error": "No matches found for team ID 7",
        "data": None,
    }


def test_recent_form_summarizes_completed_matches():
    queries = ReadOnlyFootballQueries(
        FakeReadOnlyRunner(
            many=[
                {
                    "match_id": 1,
                    "start_time": datetime(2026, 5, 1, 15, 0),
                    "home_team_name": "Arsenal",
                    "away_team_name": "Chelsea",
                    "home_score": 2,
                    "away_score": 0,
                    "competition_name": "Premier League",
                    "competition_id": 39,
                    "team_side": "home",
                },
                {
                    "match_id": 2,
                    "start_time": datetime(2026, 4, 27, 15, 0),
                    "home_team_name": "Liverpool",
                    "away_team_name": "Arsenal",
                    "home_score": 1,
                    "away_score": 1,
                    "competition_name": "Premier League",
                    "competition_id": 39,
                    "team_side": "away",
                },
            ]
        )
    )

    result = queries.get_recent_form(team_id=10, last_n_matches=2)

    assert result["success"] is True
    assert result["data"]["team_name"] == "Arsenal"
    assert result["data"]["overall_stats"] == {
        "wins": 1,
        "draws": 1,
        "losses": 0,
        "win_rate": 50.0,
        "draw_rate": 50.0,
        "loss_rate": 0.0,
    }
    assert result["data"]["recent_matches"][0]["score"] == "2-0"


def test_best_odds_maps_outcomes_and_implied_probability():
    retrieved_at = datetime(2026, 5, 27, 10, 0)
    queries = ReadOnlyFootballQueries(
        FakeReadOnlyRunner(
            many=[
                {
                    "match_id": 42,
                    "bookmaker_id": 1,
                    "bookmaker_name": "Bet365",
                    "bet_value": "Home Win",
                    "odds_value": 2.5,
                    "retrieved_at": retrieved_at,
                },
                {
                    "match_id": 42,
                    "bookmaker_id": 2,
                    "bookmaker_name": "Sky Bet",
                    "bet_value": "Away Win",
                    "odds_value": 3.0,
                    "retrieved_at": retrieved_at,
                },
            ]
        )
    )

    odds = queries.get_best_odds_for_match(42)

    assert odds["Home Win"]["odds_value"] == 2.5
    assert odds["Home Win"]["implied_probability"] == 0.4
    assert odds["Away Win"]["bookmaker_name"] == "Sky Bet"


def test_value_analysis_combines_predictions_and_odds():
    retrieved_at = datetime(2026, 5, 27, 10, 0)
    queries = ReadOnlyFootballQueries(
        FakeReadOnlyRunner(
            many=[
                [
                    {
                        "match_id": 42,
                        "predicted_result": 2,
                        "home_team_name": "Arsenal",
                        "away_team_name": "Chelsea",
                        "prob_home_win": 0.60,
                        "prob_draw": 0.25,
                        "prob_away_win": 0.15,
                        "model_type": "result_model",
                        "prediction_timestamp": datetime(2026, 5, 27, 12, 0),
                    }
                ],
                [
                    {
                        "match_id": 42,
                        "bookmaker_id": 1,
                        "bookmaker_name": "Bet365",
                        "bet_value": "Home Win",
                        "odds_value": 2.2,
                        "retrieved_at": retrieved_at,
                    }
                ],
            ]
        )
    )

    analysis = queries.analyze_matches_for_value([42], min_value_threshold=0.05)

    assert analysis["matches_processed"] == 1
    assert analysis["total_value_bets"] == 1
    assert analysis["all_value_bets"][0]["match_id"] == 42
    assert analysis["all_value_bets"][0]["expected_value"] == pytest.approx(0.32)


def test_postgres_runner_rejects_mutating_queries_before_connecting():
    def connect():
        raise AssertionError("should not connect for a mutating query")

    runner = PostgresReadOnlyRunner(connect)

    with pytest.raises(ValueError, match="read-only"):
        runner.fetch_all("UPDATE matches SET home_score = 1")
