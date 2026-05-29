from fastapi.testclient import TestClient

from football_intelligence.analyst import AnalystAgent, AnalystFootballTools
from football_intelligence.api import AnalystChatService, create_app
from tests.test_analyst_agent import FakePlanner, FakeSynthesizer
from tests.test_analyst_tools import FakeFootballQueries


class FakeAnalystAgent:
    def __init__(self):
        self.questions = []
        self.available_tool_names = (
            "match_prediction",
            "upcoming_matches",
            "recent_form",
            "match_odds",
            "value_lookup",
        )

    def answer_question(self, question):
        self.questions.append(question)

        class Response:
            answer = "Arsenal have a 61% home-win Prediction."

        return Response()


def test_chat_endpoint_preserves_request_and_response_shape():
    agent = FakeAnalystAgent()
    service = AnalystChatService(agent)
    client = TestClient(create_app(service))

    response = client.post("/api/chat", json={"text": "Prediction for match 42?"})

    assert response.status_code == 200
    assert response.json() == {
        "response": "Arsenal have a 61% home-win Prediction.",
    }
    assert agent.questions == ["Prediction for match 42?"]


def test_chat_endpoint_returns_representative_analyst_agent_answer():
    agent = AnalystAgent(
        tools=AnalystFootballTools(FakeFootballQueries()),
        planner=FakePlanner(),
        synthesizer=FakeSynthesizer(),
    )
    client = TestClient(create_app(AnalystChatService(agent)))

    response = client.post("/api/chat", json={"text": "Prediction for match 42?"})

    assert response.status_code == 200
    assert response.json() == {
        "response": (
            "Arsenal are ahead in the model.\n\n"
            "Prediction note: Predictions are model estimates, not guarantees. "
            "Use probabilities as uncertainty, not certainty."
        )
    }


def test_chat_service_tracks_and_resets_conversation_context():
    agent = FakeAnalystAgent()
    service = AnalystChatService(agent)
    client = TestClient(create_app(service))

    first = client.post("/api/chat", json={"text": "Prediction for match 42?"})
    second = client.post("/api/chat", json={"text": "What about this match odds?"})
    reset = client.post("/api/reset")

    assert first.status_code == 200
    assert second.status_code == 200
    assert "Recent conversation context:" in agent.questions[1]
    assert "Prediction for match 42?" in agent.questions[1]
    assert "Arsenal have a 61% home-win Prediction." in agent.questions[1]
    assert reset.status_code == 200
    assert reset.json() == {"message": "Conversation reset successfully"}
    assert service.get_conversation_stats()["total_messages"] == 0


def test_api_exposes_only_read_only_analyst_tools():
    agent = FakeAnalystAgent()
    service = AnalystChatService(agent)

    assert set(service.available_tool_names) == {
        "match_prediction",
        "upcoming_matches",
        "recent_form",
        "match_odds",
        "value_lookup",
    }
    assert "prediction_refresh" not in service.available_tool_names
    assert "model_training" not in service.available_tool_names


def test_status_endpoint_returns_deterministic_football_data_status_json():
    class FakeStatus:
        def to_dict(self):
            return {
                "title": "Football Data Status",
                "latest_completed_match": {
                    "match_id": 42,
                    "start_time": "2026-05-27T20:00:00",
                    "home_team": "Arsenal",
                    "away_team": "Chelsea",
                    "competition": "Premier League",
                    "country": "England",
                    "score": "2-1",
                },
                "unprocessed_completed_matches": 0,
                "latest_elo_history_date": "2026-05-26T22:00:00",
                "future_feature_set_count": 7,
                "prediction_count_next_7_days": 6,
                "odds_freshness": {
                    "latest_retrieved_at": "2026-05-28T12:00:00",
                    "latest_api_last_updated": None,
                    "matches_with_odds_next_7_days": 5,
                    "stale_after_hours": 24,
                },
                "top_premier_league_elo_teams": [
                    {
                        "team_id": 1,
                        "team_name": "Arsenal",
                        "elo": 1875,
                        "competition": "Premier League",
                        "country": "England",
                    }
                ],
                "warnings": [],
            }

    class FakeStatusService:
        def get_status(self):
            return FakeStatus()

    client = TestClient(create_app(FakeAnalystAgent(), FakeStatusService()))

    response = client.get("/api/status")

    assert response.status_code == 200
    assert response.json() == FakeStatus().to_dict()
