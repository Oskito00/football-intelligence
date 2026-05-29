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


def test_prediction_board_match_window_uses_explicit_bounds():
    starts_at = datetime(2026, 5, 29, 12, 0)
    ends_at = datetime(2026, 5, 30, 0, 0)
    runner = FakeReadOnlyRunner(
        many=[
            {
                "match_id": 42,
                "start_time": datetime(2026, 5, 29, 20, 0),
                "home_team_name": "Arsenal",
                "away_team_name": "Chelsea",
                "competition_name": "Premier League",
                "competition_country": "England",
                "competition_id": 39,
            }
        ]
    )
    queries = ReadOnlyFootballQueries(runner)

    matches = queries.get_upcoming_matches_between(
        starts_at=starts_at,
        ends_at=ends_at,
    )

    assert matches[0]["match_id"] == 42
    assert runner.calls == [("all", runner.calls[0][1], (starts_at, ends_at))]


def test_match_detail_lookup_maps_match_by_id():
    start_time = datetime(2026, 5, 29, 20, 0)
    queries = ReadOnlyFootballQueries(
        FakeReadOnlyRunner(
            one={
                "match_id": 42,
                "start_time": start_time,
                "home_team_name": "Arsenal",
                "away_team_name": "Chelsea",
                "competition_name": "Premier League",
                "competition_country": "England",
                "competition_id": 39,
                "match_status": "NS",
                "home_score": None,
                "away_score": None,
            }
        )
    )

    match = queries.get_match(42)

    assert match == {
        "match_id": 42,
        "start_time": start_time,
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "competition": "Premier League",
        "country": "England",
        "competition_id": 39,
        "status": "NS",
        "score": None,
    }


def test_feature_snapshot_facts_collect_future_feature_families():
    runner = FakeReadOnlyRunner(
        many=[
            [{"competition_season_name": "2025/2026"}],
            [{"stage_of_season": 0.73, "stage_of_season_category": "late"}],
            [{"home_team_formation": "4-3-3", "away_team_formation": "3-4-3"}],
            [
                {
                    "home_team_elo_K40": 1875,
                    "away_team_elo_K40": 1810,
                    "k_draw_parameter": 0.24,
                    "eta_home_advantage": 0.31,
                }
            ],
            [
                {
                    "home_standing": 2,
                    "home_points": 71,
                    "away_standing": 5,
                    "away_points": 63,
                }
            ],
            [
                {
                    "h2h_home_wins_last_10": 0.5,
                    "h2h_draws_last_10": 0.2,
                    "h2h_away_wins_last_10": 0.3,
                    "h2h_avg_total_goals": 2.6,
                }
            ],
            [{"home_team_form": {"wins": 3}, "away_team_form": {"wins": 2}}],
        ]
    )
    queries = ReadOnlyFootballQueries(runner)

    facts = queries.get_feature_snapshot_facts(42)

    assert facts["match_info"] == {"competition_season": "2025/2026"}
    assert facts["team_strength"]["home_team_elo_K40"] == 1875
    assert facts["league_standings"]["away_points"] == 63
    assert facts["head_to_head"]["h2h_avg_total_goals"] == 2.6
    assert facts["form"]["home_team_form"] == {"wins": 3}
    assert all(call[2] == (42,) for call in runner.calls)


def test_odds_freshness_maps_latest_odds_by_match():
    retrieved_at = datetime(2026, 5, 29, 9, 30)
    api_last_updated = datetime(2026, 5, 29, 9, 20)
    runner = FakeReadOnlyRunner(
        many=[
            {
                "match_id": 42,
                "latest_retrieved_at": retrieved_at,
                "latest_api_last_updated": api_last_updated,
            }
        ]
    )
    queries = ReadOnlyFootballQueries(runner)

    freshness = queries.get_odds_freshness_for_matches([42, 43])

    assert freshness == {
        42: {
            "latest_retrieved_at": retrieved_at,
            "latest_api_last_updated": api_last_updated,
        }
    }
    assert runner.calls[0][2] == (42, 43)


def test_value_backtest_rows_group_predictions_and_historical_odds():
    start_time = datetime(2026, 5, 29, 20, 0)
    prediction_timestamp = datetime(2026, 5, 29, 10, 0)
    retrieved_at = datetime(2026, 5, 29, 9, 0)
    runner = FakeReadOnlyRunner(
        many=[
            {
                "match_id": 42,
                "start_time": start_time,
                "home_team_name": "Arsenal",
                "away_team_name": "Chelsea",
                "competition_name": "Premier League",
                "competition_country": "England",
                "home_score": 2,
                "away_score": 1,
                "prob_home_win": 0.61,
                "prob_draw": 0.21,
                "prob_away_win": 0.18,
                "prediction_timestamp": prediction_timestamp,
                "model_type": "result_model",
                "bookmaker_id": 8,
                "bookmaker_name": "Bet365",
                "bet_value": "Home",
                "odds_value": 2.1,
                "retrieved_at": retrieved_at,
                "api_last_updated": datetime(2026, 5, 29, 8, 55),
            },
            {
                "match_id": 42,
                "start_time": start_time,
                "home_team_name": "Arsenal",
                "away_team_name": "Chelsea",
                "competition_name": "Premier League",
                "competition_country": "England",
                "home_score": 2,
                "away_score": 1,
                "prob_home_win": 0.61,
                "prob_draw": 0.21,
                "prob_away_win": 0.18,
                "prediction_timestamp": prediction_timestamp,
                "model_type": "result_model",
                "bookmaker_id": 9,
                "bookmaker_name": "Sky Bet",
                "bet_value": "Draw",
                "odds_value": 3.4,
                "retrieved_at": retrieved_at,
                "api_last_updated": datetime(2026, 5, 29, 8, 57),
            },
        ]
    )
    queries = ReadOnlyFootballQueries(runner)

    matches = queries.get_value_backtest_matches()

    assert matches == [
        {
            "match_id": 42,
            "start_time": start_time,
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "competition": "Premier League",
            "country": "England",
            "home_score": 2,
            "away_score": 1,
            "prediction": {
                "prediction_date": prediction_timestamp,
                "prob_home_win": 0.61,
                "prob_draw": 0.21,
                "prob_away_win": 0.18,
                "model_type": "result_model",
            },
            "odds": [
                {
                    "outcome": "Home Win",
                    "bookmaker_id": 8,
                    "bookmaker_name": "Bet365",
                    "odds_value": 2.1,
                    "retrieved_at": retrieved_at,
                    "api_last_updated": datetime(2026, 5, 29, 8, 55),
                },
                {
                    "outcome": "Draw",
                    "bookmaker_id": 9,
                    "bookmaker_name": "Sky Bet",
                    "odds_value": 3.4,
                    "retrieved_at": retrieved_at,
                    "api_last_updated": datetime(2026, 5, 29, 8, 57),
                },
            ],
        }
    ]
    assert runner.calls[0][0] == "all"
    assert runner.calls[0][2] == ()


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
