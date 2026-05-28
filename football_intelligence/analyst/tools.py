"""Curated read-only Analyst Tools for football questions.

The Analyst Agent should call this module instead of arbitrary SQL or retired
implementation-era functions. Each tool returns the same stable result envelope:

``{"success": bool, "tool": str, "error": dict | None, "data": object | None}``
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Protocol

from football_intelligence.database import FootballQueryError, ReadOnlyFootballQueries

ToolResult = dict[str, Any]


class FootballQueryService(Protocol):
    """Read-only football query capabilities used by Analyst Tools."""

    def get_match_prediction(self, match_id: int) -> dict[str, Any] | None:
        """Return one Prediction for a match."""

    def get_upcoming_matches(
        self,
        days_ahead: int = 7,
        competition_ids: Sequence[int] | None = None,
        country: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return Upcoming Matches."""

    def get_recent_form(
        self,
        team_id: int,
        last_n_matches: int = 10,
        competition_id: int | str | None = None,
        at_home: bool | None = None,
    ) -> dict[str, Any]:
        """Return recent Completed Match form."""

    def get_best_odds_for_match(
        self,
        match_id: int,
        bet_type_id: int = 1,
    ) -> dict[str, dict[str, Any]]:
        """Return best odds by outcome for one match."""

    def get_latest_match_odds(
        self,
        match_id: int,
        bet_type_id: int = 1,
    ) -> dict[str, list[dict[str, Any]]]:
        """Return latest all-bookmaker odds by outcome for one match."""

    def analyze_matches_for_value(
        self,
        match_ids: Sequence[int],
        kelly_fraction: float = 0.50,
        min_value_threshold: float = 0.05,
    ) -> dict[str, Any]:
        """Return model-vs-odds value analysis."""


@dataclass(frozen=True)
class AnalystToolDefinition:
    """LLM-facing metadata for one read-only Analyst Tool."""

    name: str
    description: str
    input_schema: dict[str, Any]


ANALYST_TOOL_DEFINITIONS: tuple[AnalystToolDefinition, ...] = (
    AnalystToolDefinition(
        name="match_prediction",
        description="Get the latest model Prediction for a known match ID.",
        input_schema={
            "type": "object",
            "properties": {"match_id": {"type": "integer", "minimum": 1}},
            "required": ["match_id"],
        },
    ),
    AnalystToolDefinition(
        name="upcoming_matches",
        description="List Upcoming Matches with optional competition and country filters.",
        input_schema={
            "type": "object",
            "properties": {
                "days_ahead": {"type": "integer", "minimum": 1, "default": 7},
                "competition_ids": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 1},
                },
                "country": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1},
            },
        },
    ),
    AnalystToolDefinition(
        name="recent_form",
        description="Analyze a team's recent Completed Match form by team ID.",
        input_schema={
            "type": "object",
            "properties": {
                "team_id": {"type": "integer", "minimum": 1},
                "last_n_matches": {"type": "integer", "minimum": 1, "default": 10},
                "competition_id": {"type": ["integer", "string"]},
                "at_home": {"type": ["boolean", "null"]},
            },
            "required": ["team_id"],
        },
    ),
    AnalystToolDefinition(
        name="match_odds",
        description="Get current match-result odds for a known match ID.",
        input_schema={
            "type": "object",
            "properties": {
                "match_id": {"type": "integer", "minimum": 1},
                "bet_type_id": {"type": "integer", "minimum": 1, "default": 1},
                "include_all_bookmakers": {"type": "boolean", "default": False},
            },
            "required": ["match_id"],
        },
    ),
    AnalystToolDefinition(
        name="value_lookup",
        description="Compare model probabilities with odds to find value opportunities.",
        input_schema={
            "type": "object",
            "properties": {
                "match_ids": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 1},
                    "minItems": 1,
                },
                "kelly_fraction": {"type": "number", "default": 0.50},
                "min_value_threshold": {"type": "number", "default": 0.05},
            },
            "required": ["match_ids"],
        },
    ),
)


