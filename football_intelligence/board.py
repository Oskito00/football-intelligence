"""Prediction Board service for today's remaining Upcoming Matches."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Any, Protocol


BOARD_TITLE = "Prediction Board"
EMPTY_BOARD_MESSAGE = (
    "No remaining Upcoming Matches are scheduled for today's local-date window."
)


class PredictionBoardQueries(Protocol):
    """Read-only facts required to build a Prediction Board."""

    def get_upcoming_matches_between(
        self,
        *,
        starts_at: datetime,
        ends_at: datetime,
    ) -> list[dict[str, Any]]:
        """Return Upcoming Matches between two local datetimes."""

    def get_multiple_match_predictions(
        self,
        match_ids: Sequence[int],
    ) -> dict[int, dict[str, Any]]:
        """Return latest Predictions keyed by match ID."""

    def get_odds_freshness_for_matches(
        self,
        match_ids: Sequence[int],
    ) -> dict[int, dict[str, Any]]:
        """Return odds freshness keyed by match ID."""

    def analyze_matches_for_value(self, match_ids: Sequence[int]) -> dict[str, Any]:
        """Return Market Value Signals for the supplied matches."""


@dataclass(frozen=True)
class PredictionBoard:
    """Structured board data for CLI, API, and dashboard consumers."""

    date: str
    generated_at: datetime
    starts_at: datetime
    ends_at: datetime
    matches: Sequence[Mapping[str, Any]]
    predictions: Mapping[int, Mapping[str, Any]]
    odds_freshness: Mapping[int, Mapping[str, Any]]
    value_signals: Sequence[Mapping[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Return deterministic API-ready Python values."""
        signals_by_match = _signals_by_match(self.value_signals)
        match_cards = []
        for match in self.matches:
            match_id = int(match["match_id"])
            match_cards.append(
                _match_card(
                    match,
                    prediction=self.predictions.get(match_id),
                    odds_freshness=self.odds_freshness.get(match_id),
                    value_signals=signals_by_match.get(match_id, []),
                )
            )

        return {
            "title": BOARD_TITLE,
            "date": self.date,
            "generated_at": _isoformat(self.generated_at),
            "window": {
                "starts_at": _isoformat(self.starts_at),
                "ends_at": _isoformat(self.ends_at),
                "timezone": "local",
            },
            "summary": _summary_for_match_cards(match_cards),
            "matches": match_cards,
            "warnings": _warnings_for_match_cards(match_cards),
            "empty_state": EMPTY_BOARD_MESSAGE if not match_cards else None,
        }


class PredictionBoardService:
    """Build Prediction Boards from read-only football facts."""

    def __init__(
        self,
        queries: PredictionBoardQueries,
        *,
        now_factory: Callable[[], datetime] | None = None,
    ):
        self._queries = queries
        self._now_factory = now_factory or datetime.now

    @classmethod
    def from_config(cls) -> "PredictionBoardService":
        """Build the default service from configured read-only database access."""
        from football_intelligence.database.football import ReadOnlyFootballQueries

        return cls(ReadOnlyFootballQueries.from_config())

    def today(self) -> PredictionBoard:
        """Return today's remaining local-date Prediction Board."""
        now = self._now_factory()
        date = now.date().isoformat()
        starts_at = now
        ends_at = datetime.combine(
            now.date() + timedelta(days=1),
            time.min,
            tzinfo=now.tzinfo,
        )
        matches = self._queries.get_upcoming_matches_between(
            starts_at=starts_at,
            ends_at=ends_at,
        )
        match_ids = [int(match["match_id"]) for match in matches]
        predictions: Mapping[int, Mapping[str, Any]] = {}
        odds_freshness: Mapping[int, Mapping[str, Any]] = {}
        value_signals: Sequence[Mapping[str, Any]] = []
        if match_ids:
            value_analysis = self._queries.analyze_matches_for_value(match_ids)
            predictions = self._queries.get_multiple_match_predictions(match_ids)
            odds_freshness = self._queries.get_odds_freshness_for_matches(match_ids)
            value_signals = value_analysis.get("all_value_bets", [])

        return PredictionBoard(
            date=date,
            generated_at=now,
            starts_at=starts_at,
            ends_at=ends_at,
            matches=matches,
            predictions=predictions,
            odds_freshness=odds_freshness,
            value_signals=value_signals,
        )


