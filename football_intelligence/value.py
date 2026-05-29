"""Market Value Signal scanning for upcoming football matches."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Any, Protocol


VALUE_SIGNALS_TITLE = "Market Value Signals"
EMPTY_VALUE_SIGNALS_MESSAGE = "No Market Value Signals found for this window."
DEFAULT_SIGNAL_DAYS = 7


class MarketValueSignalQueries(Protocol):
    """Read-only facts required to scan Market Value Signals."""

    def get_upcoming_matches_between(
        self,
        *,
        starts_at: datetime,
        ends_at: datetime,
    ) -> list[dict[str, Any]]:
        """Return Upcoming Matches between two local datetimes."""

    def analyze_matches_for_value(self, match_ids: Sequence[int]) -> dict[str, Any]:
        """Return model-vs-market value analysis for the supplied matches."""


@dataclass(frozen=True)
class MarketValueSignalScan:
    """Structured Market Value Signal data for CLI, API, and dashboard consumers."""

    generated_at: datetime
    starts_at: datetime
    ends_at: datetime
    label: str
    matches: Sequence[Mapping[str, Any]]
    analysis: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        signals = _normalized_signals(
            self.analysis.get("all_value_bets", []),
            matches_by_id=_matches_by_id(self.matches),
        )
        return {
            "title": VALUE_SIGNALS_TITLE,
            "generated_at": _isoformat(self.generated_at),
            "window": {
                "starts_at": _isoformat(self.starts_at),
                "ends_at": _isoformat(self.ends_at),
                "timezone": "local",
                "label": self.label,
            },
            "summary": {
                "upcoming_match_count": len(self.matches),
                "matches_with_predictions": _int_value(
                    self.analysis.get("matches_with_predictions")
                ),
                "matches_with_odds": _int_value(self.analysis.get("matches_with_odds")),
                "matches_with_value_signals": _int_value(
                    self.analysis.get("matches_with_value_bets")
                ),
                "market_value_signal_count": len(signals),
            },
            "signals": signals,
            "warnings": [],
            "empty_state": EMPTY_VALUE_SIGNALS_MESSAGE if not signals else None,
        }


class MarketValueSignalService:
    """Scan Upcoming Matches for first-class Market Value Signals."""

    def __init__(
        self,
        queries: MarketValueSignalQueries,
        *,
        now_factory: Callable[[], datetime] | None = None,
    ):
        self._queries = queries
        self._now_factory = now_factory or datetime.now

    @classmethod
    def from_config(cls) -> "MarketValueSignalService":
        """Build the default service from configured read-only database access."""
        from football_intelligence.database.football import ReadOnlyFootballQueries

        return cls(ReadOnlyFootballQueries.from_config())

    def today(self) -> MarketValueSignalScan:
        """Scan today's remaining local-date window."""
        now = self._now_factory()
        ends_at = datetime.combine(
            now.date() + timedelta(days=1),
            time.min,
            tzinfo=now.tzinfo,
        )
        return self._scan(starts_at=now, ends_at=ends_at, label="today")

    def next_days(self, *, days: int = DEFAULT_SIGNAL_DAYS) -> MarketValueSignalScan:
        """Scan the next N days for Market Value Signals."""
        if days < 1:
            raise ValueError("--days must be greater than 0")

        now = self._now_factory()
        return self._scan(
            starts_at=now,
            ends_at=now + timedelta(days=days),
            label=f"next_{days}_days",
        )

    def _scan(
        self,
        *,
        starts_at: datetime,
        ends_at: datetime,
        label: str,
    ) -> MarketValueSignalScan:
        matches = self._queries.get_upcoming_matches_between(
            starts_at=starts_at,
            ends_at=ends_at,
        )
        match_ids = [int(match["match_id"]) for match in matches]
        analysis: Mapping[str, Any]
        if match_ids:
            analysis = self._queries.analyze_matches_for_value(match_ids)
        else:
            analysis = {
                "matches_with_predictions": 0,
                "matches_with_odds": 0,
                "matches_with_value_bets": 0,
                "all_value_bets": [],
            }

        return MarketValueSignalScan(
            generated_at=starts_at,
            starts_at=starts_at,
            ends_at=ends_at,
            label=label,
            matches=matches,
            analysis=analysis,
        )


def _normalized_signals(
    signals: Sequence[Mapping[str, Any]],
    *,
    matches_by_id: Mapping[int, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    normalized = []
    for signal in signals:
        match_id = signal.get("match_id")
        match = matches_by_id.get(int(match_id)) if match_id is not None else None
        normalized.append(_normalized_signal(signal, match=match))
    return normalized


def _normalized_signal(
    signal: Mapping[str, Any],
    *,
    match: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "match_id": signal.get("match_id"),
        "start_time": _isoformat(_first_present(match, signal, "start_time")),
        "home_team": _first_present(match, signal, "home_team"),
        "away_team": _first_present(match, signal, "away_team"),
        "competition": _first_present(match, signal, "competition"),
        "country": _first_present(match, signal, "country"),
        "outcome": signal.get("outcome"),
        "model_probability": _number_or_none(signal.get("model_probability")),
        "best_odds": _number_or_none(signal.get("odds_value")),
        "implied_probability": _number_or_none(signal.get("implied_probability")),
        "edge": _number_or_none(signal.get("expected_value")),
        "bookmaker": signal.get("bookmaker_name"),
        "paper_stake_percentage": _number_or_none(
            signal.get("recommended_bet_percentage")
        ),
        "prediction_date": _isoformat(signal.get("prediction_date")),
    }


def _matches_by_id(
    matches: Sequence[Mapping[str, Any]],
) -> dict[int, Mapping[str, Any]]:
    return {int(match["match_id"]): match for match in matches}


def _first_present(
    first: Mapping[str, Any] | None,
    second: Mapping[str, Any],
    key: str,
) -> Any:
    if first is not None and first.get(key) is not None:
        return first.get(key)
    return second.get(key)


def _int_value(value: Any) -> int:
    return int(value or 0)


def _number_or_none(value: Any) -> float | None:
    return float(value) if value is not None else None


def _isoformat(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)