class AnalystFootballTools:
    """Stable read-only Analyst Tool interface over football query modules."""

    def __init__(self, queries: FootballQueryService):
        self._queries = queries
        self._handlers = {
            "match_prediction": self.get_match_prediction,
            "upcoming_matches": self.get_upcoming_matches,
            "recent_form": self.get_recent_form,
            "match_odds": self.get_match_odds,
            "value_lookup": self.get_value_lookup,
        }

    @classmethod
    def from_config(cls) -> "AnalystFootballTools":
        """Build Analyst Tools from the configured read-only football queries."""
        return cls(ReadOnlyFootballQueries.from_config())

    @property
    def definitions(self) -> tuple[AnalystToolDefinition, ...]:
        """Return the available read-only Analyst Tool definitions."""
        return ANALYST_TOOL_DEFINITIONS

    def run(self, name: str, arguments: Mapping[str, Any] | None = None) -> ToolResult:
        """Run one Analyst Tool by name with mapping arguments."""
        handler = self._handlers.get(name)
        if handler is None:
            return _failure(
                name,
                "unknown_tool",
                f"Unknown Analyst Tool: {name}",
            )

        try:
            return handler(**dict(arguments or {}))
        except (TypeError, ValueError) as exc:
            return _failure(name, "invalid_input", str(exc))

    def get_match_prediction(self, match_id: int) -> ToolResult:
        """Get the latest Prediction for one match."""
        tool = "match_prediction"
        try:
            normalized_match_id = int(match_id)
            prediction = self._queries.get_match_prediction(normalized_match_id)
        except FootballQueryError as exc:
            return _failure(tool, "backend_error", str(exc))
        except (TypeError, ValueError) as exc:
            return _failure(tool, "invalid_input", str(exc))

        if prediction is None:
            return _failure(
                tool,
                "not_found",
                f"No prediction found for match {match_id}",
            )
        return _success(tool, prediction)

    def get_upcoming_matches(
        self,
        days_ahead: int = 7,
        competition_ids: Sequence[int] | None = None,
        country: str | None = None,
        limit: int | None = None,
    ) -> ToolResult:
        """List Upcoming Matches for the requested filters."""
        tool = "upcoming_matches"
        try:
            normalized_days_ahead = int(days_ahead)
            normalized_competition_ids = (
                [int(competition_id) for competition_id in competition_ids]
                if competition_ids
                else None
            )
            normalized_limit = int(limit) if limit is not None else None
            matches = self._queries.get_upcoming_matches(
                days_ahead=normalized_days_ahead,
                competition_ids=normalized_competition_ids,
                country=country,
                limit=normalized_limit,
            )
        except FootballQueryError as exc:
            return _failure(tool, "backend_error", str(exc))
        except (TypeError, ValueError) as exc:
            return _failure(tool, "invalid_input", str(exc))

        return _success(
            tool,
            {
                "filters": {
                    "days_ahead": normalized_days_ahead,
                    "competition_ids": normalized_competition_ids,
                    "country": country,
                    "limit": normalized_limit,
                },
                "summary": {"matches_returned": len(matches)},
                "matches": matches,
            },
        )

    def get_recent_form(
        self,
        team_id: int,
        last_n_matches: int = 10,
        competition_id: int | str | None = None,
        at_home: bool | None = None,
    ) -> ToolResult:
        """Analyze recent Completed Match form for a team."""
        tool = "recent_form"
        try:
            normalized_team_id = int(team_id)
            normalized_last_n_matches = int(last_n_matches)
            result = self._queries.get_recent_form(
                team_id=normalized_team_id,
                last_n_matches=normalized_last_n_matches,
                competition_id=competition_id,
                at_home=at_home,
            )
        except FootballQueryError as exc:
            return _failure(tool, "backend_error", str(exc))
        except (TypeError, ValueError) as exc:
            return _failure(tool, "invalid_input", str(exc))

        if not result.get("success"):
            return _failure(tool, "not_found", result.get("error") or "No form found")
        return _success(tool, result.get("data"))

    def get_match_odds(
        self,
        match_id: int,
        bet_type_id: int = 1,
        include_all_bookmakers: bool = False,
    ) -> ToolResult:
        """Get match-result odds for one match."""
        tool = "match_odds"
        try:
            normalized_match_id = int(match_id)
            normalized_bet_type_id = int(bet_type_id)
            if include_all_bookmakers:
                odds = self._queries.get_latest_match_odds(
                    normalized_match_id,
                    bet_type_id=normalized_bet_type_id,
                )
            else:
                odds = self._queries.get_best_odds_for_match(
                    normalized_match_id,
                    bet_type_id=normalized_bet_type_id,
                )
        except FootballQueryError as exc:
            return _failure(tool, "backend_error", str(exc))
        except (TypeError, ValueError) as exc:
            return _failure(tool, "invalid_input", str(exc))

        if not odds:
            return _failure(tool, "not_found", f"No odds found for match {match_id}")
        return _success(
            tool,
            {
                "match_id": normalized_match_id,
                "bet_type_id": normalized_bet_type_id,
                "include_all_bookmakers": bool(include_all_bookmakers),
                "odds": odds,
            },
        )

    def get_value_lookup(
        self,
        match_ids: Sequence[int],
        kelly_fraction: float = 0.50,
        min_value_threshold: float = 0.05,
    ) -> ToolResult:
        """Find value opportunities across known match IDs."""
        tool = "value_lookup"
        try:
            if isinstance(match_ids, (str, bytes, bytearray)):
                raise ValueError("match_ids must be a sequence of match IDs")
            normalized_match_ids = [int(match_id) for match_id in match_ids]
            if not normalized_match_ids:
                raise ValueError("match_ids must contain at least one match ID")
            analysis = self._queries.analyze_matches_for_value(
                normalized_match_ids,
                kelly_fraction=float(kelly_fraction),
                min_value_threshold=float(min_value_threshold),
            )
        except FootballQueryError as exc:
            return _failure(tool, "backend_error", str(exc))
        except (TypeError, ValueError) as exc:
            return _failure(tool, "invalid_input", str(exc))

        return _success(tool, analysis)


def _success(tool: str, data: Any) -> ToolResult:
    return {
        "success": True,
        "tool": tool,
        "error": None,
        "data": _agent_safe_value(data),
    }


def _failure(tool: str, code: str, message: str) -> ToolResult:
    return {
        "success": False,
        "tool": tool,
        "error": {"code": code, "message": message},
        "data": None,
    }


def _agent_safe_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _agent_safe_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_agent_safe_value(item) for item in value]
    return value
