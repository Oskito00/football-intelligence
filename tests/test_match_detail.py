from datetime import datetime

from fastapi.testclient import TestClient

from football_intelligence.api import create_app
from football_intelligence.match_detail import (
    MatchDetailNotFound,
    MatchDetailService,
)


class FakeMatchDetailQueries:
    def get_match(self, match_id):
        assert match_id == 42
        return {
            "match_id": 42,
            "start_time": datetime(2026, 5, 29, 20, 0),
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "competition": "Premier League",
            "country": "England",
            "competition_id": 39,
            "status": "NS",
            "score": None,
        }

    def get_match_prediction(self, match_id):
        assert match_id == 42
        return {
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

    def get_best_odds_for_match(self, match_id):
        assert match_id == 42
        return {
            "Home Win": {
                "bookmaker_id": 1,
                "bookmaker_name": "Bet365",
                "odds_value": 2.1,
                "implied_probability": 0.4761904762,
                "retrieved_at": datetime(2026, 5, 29, 9, 30),
            },
            "Draw": {
                "bookmaker_id": 2,
                "bookmaker_name": "Sky Bet",
                "odds_value": 3.4,
                "implied_probability": 0.2941176471,
                "retrieved_at": datetime(2026, 5, 29, 9, 35),
            },
        }

    def get_feature_snapshot_facts(self, match_id):
        assert match_id == 42
        return {
            "match_info": {
                "competition_season": "2025/2026",
            },
            "stage_of_season": {
                "stage_of_season": 0.73,
                "stage_of_season_category": "late",
            },
            "team_strength": {
                "home_team_elo_K40": 1875,
                "away_team_elo_K40": 1810,
                "k_draw_parameter": 0.24,
                "eta_home_advantage": 0.31,
            },
            "league_standings": {
                "home_standing": 2,
                "home_points": 71,
                "away_standing": 5,
                "away_points": 63,
            },
            "formation": {
                "home_team_formation": "4-3-3",
                "away_team_formation": "3-4-3",
            },
            "head_to_head": {
                "h2h_home_wins_last_10": 0.5,
                "h2h_draws_last_10": 0.2,
                "h2h_away_wins_last_10": 0.3,
                "h2h_avg_total_goals": 2.6,
            },
        }


def test_match_detail_service_returns_prediction_odds_and_feature_snapshot():
    detail = MatchDetailService(FakeMatchDetailQueries()).get_match_detail(42).to_dict()

    assert detail["title"] == "Match Detail"
    assert detail["match"] == {
        "match_id": 42,
        "start_time": "2026-05-29T20:00:00",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "competition": "Premier League",
        "country": "England",
        "competition_id": 39,
        "status": "NS",
        "score": None,
    }
    assert detail["prediction"]["predicted_result"] == "Home Win"
    assert detail["prediction_empty_state"] is None
    assert detail["odds_context"]["best_prices"][0] == {
        "outcome": "Home Win",
        "best_odds": 2.1,
        "implied_probability": 0.4761904762,
        "bookmaker": "Bet365",
        "retrieved_at": "2026-05-29T09:30:00",
    }
    assert detail["odds_context"]["empty_state"] is None
    assert detail["feature_snapshot"]["available"] is True
    assert detail["feature_snapshot"]["groups"][0]["title"] == "Match Context"
    assert detail["feature_snapshot"]["groups"][1]["metrics"][0] == {
        "label": "Home Elo K40",
        "value": 1875.0,
    }
    assert detail["feature_snapshot"]["market_context"]["best_prices"][1]["outcome"] == "Draw"
    assert detail["feature_snapshot"]["empty_state"] is None
    assert detail["warnings"] == []


def test_match_detail_service_reports_empty_states_for_missing_optional_data():
    class MissingOptionalQueries(FakeMatchDetailQueries):
        def get_match_prediction(self, match_id):
            return None

        def get_best_odds_for_match(self, match_id):
            return {}

        def get_feature_snapshot_facts(self, match_id):
            return {}

    detail = MatchDetailService(MissingOptionalQueries()).get_match_detail(42).to_dict()

    assert detail["prediction"] is None
    assert detail["prediction_empty_state"] == "No Prediction is available for this match."
    assert detail["odds_context"]["best_prices"] == []
    assert detail["odds_context"]["empty_state"] == "No odds context is available for this match."
    assert detail["feature_snapshot"]["available"] is False
    assert detail["feature_snapshot"]["groups"] == []
    assert detail["feature_snapshot"]["empty_state"] == (
        "No Feature Snapshot inputs are available for this match."
    )
    assert {warning["code"] for warning in detail["warnings"]} == {
        "missing_prediction",
        "missing_odds",
        "missing_feature_snapshot",
    }


def test_match_detail_api_returns_deterministic_match_detail_json():
    class FakeMatchDetail:
        def to_dict(self):
            return {
                "title": "Match Detail",
                "match": {"match_id": 42},
                "prediction": None,
                "prediction_empty_state": "No Prediction is available for this match.",
                "odds_context": {
                    "has_odds": False,
                    "best_prices": [],
                    "empty_state": "No odds context is available for this match.",
                },
                "feature_snapshot": {
                    "title": "Feature Snapshot",
                    "available": False,
                    "groups": [],
                    "market_context": {"has_odds": False, "best_prices": []},
                    "empty_state": "No Feature Snapshot inputs are available for this match.",
                },
                "warnings": [],
            }

    class FakeMatchDetailService:
        def get_match_detail(self, match_id):
            assert match_id == 42
            return FakeMatchDetail()

    client = TestClient(create_app(match_detail_service=FakeMatchDetailService()))

    response = client.get("/api/matches/42")

    assert response.status_code == 200
    assert response.json() == FakeMatchDetail().to_dict()


def test_match_detail_api_returns_not_found_for_missing_match():
    class MissingMatchDetailService:
        def get_match_detail(self, match_id):
            assert match_id == 404
            raise MatchDetailNotFound("Match 404 was not found")

    client = TestClient(create_app(match_detail_service=MissingMatchDetailService()))

    response = client.get("/api/matches/404")

    assert response.status_code == 404
    assert response.json() == {"detail": "Match 404 was not found"}
