import re
from pathlib import Path

from fastapi.testclient import TestClient

from football_intelligence.api import create_app


ROOT = Path(__file__).resolve().parents[1]
READ_ONLY_DASHBOARD_API_METHODS = {
    "/api/status": {"get"},
    "/api/board/today": {"get"},
    "/api/value-signals": {"get"},
    "/api/matches/{match_id}": {"get"},
}
DASHBOARD_FETCH_TARGETS = {
    "/api/status",
    "/api/board/today",
    "/api/value-signals?today=true",
    "/api/matches/${matchId}",
}
NON_DASHBOARD_FETCH_TARGETS = {
    "/api/chat",
    "/api/reset",
    "/api/prediction-refresh",
    "/api/odds-refresh",
    "/api/feature-rebuild",
    "/api/model-training",
}
FORBIDDEN_OPERATIONAL_API_PATHS = NON_DASHBOARD_FETCH_TARGETS - {
    "/api/chat",
    "/api/reset",
}
FORBIDDEN_DASHBOARD_CONTROL_LABELS = (
    "Prediction Refresh",
    "Refresh Predictions",
    "Odds Refresh",
    "Refresh Odds",
    "Feature Rebuild",
    "Rebuild Features",
    "Model Training",
    "Train Model",
    "Delete",
)
STATUS_PAYLOAD = {
    "title": "Football Data Status",
    "odds_freshness": {
        "latest_retrieved_at": None,
        "matches_with_odds_next_7_days": 0,
    },
    "top_premier_league_elo_teams": [],
    "warnings": [],
}
BOARD_PAYLOAD = {
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
    "empty_state": "No remaining Upcoming Matches are scheduled.",
}
SIGNAL_SCAN_PAYLOAD = {
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
MATCH_DETAIL_PAYLOAD = {
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


class FakeApiResource:
    def __init__(self, payload):
        self._payload = payload

    def to_dict(self):
        return self._payload


class FailingChatService:
    @property
    def available_tool_names(self):
        return ("upcoming_matches",)

    def process_query(self, user_input):
        raise AssertionError("Dashboard endpoints must not use Analyst Agent chat")

    def reset_conversation(self):
        raise AssertionError("Dashboard endpoints must not reset chat state")

    def get_conversation_stats(self):
        return {}


class FakeStatusService:
    def get_status(self):
        return FakeApiResource(STATUS_PAYLOAD)


class FakeBoardService:
    def today(self):
        return FakeApiResource(BOARD_PAYLOAD)


class FakeValueService:
    def today(self):
        return FakeApiResource(SIGNAL_SCAN_PAYLOAD)

    def next_days(self, *, days=7):
        return FakeApiResource(SIGNAL_SCAN_PAYLOAD)


class FakeMatchDetailService:
    def get_match_detail(self, match_id):
        assert match_id == 42
        return FakeApiResource(MATCH_DETAIL_PAYLOAD)


def test_dashboard_api_endpoints_are_get_only_deterministic_contracts():
    client = TestClient(create_app())

    schema = client.get("/openapi.json").json()

    for path, methods in READ_ONLY_DASHBOARD_API_METHODS.items():
        assert set(schema["paths"][path]) == methods

    for forbidden_path in FORBIDDEN_OPERATIONAL_API_PATHS:
        assert forbidden_path not in schema["paths"]


def test_dashboard_api_startup_does_not_run_database_setup(monkeypatch):
    from football_intelligence.database import setup as database_setup

    def fail_setup(*args, **kwargs):
        raise AssertionError("API startup must not run Database Setup")

    monkeypatch.setattr(database_setup, "setup_database", fail_setup)
    monkeypatch.setattr(database_setup, "upgrade_database", fail_setup)

    client = TestClient(create_app())

    assert client.get("/openapi.json").status_code == 200


def test_dashboard_api_endpoints_do_not_require_analyst_agent_chat_flow():
    client = TestClient(
        create_app(
            chat_service=FailingChatService(),
            status_service=FakeStatusService(),
            board_service=FakeBoardService(),
            value_service=FakeValueService(),
            match_detail_service=FakeMatchDetailService(),
        )
    )

    responses = [
        client.get("/api/status"),
        client.get("/api/board/today"),
        client.get("/api/value-signals?today=true"),
        client.get("/api/matches/42"),
    ]

    chat_response = client.post("/api/chat", json={"text": "Prediction for match 42?"})

    assert [response.status_code for response in responses] == [200, 200, 200, 200]
    assert chat_response.status_code == 500


def test_svelte_dashboard_only_calls_read_only_dashboard_endpoints():
    app_source = read_text(ROOT / "frontend" / "src" / "App.svelte")

    fetch_targets = set(re.findall(r"fetch\(`\$\{API_URL\}([^`]+)`\)", app_source))

    assert fetch_targets == DASHBOARD_FETCH_TARGETS
    assert "method:" not in app_source
    assert "type=\"submit\"" not in app_source

    for forbidden_endpoint in NON_DASHBOARD_FETCH_TARGETS:
        assert forbidden_endpoint not in fetch_targets

    for forbidden_control in FORBIDDEN_DASHBOARD_CONTROL_LABELS:
        assert forbidden_control.lower() not in app_source.lower()


def test_svelte_dashboard_renders_setup_required_state_without_operational_controls():
    app_source = read_text(ROOT / "frontend" / "src" / "App.svelte")

    assert "setup_required" in app_source
    assert "Database Setup required" in app_source
    assert "setup_command" in app_source
    assert "setupRequired = error.setupRequired" in app_source
    assert "/api/db" not in app_source


def test_future_agent_docs_pin_the_read_only_dashboard_boundary():
    domain_doc = read_text(ROOT / "docs" / "agents" / "domain.md")

    assert "CONTEXT.md" in domain_doc
    assert "ADR-0002" in domain_doc
    assert "read-only Svelte dashboard boundary" in domain_doc
    assert "Prediction Refresh" in domain_doc
    assert "Model Training" in domain_doc


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")