def _match_card(
    match: Mapping[str, Any],
    *,
    prediction: Mapping[str, Any] | None,
    odds_freshness: Mapping[str, Any] | None,
    value_signals: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "match_id": match["match_id"],
        "start_time": _isoformat(match.get("start_time")),
        "home_team": match["home_team"],
        "away_team": match["away_team"],
        "competition": match["competition"],
        "country": match["country"],
        "competition_id": match.get("competition_id"),
        "prediction": _normalize_prediction(prediction),
        "odds_freshness": _normalize_odds_freshness(odds_freshness),
        "market_value_signals": [
            _normalize_value_signal(signal) for signal in value_signals
        ],
    }


def _normalize_prediction(prediction: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not prediction:
        return None
    return {
        "predicted_result": prediction.get("predicted_result"),
        "confidence": _number_or_none(prediction.get("confidence")),
        "probabilities": {
            "home_win": _number_or_none(prediction.get("prob_home_win")),
            "draw": _number_or_none(prediction.get("prob_draw")),
            "away_win": _number_or_none(prediction.get("prob_away_win")),
        },
        "model_type": prediction.get("model_type"),
        "prediction_date": _isoformat(prediction.get("prediction_date")),
    }


def _normalize_odds_freshness(odds: Mapping[str, Any] | None) -> dict[str, Any]:
    odds = odds or {}
    return {
        "has_odds": bool(odds),
        "latest_retrieved_at": _isoformat(odds.get("latest_retrieved_at")),
        "latest_api_last_updated": _isoformat(odds.get("latest_api_last_updated")),
    }


def _normalize_value_signal(signal: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "outcome": signal.get("outcome"),
        "model_probability": _number_or_none(signal.get("model_probability")),
        "best_odds": _number_or_none(signal.get("odds_value")),
        "implied_probability": _number_or_none(signal.get("implied_probability")),
        "edge": _number_or_none(signal.get("expected_value")),
        "bookmaker": signal.get("bookmaker_name"),
        "paper_stake_percentage": _number_or_none(
            signal.get("recommended_bet_percentage")
        ),
    }


def _signals_by_match(
    value_signals: Sequence[Mapping[str, Any]],
) -> dict[int, list[Mapping[str, Any]]]:
    grouped: dict[int, list[Mapping[str, Any]]] = {}
    for signal in value_signals:
        match_id = signal.get("match_id")
        if match_id is None:
            continue
        grouped.setdefault(int(match_id), []).append(signal)
    return grouped


def _summary_for_match_cards(
    match_cards: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    return {
        "upcoming_match_count": len(match_cards),
        "matches_with_predictions": sum(
            1 for match in match_cards if match["prediction"] is not None
        ),
        "matches_with_odds": sum(
            1 for match in match_cards if match["odds_freshness"]["has_odds"]
        ),
        "market_value_signal_count": sum(
            len(match["market_value_signals"]) for match in match_cards
        ),
    }


def _warnings_for_match_cards(
    match_cards: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    warnings = []
    if any(match["prediction"] is None for match in match_cards):
        warnings.append(
            _warning(
                "missing_predictions",
                "Some Upcoming Matches do not have Predictions.",
            )
        )
    if any(not match["odds_freshness"]["has_odds"] for match in match_cards):
        warnings.append(
            _warning(
                "missing_odds",
                "Some Upcoming Matches do not have odds freshness.",
            )
        )
    return warnings


def _warning(code: str, message: str) -> dict[str, str]:
    return {
        "code": code,
        "severity": "warning",
        "message": message,
    }


def _number_or_none(value: Any) -> float | None:
    return float(value) if value is not None else None


def _isoformat(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)
