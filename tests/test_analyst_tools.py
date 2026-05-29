from datetime import datetime

from football_intelligence.analyst import (
    ANALYST_TOOL_DEFINITIONS,
    AnalystFootballTools,
)
from football_intelligence.database import FootballQueryError


class FakeFootballQueries:
    def __init__(self):
        self.calls = []
        self.prediction = {
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

    def get_match_prediction(self, match_id):
        self.calls.append(("get_match_prediction", match_id))
        return self.prediction

    def get_upcoming_matches(
        self,
        days_ahead=7,
        competition_ids=None,
        country=None,
        limit=None,
    ):
        self.calls.append(
            ("get_upcoming_matches", days_ahead, competition_ids, country, limit)
        )
        return [
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

    def get_recent_form(
        self,
        team_id,
        last_n_matches=10,
        competition_id=None,
        at_home=None,
    ):
        self.calls.append(
            ("get_recent_form", team_id, last_n_matches, competition_id, at_home)
        )
        return {
            "success": True,
            "error": None,
            "data": {
                "team_id": team_id,
                "team_name": "Arsenal",
                "total_matches": 2,
                "recent_matches": [
                    {
                        "match_id": 1,
                        "date": datetime(2026, 5, 1, 15, 0),
                        "team_result": "Win",
                    }
                ],
            },
        }

    def get_best_odds_for_match(self, match_id, bet_type_id=1):
        self.calls.append(("get_best_odds_for_match", match_id, bet_type_id))
        return {
            "Home Win": {
                "odds_value": 2.5,
                "bookmaker_name": "Bet365",
                "retrieved_at": datetime(2026, 5, 27, 10, 0),
            }
        }

    def get_latest_match_odds(self, match_id, bet_type_id=1):
        self.calls.append(("get_latest_match_odds", match_id, bet_type_id))
        return {
            "Home Win": [
                {
                    "odds_value": 2.5,
                    "bookmaker_name": "Bet365",
                    "retrieved_at": datetime(2026, 5, 27, 10, 0),
                }
            ]
        }

    def analyze_matches_for_value(
        self,
        match_ids,
        kelly_fraction=0.50,
        min_value_threshold=0.05,
    ):
        self.calls.append(
            (
                "analyze_matches_for_value",
                match_ids,
                kelly_fraction,
                min_value_threshold,
            )
        )
        return {
            "total_matches_analyzed": len(match_ids),
            "total_value_bets": 1,
            "all_value_bets": [
                {
                    "match_id": match_ids[0],
                    "expected_value": 0.32,
                    "prediction_date": datetime(2026, 5, 27, 12, 0),
                }
            ],
        }


class FailingFootballQueries(FakeFootballQueries):
    def get_upcoming_matches(self, *args, **kwargs):
        raise FootballQueryError("database offline")


def test_analyst_tool_definitions_are_curated_read_only_contracts():
    definitions = {definition.name: definition for definition in ANALYST_TOOL_DEFINITIONS}

    assert set(definitions) == {
        "match_prediction",
        "upcoming_matches",
        "recent_form",
        "match_odds",
        "value_lookup",
    }
    for definition in definitions.values():
        assert definition.description
        assert definition.input_schema["type"] == "object"


def test_match_prediction_tool_returns_stable_agent_result():
    queries = FakeFootballQueries()
    tools = AnalystFootballTools(queries)

    result = tools.get_match_prediction(match_id=42)

    assert result == {
        "success": True,
        "tool": "match_prediction",
        "error": None,
        "data": {
            "match_id": 42,
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "predicted_result": "Home Win",
            "confidence": 0.61,
            "prob_home_win": 0.61,
            "prob_draw": 0.21,
            "prob_away_win": 0.18,
            "model_type": "result_model",
            "prediction_date": "2026-05-27T12:00:00",
        },
    }
    assert queries.calls == [("get_match_prediction", 42)]


def test_match_prediction_tool_returns_not_found_shape():
    queries = FakeFootballQueries()
    queries.prediction = None
    tools = AnalystFootballTools(queries)

    result = tools.get_match_prediction(match_id=404)

    assert result == {
        "success": False,
        "tool": "match_prediction",
        "error": {
            "code": "not_found",
            "message": "No prediction found for match 404",
        },
        "data": None,
    }


def test_upcoming_matches_tool_wraps_matches_with_filters_and_summary():
    queries = FakeFootballQueries()
    tools = AnalystFootballTools(queries)

    result = tools.get_upcoming_matches(
        days_ahead="5",
        competition_ids=["39"],
        country="England",
        limit="3",
    )

    assert result["success"] is True
    assert result["tool"] == "upcoming_matches"
    assert result["error"] is None
    assert result["data"]["filters"] == {
        "days_ahead": 5,
        "competition_ids": [39],
        "country": "England",
        "limit": 3,
    }
    assert result["data"]["summary"] == {"matches_returned": 1}
    assert result["data"]["matches"][0]["home_team"] == "Liverpool"
    assert queries.calls == [
        ("get_upcoming_matches", 5, [39], "England", 3),
    ]


def test_recent_form_tool_returns_form_data_without_nested_legacy_envelope():
    queries = FakeFootballQueries()
    tools = AnalystFootballTools(queries)

    result = tools.get_recent_form(
        team_id="10",
        last_n_matches="2",
        competition_id=39,
        at_home=True,
    )

    assert result["success"] is True
    assert result["tool"] == "recent_form"
    assert result["data"]["team_name"] == "Arsenal"
    assert result["data"]["recent_matches"][0]["date"] == "2026-05-01T15:00:00"
    assert queries.calls == [
        ("get_recent_form", 10, 2, 39, True),
    ]


def test_recent_form_tool_maps_query_no_result_to_not_found_shape():
    class NoRecentFormQueries(FakeFootballQueries):
        def get_recent_form(self, *args, **kwargs):
            return {
                "success": False,
                "error": "No matches found for team ID 10",
                "data": None,
            }

    tools = AnalystFootballTools(NoRecentFormQueries())

    assert tools.get_recent_form(team_id=10) == {
        "success": False,
        "tool": "recent_form",
        "error": {
            "code": "not_found",
            "message": "No matches found for team ID 10",
        },
        "data": None,
    }


def test_match_odds_tool_returns_best_odds_contract_by_default():
    queries = FakeFootballQueries()
    tools = AnalystFootballTools(queries)

    result = tools.get_match_odds(match_id="42")

    assert result == {
        "success": True,
        "tool": "match_odds",
        "error": None,
        "data": {
            "match_id": 42,
            "bet_type_id": 1,
            "include_all_bookmakers": False,
            "odds": {
                "Home Win": {
                    "odds_value": 2.5,
                    "bookmaker_name": "Bet365",
                    "retrieved_at": "2026-05-27T10:00:00",
                }
            },
        },
    }
    assert queries.calls == [("get_best_odds_for_match", 42, 1)]


def test_match_odds_tool_can_return_all_bookmaker_odds():
    queries = FakeFootballQueries()
    tools = AnalystFootballTools(queries)

    result = tools.get_match_odds(match_id=42, include_all_bookmakers=True)

    assert result["success"] is True
    assert result["data"]["include_all_bookmakers"] is True
    assert result["data"]["odds"]["Home Win"][0]["bookmaker_name"] == "Bet365"
    assert queries.calls == [("get_latest_match_odds", 42, 1)]


def test_value_lookup_tool_returns_value_analysis_contract():
    queries = FakeFootballQueries()
    tools = AnalystFootballTools(queries)

    result = tools.get_value_lookup(
        match_ids=["42"],
        kelly_fraction="0.25",
        min_value_threshold="0.10",
    )

    assert result["success"] is True
    assert result["tool"] == "value_lookup"
    assert result["data"]["total_matches_analyzed"] == 1
    assert result["data"]["all_value_bets"][0] == {
        "match_id": 42,
        "expected_value": 0.32,
        "prediction_date": "2026-05-27T12:00:00",
    }
    assert queries.calls == [
        ("analyze_matches_for_value", [42], 0.25, 0.10),
    ]


def test_value_lookup_tool_rejects_scalar_match_ids():
    tools = AnalystFootballTools(FakeFootballQueries())

    result = tools.get_value_lookup(match_ids="42")

    assert result == {
        "success": False,
        "tool": "value_lookup",
        "error": {
            "code": "invalid_input",
            "message": "match_ids must be a sequence of match IDs",
        },
        "data": None,
    }


def test_run_dispatches_named_tool_and_returns_invalid_input_for_bad_arguments():
    tools = AnalystFootballTools(FakeFootballQueries())

    result = tools.run("match_prediction", {"match_id": 42})
    missing_input = tools.run("match_prediction")
    unknown = tools.run("raw_sql", {"query": "SELECT 1"})

    assert result["success"] is True
    assert missing_input["success"] is False
    assert missing_input["error"]["code"] == "invalid_input"
    assert unknown == {
        "success": False,
        "tool": "raw_sql",
        "error": {
            "code": "unknown_tool",
            "message": "Unknown Analyst Tool: raw_sql",
        },
        "data": None,
    }


def test_backend_errors_return_stable_failure_shape():
    tools = AnalystFootballTools(FailingFootballQueries())

    result = tools.get_upcoming_matches()

    assert result == {
        "success": False,
        "tool": "upcoming_matches",
        "error": {"code": "backend_error", "message": "database offline"},
        "data": None,
    }
