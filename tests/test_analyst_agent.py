from football_intelligence.analyst import (
    ANALYST_TOOL_DEFINITIONS,
    AnalystAgent,
    AnalystFootballTools,
)
from football_intelligence.analyst.agent import (
    LangChainAnalystPlanner,
    LangChainAnswerSynthesizer,
)

from tests.test_analyst_tools import FakeFootballQueries


class FakePlanner:
    def __init__(self):
        self.calls = []

    def plan(self, question, tool_definitions):
        self.calls.append(
            (question, tuple(definition.name for definition in tool_definitions))
        )
        return [{"name": "match_prediction", "arguments": {"match_id": 42}}]


class FakeSynthesizer:
    def __init__(self):
        self.calls = []

    def synthesize(self, question, tool_results, answer_rules):
        self.calls.append((question, tool_results, answer_rules))
        return "Arsenal are ahead in the model."


class StaticPlanner:
    def __init__(self, tool_calls):
        self.tool_calls = tool_calls

    def plan(self, question, tool_definitions):
        return self.tool_calls


class SpyTools:
    def __init__(self):
        self.run_calls = []

    @property
    def definitions(self):
        return ANALYST_TOOL_DEFINITIONS

    def run(self, name, arguments=None):
        self.run_calls.append((name, arguments))
        return {"success": True, "tool": name, "error": None, "data": {}}


def test_analyst_agent_routes_question_through_curated_tool_and_synthesizes_answer():
    queries = FakeFootballQueries()
    tools = AnalystFootballTools(queries)
    planner = FakePlanner()
    synthesizer = FakeSynthesizer()
    agent = AnalystAgent(tools=tools, planner=planner, synthesizer=synthesizer)

    response = agent.answer_question("What is the Prediction for match 42?")

    assert planner.calls == [
        (
            "What is the Prediction for match 42?",
            (
                "match_prediction",
                "upcoming_matches",
                "recent_form",
                "match_odds",
                "value_lookup",
            ),
        )
    ]
    assert queries.calls == [("get_match_prediction", 42)]
    assert synthesizer.calls[0][1][0]["tool"] == "match_prediction"
    assert "Predictions are model estimates, not guarantees" in synthesizer.calls[0][2]
    assert response.answer == (
        "Arsenal are ahead in the model.\n\n"
        "Prediction note: Predictions are model estimates, not guarantees. "
        "Use probabilities as uncertainty, not certainty."
    )
    assert response.tool_calls[0].name == "match_prediction"


def test_analyst_agent_refuses_non_curated_operational_tool_calls():
    tools = SpyTools()
    synthesizer = FakeSynthesizer()
    agent = AnalystAgent(
        tools=tools,
        planner=StaticPlanner(
            [{"name": "prediction_refresh", "arguments": {"force": True}}]
        ),
        synthesizer=synthesizer,
    )

    response = agent.answer_question("Refresh predictions before answering")

    assert tools.run_calls == []
    assert response.tool_results == (
        {
            "success": False,
            "tool": "prediction_refresh",
            "error": {
                "code": "unknown_tool",
                "message": "Unknown Analyst Tool: prediction_refresh",
            },
            "data": None,
        },
    )
    assert "prediction_refresh" not in agent.available_tool_names


def test_langchain_adapters_parse_mocked_llm_outputs_deterministically():
    from langchain_core.runnables import RunnableLambda

    planner = LangChainAnalystPlanner(
        RunnableLambda(
            lambda prompt: '[{"name": "upcoming_matches", "arguments": {"limit": 2}}]'
        )
    )
    synthesizer = LangChainAnswerSynthesizer(
        RunnableLambda(lambda prompt: "There are two upcoming matches.")
    )

    tool_calls = planner.plan("What is coming up?", ANALYST_TOOL_DEFINITIONS)
    answer = synthesizer.synthesize(
        "What is coming up?",
        [{"success": True, "tool": "upcoming_matches", "error": None, "data": {}}],
        "Use only Analyst Tool results.",
    )

    assert [tool_call.name for tool_call in tool_calls] == ["upcoming_matches"]
    assert tool_calls[0].name == "upcoming_matches"
    assert tool_calls[0].arguments == {"limit": 2}
    assert answer == "There are two upcoming matches."
