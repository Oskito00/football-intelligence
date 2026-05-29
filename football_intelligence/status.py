"""Football Data Status service for read-only data readiness facts."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol


DEFAULT_STATUS_DAYS = 7
DEFAULT_ODDS_STALE_AFTER_HOURS = 24
DEFAULT_TOP_TEAM_LIMIT = 5
DEFAULT_ELO_COMPETITION = "Premier League"
DEFAULT_ELO_COUNTRY = "England"


class FootballDataStatusQueries(Protocol):
    """Read-only facts required to build Football Data Status."""

    def get_football_data_status_facts(
        self,
        *,
        days: int = DEFAULT_STATUS_DAYS,
        top_team_limit: int = DEFAULT_TOP_TEAM_LIMIT,
        elo_competition: str = DEFAULT_ELO_COMPETITION,
        elo_country: str = DEFAULT_ELO_COUNTRY,
    ) -> dict[str, Any]:
        """Return football-data readiness facts from storage."""


@dataclass(frozen=True)
class FootballDataStatus:
    """Structured status facts and warnings for dashboard/API/CLI callers."""

    latest_completed_match: Mapping[str, Any] | None
    unprocessed_completed_matches: int
    latest_elo_history_date: Any
    future_feature_set_count: int
    prediction_count_next_7_days: int
    odds_freshness: Mapping[str, Any]
    top_premier_league_elo_teams: Sequence[Mapping[str, Any]]
    warnings: Sequence[Mapping[str, str]]

    def to_dict(self) -> dict[str, Any]:
        """Return deterministic API-ready Python values."""
        return {
            "title": "Football Data Status",
            "latest_completed_match": _normalize_completed_match(
                self.latest_completed_match
            ),
            "unprocessed_completed_matches": self.unprocessed_completed_matches,
            "latest_elo_history_date": _isoformat(self.latest_elo_history_date),
            "future_feature_set_count": self.future_feature_set_count,
            "prediction_count_next_7_days": self.prediction_count_next_7_days,
            "odds_freshness": _normalize_odds_freshness(self.odds_freshness),
            "top_premier_league_elo_teams": [
                _normalize_elo_team(team)
                for team in self.top_premier_league_elo_teams
            ],
            "warnings": [dict(warning) for warning in self.warnings],
        }


class FootballDataStatusService:
    """Build Football Data Status from read-only data facts."""

    def __init__(
        self,
        queries: FootballDataStatusQueries,
        *,
        now_factory: Callable[[], datetime] | None = None,
        odds_stale_after: timedelta | None = None,
    ):
        self._queries = queries
        self._now_factory = now_factory or datetime.now
        self._odds_stale_after = odds_stale_after or timedelta(
            hours=DEFAULT_ODDS_STALE_AFTER_HOURS
        )

    @classmethod
    def from_config(cls) -> "FootballDataStatusService":
        """Build the default service from configured read-only database access."""
        from football_intelligence.database.football import ReadOnlyFootballQueries

        return cls(ReadOnlyFootballQueries.from_config())

    def get_status(self) -> FootballDataStatus:
        """Return status facts and warnings without collapsing them into a score."""
        facts = self._queries.get_football_data_status_facts(
            days=DEFAULT_STATUS_DAYS,
            top_team_limit=DEFAULT_TOP_TEAM_LIMIT,
            elo_competition=DEFAULT_ELO_COMPETITION,
            elo_country=DEFAULT_ELO_COUNTRY,
        )
        warnings = _derive_warnings(
            facts,
            now=self._now_factory(),
            odds_stale_after=self._odds_stale_after,
        )
        return FootballDataStatus(
            latest_completed_match=facts.get("latest_completed_match"),
            unprocessed_completed_matches=int(
                facts.get("unprocessed_completed_matches") or 0
            ),
            latest_elo_history_date=facts.get("latest_elo_history_date"),
            future_feature_set_count=int(facts.get("future_feature_set_count") or 0),
            prediction_count_next_7_days=int(
                facts.get("prediction_count_next_7_days") or 0
            ),
            odds_freshness=facts.get("odds_freshness") or {},
            top_premier_league_elo_teams=facts.get(
                "top_premier_league_elo_teams"
            )
            or [],
            warnings=warnings,
        )


def _derive_warnings(
    facts: Mapping[str, Any],
    *,
    now: datetime,
    odds_stale_after: timedelta,
) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []

    if not facts.get("latest_completed_match"):
        warnings.append(
            _warning(
                "missing_latest_completed_match",
                "No latest Completed Match is available.",
            )
        )

    unprocessed = int(facts.get("unprocessed_completed_matches") or 0)
    if unprocessed > 0:
        warnings.append(
            _warning(
                "unprocessed_completed_matches",
                (
                    f"{unprocessed} Completed Matches have not been incorporated "
                    "into the Historical Feature Set."
                ),
            )
        )

    if not facts.get("latest_elo_history_date"):
        warnings.append(
            _warning(
                "missing_latest_elo_history",
                "No latest Elo history date is available.",
            )
        )

    if int(facts.get("future_feature_set_count") or 0) == 0:
        warnings.append(
            _warning(
                "missing_future_feature_set",
                "No Future Feature Set rows are available for the next 7 days.",
            )
        )

    if int(facts.get("prediction_count_next_7_days") or 0) == 0:
        warnings.append(
            _warning(
                "missing_predictions",
                "No Predictions are available for the next 7 days.",
            )
        )

    odds_freshness = facts.get("odds_freshness") or {}
    latest_odds = odds_freshness.get("latest_retrieved_at")
    if latest_odds is None:
        warnings.append(_warning("missing_odds", "No odds freshness is available."))
    elif now - _as_naive_datetime(latest_odds) > odds_stale_after:
        warnings.append(
            _warning(
                "stale_odds",
                (
                    "Odds freshness is older than "
                    f"{int(odds_stale_after.total_seconds() // 3600)} hours."
                ),
            )
        )

    if not facts.get("top_premier_league_elo_teams"):
        warnings.append(
            _warning(
                "missing_premier_league_elo_teams",
                "No top Premier League Elo teams are available.",
            )
        )

    return warnings


def _warning(code: str, message: str) -> dict[str, str]:
    return {
        "code": code,
        "severity": "warning",
        "message": message,
    }


def _normalize_completed_match(match: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not match:
        return None
    return {
        "match_id": match.get("match_id"),
        "start_time": _isoformat(match.get("start_time")),
        "home_team": match.get("home_team"),
        "away_team": match.get("away_team"),
        "competition": match.get("competition"),
        "country": match.get("country"),
        "score": match.get("score"),
    }


def _normalize_odds_freshness(odds: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "latest_retrieved_at": _isoformat(odds.get("latest_retrieved_at")),
        "latest_api_last_updated": _isoformat(odds.get("latest_api_last_updated")),
        "matches_with_odds_next_7_days": int(
            odds.get("matches_with_odds_next_7_days") or 0
        ),
        "stale_after_hours": DEFAULT_ODDS_STALE_AFTER_HOURS,
    }


def _normalize_elo_team(team: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "team_id": team.get("team_id"),
        "team_name": team.get("team_name"),
        "elo": int(team["elo"]) if team.get("elo") is not None else None,
        "competition": team.get("competition"),
        "country": team.get("country"),
    }


def _isoformat(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _as_naive_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.replace(tzinfo=None)
        return value
    return datetime.fromisoformat(str(value))
