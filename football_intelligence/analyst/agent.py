"""Read-only Analyst Agent over curated football tools.

LangChain-facing orchestration lives here so deterministic football workflows
remain outside the agent layer.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from football_intelligence.analyst.tools import (
    AnalystFootballTools,
    AnalystToolDefinition,
    ToolResult,
)

PREDICTION_UNCERTAINTY_NOTE = (
    "Prediction note: Predictions are model estimates, not guarantees. "
    "Use probabilities as uncertainty, not certainty."
)
PREDICTION_TOOL_NAMES = {"match_prediction", "value_lookup"}

ANSWER_RULES = (
    "Answer the Natural-Language Football Question using only the supplied "
    "Analyst Tool results. Distinguish football facts from Predictions. "
    "Predictions are model estimates, not guarantees; communicate uncertainty "
    "with probabilities or confidence values when prediction data is used."
)


@dataclass(frozen=True)
class AnalystToolCall:
    """One planned call to a curated read-only Analyst Tool."""

    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class AnalystAgentResponse:
    """Answer and trace data produced by the read-only Analyst Agent."""

    question: str
    answer: str
    tool_calls: tuple[AnalystToolCall, ...]
    tool_results: tuple[ToolResult, ...]


class AnalystPlanner(Protocol):
    """Planner that maps a natural-language question to Analyst Tool calls."""

    def plan(
        self,
        question: str,
        tool_definitions: Sequence[AnalystToolDefinition],
    ) -> Sequence[AnalystToolCall | Mapping[str, Any]]:
        """Return requested read-only tool calls."""


class AnalystAnswerSynthesizer(Protocol):
    """Synthesizer that turns Analyst Tool results into a user answer."""

    def synthesize(
        self,
        question: str,
        tool_results: Sequence[ToolResult],
        answer_rules: str,
    ) -> str:
        """Return a natural-language answer."""


class AnalystAgent:
    """Read-only Analyst Agent for Natural-Language Football Questions."""

    def __init__(
        self,
        tools: AnalystFootballTools,
        planner: AnalystPlanner,
        synthesizer: AnalystAnswerSynthesizer,
    ):
        self._tools = tools
        self._planner = planner
        self._synthesizer = synthesizer

    @classmethod
    def from_config(cls, llm: Any) -> "AnalystAgent":
        """Build the default LangChain-backed Analyst Agent."""
        return cls(
            tools=AnalystFootballTools.from_config(),
            planner=LangChainAnalystPlanner(llm),
            synthesizer=LangChainAnswerSynthesizer(llm),
        )

    @property
    def tool_definitions(self) -> tuple[AnalystToolDefinition, ...]:
        """Return curated read-only Analyst Tool definitions."""
        return self._tools.definitions

    @property
    def available_tool_names(self) -> tuple[str, ...]:
        """Return the names of tools the agent is allowed to execute."""
        return tuple(definition.name for definition in self.tool_definitions)

    def answer_question(self, question: str) -> AnalystAgentResponse:
        """Answer one Natural-Language Football Question through Analyst Tools."""
        planned_calls = self._planner.plan(question, self.tool_definitions)
        tool_calls = tuple(_coerce_tool_call(call) for call in planned_calls)
        tool_results = tuple(self._run_curated_tool(call) for call in tool_calls)

        answer = self._synthesizer.synthesize(question, tool_results, ANSWER_RULES)
        answer = _ensure_prediction_uncertainty_note(answer, tool_results)

        return AnalystAgentResponse(
            question=question,
            answer=answer,
            tool_calls=tool_calls,
            tool_results=tool_results,
        )

    def _run_curated_tool(self, tool_call: AnalystToolCall) -> ToolResult:
        if tool_call.name not in self.available_tool_names:
            return _unknown_tool_result(tool_call.name)
        return self._tools.run(tool_call.name, tool_call.arguments)


class LangChainAnalystPlanner:
    """LangChain planner for selecting curated Analyst Tools."""

    def __init__(self, llm: Any):
        self._llm = llm
        self._prompt = _chat_prompt_template(
            [
                (
                    "system",
                    "Select read-only Analyst Tools for the football question. "
                    "Return only JSON: a list of objects with name and arguments.",
                ),
                (
                    "human",
                    "Question: {question}\n\nAvailable tools:\n{tool_definitions}",
                ),
            ]
        )

    def plan(
        self,
        question: str,
        tool_definitions: Sequence[AnalystToolDefinition],
    ) -> Sequence[AnalystToolCall]:
        prompt_input = {
            "question": question,
            "tool_definitions": _tool_definitions_json(tool_definitions),
        }
        raw_response = _invoke_langchain(self._prompt, self._llm, prompt_input)
        return _parse_planned_tool_calls(_message_content(raw_response))


class LangChainAnswerSynthesizer:
    """LangChain synthesizer for final Analyst Agent answers."""

    def __init__(self, llm: Any):
        self._llm = llm
        self._prompt = _chat_prompt_template(
            [
                ("system", "{answer_rules}"),
                (
                    "human",
                    "Question: {question}\n\nAnalyst Tool results:\n{tool_results}",
                ),
            ]
        )

    def synthesize(
        self,
        question: str,
        tool_results: Sequence[ToolResult],
        answer_rules: str,
    ) -> str:
        raw_response = _invoke_langchain(
            self._prompt,
            self._llm,
            {
                "question": question,
                "tool_results": json.dumps(list(tool_results), sort_keys=True),
                "answer_rules": answer_rules,
            },
        )
        return _message_content(raw_response)


def _coerce_tool_call(call: AnalystToolCall | Mapping[str, Any]) -> AnalystToolCall:
    if isinstance(call, AnalystToolCall):
        return call
    if not isinstance(call, Mapping):
        raise ValueError("Analyst tool call must be a mapping")

    name = call.get("name") or call.get("tool")
    arguments = call.get("arguments", call.get("args", {}))
    if not isinstance(name, str) or not name:
        raise ValueError("Analyst tool call must include a tool name")
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, Mapping):
        raise ValueError("Analyst tool call arguments must be a mapping")

    return AnalystToolCall(name=name, arguments=dict(arguments))


def _parse_planned_tool_calls(response_content: str) -> list[AnalystToolCall]:
    parsed_response = json.loads(response_content)
    if not isinstance(parsed_response, list):
        raise ValueError("Analyst Agent planner must return a JSON list")
    return [_coerce_tool_call(item) for item in parsed_response]


def _unknown_tool_result(tool_name: str) -> ToolResult:
    return {
        "success": False,
        "tool": tool_name,
        "error": {
            "code": "unknown_tool",
            "message": f"Unknown Analyst Tool: {tool_name}",
        },
        "data": None,
    }


def _ensure_prediction_uncertainty_note(
    answer: str,
    tool_results: Sequence[ToolResult],
) -> str:
    if not _uses_prediction_data(tool_results):
        return answer
    if PREDICTION_UNCERTAINTY_NOTE in answer:
        return answer
    return f"{answer}\n\n{PREDICTION_UNCERTAINTY_NOTE}"


def _uses_prediction_data(tool_results: Sequence[ToolResult]) -> bool:
    return any(
        result.get("success") and result.get("tool") in PREDICTION_TOOL_NAMES
        for result in tool_results
    )


def _tool_definitions_json(
    tool_definitions: Sequence[AnalystToolDefinition],
) -> str:
    return json.dumps(
        [
            {
                "name": definition.name,
                "description": definition.description,
                "input_schema": definition.input_schema,
            }
            for definition in tool_definitions
        ],
        sort_keys=True,
    )


def _chat_prompt_template(messages: Sequence[tuple[str, str]]) -> Any:
    try:
        from langchain_core.prompts import ChatPromptTemplate
    except ImportError as exc:
        raise ImportError(
            "LangChain is required for AnalystAgent.from_config(); install "
            "langchain-core to use the default agent adapters."
        ) from exc
    return ChatPromptTemplate.from_messages(list(messages))


def _invoke_langchain(prompt: Any, llm: Any, prompt_input: Mapping[str, Any]) -> Any:
    chain = prompt | llm
    return chain.invoke(dict(prompt_input))


def _message_content(response: Any) -> str:
    content = getattr(response, "content", response)
    return str(content)
