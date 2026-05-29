from datetime import datetime

from football_intelligence.status import FootballDataStatusService


class FakeReadOnlyRunner:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def fetch_one(self, query, params=()):
        self.calls.append(("one", query, tuple(params)))
        return self.results.pop(0)

    def fetch_all(self, query, params=()):
        self.calls.append(("all", query, tuple(params)))
        return self.results.pop(0)


def test_football_data_status_reports_facts_and_warnings():
    from football_intelligence.database.football import ReadOnlyFootballQueries

    runner = FakeReadOnlyRunner(
        [
            {
                "match_id": 42,
                "start_time": datetime(2026, 5, 27, 20, 0),
                "home_team_name": "Arsenal",
                "away_team_name": "Chelsea",
                "competition_name": "Premier League",
                "competition_country": "England",
                "home_score": 2,
                "away_score": 1,
            },
            {"count": 2},
            {"latest_elo_history_date": datetime(2026, 5, 26, 22, 0)},
            {"count": 0},
            {"count": 3},
            {
                "latest_retrieved_at": datetime(2026, 5, 28, 12, 0),
                "latest_api_last_updated": datetime(2026, 5, 28, 11, 50),
                "matches_with_odds_next_7_days": 2,
            },
            [
                {
                    "team_id": 1,
                    "team_name": "Arsenal",
                    "elo": 1875,
                    "competition": "Premier League",
                    "country": "England",
                },
                {
                    "team_id": 2,
                    "team_name": "Liverpool",
                    "elo": 1840,
                    "competition": "Premier League",
                    "country": "England",
                },
            ],
        ]
    )
    service = FootballDataStatusService(
        ReadOnlyFootballQueries(runner),
        now_factory=lambda: datetime(2026, 5, 29, 12, 0),
    )

    status = service.get_status().to_dict()

    assert status["title"] == "Football Data Status"
    assert status["latest_completed_match"] == {
        "match_id": 42,
        "start_time": "2026-05-27T20:00:00",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "competition": "Premier League",
        "country": "England",
        "score": "2-1",
    }
    assert status["unprocessed_completed_matches"] == 2
    assert status["latest_elo_history_date"] == "2026-05-26T22:00:00"
    assert status["future_feature_set_count"] == 0
    assert status["prediction_count_next_7_days"] == 3
    assert status["odds_freshness"] == {
        "latest_retrieved_at": "2026-05-28T12:00:00",
        "latest_api_last_updated": "2026-05-28T11:50:00",
        "matches_with_odds_next_7_days": 2,
        "stale_after_hours": 24,
    }
    assert [team["team_name"] for team in status["top_premier_league_elo_teams"]] == [
        "Arsenal",
        "Liverpool",
    ]
    assert status["warnings"] == [
        {
            "code": "unprocessed_completed_matches",
            "severity": "warning",
            "message": (
                "2 Completed Matches have not been incorporated into the "
                "Historical Feature Set."
            ),
        },
        {
            "code": "missing_future_feature_set",
            "severity": "warning",
            "message": "No Future Feature Set rows are available for the next 7 days.",
        },
    ]


def test_football_data_status_warns_when_odds_are_stale():
    class FakeStatusQueries:
        def get_football_data_status_facts(self, **kwargs):
            return {
                "latest_completed_match": None,
                "unprocessed_completed_matches": 0,
                "latest_elo_history_date": None,
                "future_feature_set_count": 1,
                "prediction_count_next_7_days": 1,
                "odds_freshness": {
                    "latest_retrieved_at": datetime(2026, 5, 27, 12, 0),
                    "latest_api_last_updated": None,
                    "matches_with_odds_next_7_days": 1,
                },
                "top_premier_league_elo_teams": [],
            }

    service = FootballDataStatusService(
        FakeStatusQueries(),
        now_factory=lambda: datetime(2026, 5, 29, 12, 0),
    )

    warnings = service.get_status().to_dict()["warnings"]

    assert {warning["code"] for warning in warnings} == {
        "missing_latest_completed_match",
        "missing_latest_elo_history",
        "stale_odds",
        "missing_premier_league_elo_teams",
    }
