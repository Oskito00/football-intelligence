"""Match detail and Feature Snapshot service."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol


MATCH_DETAIL_TITLE = "Match Detail"
FEATURE_SNAPSHOT_TITLE = "Feature Snapshot"
MISSING_PREDICTION_MESSAGE = "No Prediction is available for this match."
MISSING_ODDS_MESSAGE = "No odds context is available for this match."
MISSING_FEATURE_SNAPSHOT_MESSAGE = (
    "No Feature Snapshot inputs are available for this match."
)
FeatureMetricSpec = tuple[str, str]


class MatchDetailNotFound(LookupError):
    """Raised when a requested match cannot be found."""


class MatchDetailQueries(Protocol):
    """Read-only facts required to build match detail."""

    def get_match(self, match_id: int) -> dict[str, Any] | None:
        """Return one match by ID."""

    def get_match_prediction(self, match_id: int) -> dict[str, Any] | None:
        """Return the latest Prediction for one match."""

    def get_best_odds_for_match(self, match_id: int) -> dict[str, dict[str, Any]]:
        """Return best current odds by outcome for one match."""

    def get_feature_snapshot_facts(self, match_id: int) -> dict[str, Any]:
        """Return factual Future Feature Set inputs keyed by feature family."""


@dataclass(frozen=True)
class FeatureGroupSpec:
    """Display grouping for one Feature Snapshot fact family."""

    title: str
    family: str
    metrics: tuple[FeatureMetricSpec, ...]


FEATURE_GROUP_SPECS = (
    FeatureGroupSpec(
        title="Match Context",
        family="match_info",
        metrics=(("Competition Season", "competition_season"),),
    ),
    FeatureGroupSpec(
        title="Match Context",
        family="stage_of_season",
        metrics=(
            ("Stage Category", "stage_of_season_category"),
            ("Stage Of Season", "stage_of_season"),
        ),
    ),
    FeatureGroupSpec(
        title="Team Strength",
        family="team_strength",
        metrics=(
            ("Home Elo K40", "home_team_elo_K40"),
            ("Away Elo K40", "away_team_elo_K40"),
            ("Draw Parameter", "k_draw_parameter"),
            ("Home Advantage", "eta_home_advantage"),
        ),
    ),
    FeatureGroupSpec(
        title="Formation",
        family="formation",
        metrics=(
            ("Home Formation", "home_team_formation"),
            ("Away Formation", "away_team_formation"),
        ),
    ),
    FeatureGroupSpec(
        title="League Standings",
        family="league_standings",
        metrics=(
            ("Home Standing", "home_standing"),
            ("Home Points", "home_points"),
            ("Away Standing", "away_standing"),
            ("Away Points", "away_points"),
        ),
    ),
    FeatureGroupSpec(
        title="Head To Head",
        family="head_to_head",
        metrics=(
            ("Home Wins Last 10", "h2h_home_wins_last_10"),
            ("Draws Last 10", "h2h_draws_last_10"),
            ("Away Wins Last 10", "h2h_away_wins_last_10"),
            ("Average Total Goals", "h2h_avg_total_goals"),
        ),
    ),
    FeatureGroupSpec(
        title="Recent Form",
        family="form",
        metrics=(
            ("Home Team Form", "home_team_form"),
            ("Away Team Form", "away_team_form"),
            ("Draw Features", "draw_features"),
        ),
    ),
)


@dataclass(frozen=True)
class MatchDetail:
    """Structured match detail for API and dashboard consumers."""

    match: Mapping[str, Any]
    prediction: Mapping[str, Any] | None
    best_odds: Mapping[str, Mapping[str, Any]]
    feature_facts: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        prediction = _normalize_prediction(self.prediction)
        odds_context = _odds_context(self.best_odds)
        feature_snapshot = _feature_snapshot(
            self.feature_facts,
            market_context={
                "has_odds": odds_context["has_odds"],
                "best_prices": odds_context["best_prices"],
            },
        )
        warnings = _warnings(
            has_prediction=prediction is not None,
            has_odds=odds_context["has_odds"],
            has_feature_snapshot=feature_snapshot["available"],
        )

        return {
            "title": MATCH_DETAIL_TITLE,
            "match": _normalize_match(self.match),
            "prediction": prediction,
            "prediction_empty_state": (
                None if prediction else MISSING_PREDICTION_MESSAGE
            ),
            "odds_context": odds_context,
            "feature_snapshot": feature_snapshot,
            "warnings": warnings,
        }


class MatchDetailService:
    """Build match detail and Feature Snapshots from read-only football facts."""

    def __init__(self, queries: MatchDetailQueries):
        self._queries = queries

    @classmethod
    def from_config(cls) -> "MatchDetailService":
        """Build the default service from configured read-only database access."""
        from football_intelligence.database.football import ReadOnlyFootballQueries

        return cls(ReadOnlyFootballQueries.from_config())

    def get_match_detail(self, match_id: int) -> MatchDetail:
        """Return deterministic match detail for one match."""
        match = self._queries.get_match(match_id)
        if match is None:
            raise MatchDetailNotFound(f"Match {match_id} was not found")

        return MatchDetail(
            match=match,
            prediction=self._queries.get_match_prediction(match_id),
            best_odds=self._queries.get_best_odds_for_match(match_id),
            feature_facts=self._queries.get_feature_snapshot_facts(match_id),
        )


def _normalize_match(match: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "match_id": match["match_id"],
        "start_time": _isoformat(match.get("start_time")),
        "home_team": match["home_team"],
        "away_team": match["away_team"],
        "competition": match["competition"],
        "country": match["country"],
        "competition_id": match.get("competition_id"),
        "status": match.get("status"),
        "score": match.get("score"),
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


def _odds_context(best_odds: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    best_prices = [
        _best_price(outcome, best_odds[outcome])
        for outcome in _sorted_outcomes(best_odds.keys())
    ]
    return {
        "has_odds": bool(best_prices),
        "best_prices": best_prices,
        "empty_state": None if best_prices else MISSING_ODDS_MESSAGE,
    }


def _best_price(outcome: str, odds: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "outcome": outcome,
        "best_odds": _number_or_none(odds.get("odds_value")),
        "implied_probability": _number_or_none(odds.get("implied_probability")),
        "bookmaker": odds.get("bookmaker_name"),
        "retrieved_at": _isoformat(odds.get("retrieved_at")),
    }


def _feature_snapshot(
    feature_facts: Mapping[str, Any],
    *,
    market_context: Mapping[str, Any],
) -> dict[str, Any]:
    groups = _feature_groups(feature_facts)
    return {
        "title": FEATURE_SNAPSHOT_TITLE,
        "available": bool(groups),
        "groups": groups,
        "market_context": market_context,
        "empty_state": None if groups else MISSING_FEATURE_SNAPSHOT_MESSAGE,
    }


def _feature_groups(feature_facts: Mapping[str, Any]) -> list[dict[str, Any]]:
    merged: dict[str, list[dict[str, Any]]] = {}
    for spec in FEATURE_GROUP_SPECS:
        group = _group(spec.title, feature_facts.get(spec.family), spec.metrics)
        if not group:
            continue
        merged.setdefault(group["title"], []).extend(group["metrics"])

    return [
        {"title": title, "metrics": metrics}
        for title, metrics in merged.items()
        if metrics
    ]


def _group(
    title: str,
    source: Any,
    fields: tuple[tuple[str, str], ...],
) -> dict[str, Any] | None:
    if not isinstance(source, Mapping):
        return None

    metrics = [
        {"label": label, "value": _display_value(source.get(key))}
        for label, key in fields
        if source.get(key) is not None
    ]
    if not metrics:
        return None
    return {"title": title, "metrics": metrics}


def _warnings(
    *,
    has_prediction: bool,
    has_odds: bool,
    has_feature_snapshot: bool,
) -> list[dict[str, str]]:
    missing_states = (
        (not has_prediction, "missing_prediction", MISSING_PREDICTION_MESSAGE),
        (not has_odds, "missing_odds", MISSING_ODDS_MESSAGE),
        (
            not has_feature_snapshot,
            "missing_feature_snapshot",
            MISSING_FEATURE_SNAPSHOT_MESSAGE,
        ),
    )
    return [
        _warning(code, message)
        for missing, code, message in missing_states
        if missing
    ]


def _warning(code: str, message: str) -> dict[str, str]:
    return {
        "code": code,
        "severity": "warning",
        "message": message,
    }


def _sorted_outcomes(outcomes: Any) -> list[str]:
    preferred_order = {"Home Win": 0, "Draw": 1, "Away Win": 2}
    return sorted(
        outcomes,
        key=lambda outcome: (preferred_order.get(outcome, 99), outcome),
    )


def _display_value(value: Any) -> Any:
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return float(value)
    return value


def _number_or_none(value: Any) -> float | None:
    return float(value) if value is not None else None


def _isoformat(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)
