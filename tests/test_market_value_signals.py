from datetime import datetime

from fastapi.testclient import TestClient

from football_intelligence.api import create_app
from football_intelligence.cli import main as cli_main
from football_intelligence.value import MarketValueSignalService


class FakeValueQueries:
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
                "start_time": "2026-05-30T15:00:00",
                "home_team": "Liverpool",
                "away_team": "Everton",
                "competition": "Premier League",
                "country": "England",
                "competition_id": 39,
            },
        ]

    def analyze_matches_for_value(self, match_ids):
        self.calls.append(("value", tuple(match_ids)))
        return {
            "total_matches_analyzed": 2,
            "matches_with_predictions": 2,
            "matches_with_odds": 1,
            "matches_with_value_bets": 1,
            "total_value_bets": 1,
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
                    "prediction_date": datetime(2026, 5, 29, 10, 0),
                }
            ],
        }


def test_market_value_signal_service_scans_next_seven_days_by_default():
    queries = FakeValueQueries()
    service = MarketValueSignalService(
        queries,
        now_factory=lambda: datetime(2026, 5, 29, 12, 0),
    )

    scan = service.next_days().to_dict()

    assert scan["title"] == "Market Value Signals"
    assert scan["window"] == {
        "starts_at": "2026-05-29T12:00:00",
        "ends_at": "2026-06-05T12:00:00",
        "timezone": "local",
        "label": "next_7_days",
    }
    assert scan["summary"] == {
        "upcoming_match_count": 2,
        "matches_with_predictions": 2,
        "matches_with_odds": 1,
        "matches_with_value_signals": 1,
        "market_value_signal_count": 1,
    }
    assert scan["signals"] == [
        {
            "match_id": 42,
            "start_time": "2026-05-29T20:00:00",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "competition": "Premier League",
            "country": "England",
            "outcome": "Home Win",
            "model_probability": 0.61,
            "best_odds": 2.1,
            "implied_probability": 0.4761904762,
            "edge": 0.281,
            "bookmaker": "Bet365",
            "paper_stake_percentage": 12.4,
            "prediction_date": "2026-05-29T10:00:00",
        }
    ]
    assert scan["empty_state"] is None
    assert queries.calls == [
        (
            "matches",
            datetime(2026, 5, 29, 12, 0),
            datetime(2026, 6, 5, 12, 0),
        ),
        ("value", (42, 43)),
    ]


def test_market_value_signal_service_scans_today_local_date_window():
    queries = FakeValueQueries()
    service = MarketValueSignalService(
        queries,
        now_factory=lambda: datetime(2026, 5, 29, 12, 0),
    )

    scan = service.today().to_dict()

    assert scan["window"]["starts_at"] == "2026-05-29T12:00:00"
    assert scan["window"]["ends_at"] == "2026-05-30T00:00:00"
    assert scan["window"]["label"] == "today"


def test_value_picks_cli_defaults_to_next_seven_days_and_renders_paper_stake(
    monkeypatch,
    capsys,
):
    class FakeService:
        def next_days(self, *, days=7):
            assert days == 7
            return FakeScan()

    class FakeScan:
        def to_dict(self):
            return {
                "title": "Market Value Signals",
                "window": {
                    "starts_at": "2026-05-29T12:00:00",
                    "ends_at": "2026-06-05T12:00:00",
                    "timezone": "local",
                    "label": "next_7_days",
                },
                "summary": {
                    "upcoming_match_count": 1,
                    "matches_with_predictions": 1,
                    "matches_with_odds": 1,
                    "matches_with_value_signals": 1,
                    "market_value_signal_count": 1,
                },
                "signals": [
                    {
                        "match_id": 42,
                        "start_time": "2026-05-29T20:00:00",
                        "home_team": "Arsenal",
                        "away_team": "Chelsea",
                        "competition": "Premier League",
                        "country": "England",
                        "outcome": "Home Win",
                        "model_probability": 0.61,
                        "best_odds": 2.1,
                        "implied_probability": 0.4761904762,
                        "edge": 0.281,
                        "bookmaker": "Bet365",
                        "paper_stake_percentage": 12.4,
                        "prediction_date": "2026-05-29T10:00:00",
                    }
                ],
                "warnings": [],
                "empty_state": None,
            }

    monkeypatch.setattr(cli_main, "get_market_value_signal_service", FakeService)

    exit_code = cli_main.main(["value-picks"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Market Value Signals - next_7_days" in output
    assert "Arsenal vs Chelsea" in output
    assert "Outcome: Home Win" in output
    assert "Model Probability: 61.0%" in output
    assert "Best Odds: 2.10" in output
    assert "Implied Probability: 47.6%" in output
    assert "Edge: 28.1%" in output
    assert "Bookmaker: Bet365" in output
    assert "Paper Stake: 12.4%" in output
    assert "Recommended Stake" not in output


def test_value_picks_cli_today_uses_today_window(monkeypatch, capsys):
    calls = []

    class FakeService:
        def today(self):
            calls.append("today")
            return FakeScan()

    class FakeScan:
        def to_dict(self):
            return {
                "title": "Market Value Signals",
                "window": {
                    "starts_at": "2026-05-29T12:00:00",
                    "ends_at": "2026-05-30T00:00:00",
                    "timezone": "local",
                    "label": "today",
                },
                "summary": {
                    "upcoming_match_count": 0,
                    "matches_with_predictions": 0,
                    "matches_with_odds": 0,
                    "matches_with_value_signals": 0,
                    "market_value_signal_count": 0,
                },
                "signals": [],
                "warnings": [],
                "empty_state": "No Market Value Signals found for this window.",
            }

    monkeypatch.setattr(cli_main, "get_market_value_signal_service", FakeService)

    exit_code = cli_main.main(["value-picks", "--today"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert calls == ["today"]
    assert "Market Value Signals - today" in output
    assert "No Market Value Signals found for this window." in output


def test_value_signals_api_returns_deterministic_json_and_today_window():
    class FakeValueService:
        def today(self):
            return FakeScan("today")

        def next_days(self, *, days=7):
            return FakeScan(f"next_{days}_days")

    class FakeScan:
        def __init__(self, label):
            self._label = label

        def to_dict(self):
            return {
                "title": "Market Value Signals",
                "generated_at": "2026-05-29T12:00:00",
                "window": {
                    "starts_at": "2026-05-29T12:00:00",
                    "ends_at": "2026-05-30T00:00:00",
                    "timezone": "local",
                    "label": self._label,
                },
                "summary": {
                    "upcoming_match_count": 0,
                    "matches_with_predictions": 0,
                    "matches_with_odds": 0,
                    "matches_with_value_signals": 0,
                    "market_value_signal_count": 0,
                },
                "signals": [],
                "warnings": [],
                "empty_state": "No Market Value Signals found for this window.",
            }

    client = TestClient(create_app(value_service=FakeValueService()))

    response = client.get("/api/value-signals?today=true")

    assert response.status_code == 200
    assert response.json()["window"]["label"] == "today"
