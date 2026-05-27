"""Read-only football query interfaces for Analyst Tool consumers.

The public methods in this module intentionally return legacy-compatible
Python dictionaries while hiding SQL and connection handling behind an
injectable read-only runner. These contracts are stable for Analyst Tools:

- ``get_match_prediction`` returns one Prediction dictionary or ``None``.
- ``get_multiple_match_predictions`` returns ``{match_id: prediction}``.
- ``get_upcoming_matches`` returns a list of Upcoming Match dictionaries.
- ``get_recent_form`` returns ``{"success", "error", "data"}``.
- ``get_best_odds_for_multiple_matches`` returns ``{match_id: odds_by_outcome}``.
- ``analyze_matches_for_value`` returns a value-bet analysis dictionary.

Database failures raise ``FootballQueryError`` so callers can distinguish
backend errors from valid no-result lookups.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

Row = Mapping[str, Any]
Prediction = dict[str, Any]
OddsByOutcome = dict[str, dict[str, Any]]
AllBookmakerOddsByOutcome = dict[str, list[dict[str, Any]]]

PREDICTED_RESULT_LABELS = {2: "Home Win", 1: "Draw", 0: "Away Win"}
PROBABILITY_OUTCOMES = (
    ("prob_home_win", "Home Win"),
    ("prob_draw", "Draw"),
    ("prob_away_win", "Away Win"),
)
RECENT_MATCH_LIMIT = 5


class FootballQueryError(RuntimeError):
    """Raised when a read-only football query cannot be completed."""


class ReadOnlyQueryRunner(Protocol):
    """Small DB-API boundary used by the football query module."""

    def fetch_one(self, query: str, params: Sequence[Any] = ()) -> Row | None:
        """Run a read-only query and return one mapping row."""

    def fetch_all(self, query: str, params: Sequence[Any] = ()) -> list[Row]:
        """Run a read-only query and return mapping rows."""


@dataclass(frozen=True)
class PostgresReadOnlyRunner:
    """Read-only PostgreSQL runner for football query modules."""

    connection_factory: Callable[[], Any]

    def fetch_one(self, query: str, params: Sequence[Any] = ()) -> Row | None:
        rows = self.fetch_all(query, params)
        return rows[0] if rows else None

    def fetch_all(self, query: str, params: Sequence[Any] = ()) -> list[Row]:
        _ensure_read_only_query(query)
        conn = self.connection_factory()
        try:
            cursor = conn.cursor()
            try:
                cursor.execute(query, tuple(params))
                return list(cursor.fetchall())
            finally:
                cursor.close()
        finally:
            conn.close()


class ReadOnlyFootballQueries:
    """Read-only football lookups for predictions, matches, form, odds, and value."""

    def __init__(self, runner: ReadOnlyQueryRunner):
        self._runner = runner

    @classmethod
    def from_config(cls) -> "ReadOnlyFootballQueries":
        """Build queries from the repo's PostgreSQL configuration."""
        from config import get_config
        import psycopg2
        from psycopg2.extras import RealDictCursor

        config = get_config()

        def connect():
            return psycopg2.connect(
                host=config.DB_HOST,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                port=getattr(config, "DB_PORT", 5432),
                cursor_factory=RealDictCursor,
            )

        return cls(PostgresReadOnlyRunner(connect))

    def get_match_prediction(self, match_id: int) -> Prediction | None:
        """Return the latest Prediction for one match, or ``None`` when absent."""
        query = """
            SELECT
                match_id,
                predicted_result,
                home_team_name,
                away_team_name,
                prob_home_win,
                prob_draw,
                prob_away_win,
                model_type,
                prediction_timestamp
            FROM match_result_predictions
            WHERE match_id = %s
            ORDER BY prediction_timestamp DESC
            LIMIT 1
        """
        try:
            row = self._runner.fetch_one(query, (match_id,))
        except Exception as exc:
            raise FootballQueryError(
                f"Error getting prediction for match {match_id}: {exc}"
            ) from exc

        return _map_prediction(row) if row else None

    def get_multiple_match_predictions(
        self,
        match_ids: Sequence[int],
    ) -> dict[int, Prediction]:
        """Return latest Predictions keyed by match ID."""
        if not match_ids:
            return {}

        placeholders = _placeholders(match_ids)
        query = f"""
            SELECT
                match_id,
                predicted_result,
                home_team_name,
                away_team_name,
                prob_home_win,
                prob_draw,
                prob_away_win,
                model_type,
                prediction_timestamp
            FROM match_result_predictions
            WHERE match_id IN ({placeholders})
            ORDER BY match_id, prediction_timestamp DESC
        """
        try:
            rows = self._runner.fetch_all(query, tuple(match_ids))
        except Exception as exc:
            raise FootballQueryError(f"Error getting predictions: {exc}") from exc

        predictions: dict[int, Prediction] = {}
        for row in rows:
            match_id = int(row["match_id"])
            if match_id not in predictions:
                predictions[match_id] = _map_prediction(row)
        return predictions

    def get_upcoming_matches(
        self,
        days_ahead: int = 7,
        competition_ids: Sequence[int] | None = None,
        country: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return Upcoming Matches in the requested window."""
        days_ahead = int(days_ahead)
        if days_ahead < 1:
            raise ValueError("days_ahead must be greater than 0")
        if limit is not None and int(limit) < 1:
            raise ValueError("limit must be greater than 0")

        conditions = [
            "match_status = 'NS'",
            "start_time >= CURRENT_TIMESTAMP",
            "start_time <= CURRENT_TIMESTAMP + (%s * INTERVAL '1 day')",
            "home_team_name IS NOT NULL",
            "away_team_name IS NOT NULL",
        ]
        params: list[Any] = [days_ahead]

        if competition_ids:
            conditions.append(f"competition_id IN ({_placeholders(competition_ids)})")
            params.extend(competition_ids)
        if country:
            conditions.append("competition_country ILIKE %s")
            params.append(f"%{country}%")

        limit_clause = ""
        if limit is not None:
            limit_clause = "LIMIT %s"
            params.append(int(limit))

        query = f"""
            SELECT
                match_id,
                start_time,
                home_team_name,
                away_team_name,
                competition_name,
                competition_country,
                competition_id
            FROM matches
            WHERE {' AND '.join(conditions)}
            ORDER BY start_time ASC
            {limit_clause}
        """
        try:
            rows = self._runner.fetch_all(query, tuple(params))
        except Exception as exc:
            raise FootballQueryError(f"Error getting upcoming matches: {exc}") from exc

        return [_map_upcoming_match(row) for row in rows]

    def get_recent_form(
        self,
        team_id: int,
        last_n_matches: int = 10,
        competition_id: int | str | None = None,
        at_home: bool | None = None,
    ) -> dict[str, Any]:
        """Return recent completed-match form analysis for a team."""
        last_n_matches = int(last_n_matches)
        if last_n_matches < 1:
            raise ValueError("last_n_matches must be greater than 0")

        side_filter, params = _recent_form_side_filter(team_id, at_home)

        competition_filter = ""
        if competition_id:
            competition_filter = "AND m.competition_id = %s"
            params.append(competition_id)

        params.append(last_n_matches)
        query = f"""
            SELECT
                m.match_id,
                m.start_time,
                m.home_team_name,
                m.away_team_name,
                m.home_score,
                m.away_score,
                m.competition_name,
                m.competition_id,
                CASE WHEN m.home_team_id = %s THEN 'home' ELSE 'away' END AS team_side
            FROM matches m
            WHERE m.home_score IS NOT NULL
            AND m.away_score IS NOT NULL
            {side_filter}
            {competition_filter}
            ORDER BY m.start_time DESC
            LIMIT %s
        """
        query_params = [team_id, *params]
        try:
            rows = self._runner.fetch_all(query, tuple(query_params))
        except Exception as exc:
            raise FootballQueryError(f"Error getting recent form: {exc}") from exc

        if not rows:
            return {
                "success": False,
                "error": f"No matches found for team ID {team_id}",
                "data": None,
            }
        return _map_recent_form(
            rows,
            team_id=team_id,
            last_n_matches=last_n_matches,
            competition_id=competition_id,
            at_home=at_home,
        )

    def get_best_odds_for_match(
        self,
        match_id: int,
        bet_type_id: int = 1,
    ) -> OddsByOutcome:
        """Return best current odds by outcome for one match."""
        return self.get_best_odds_for_multiple_matches([match_id], bet_type_id).get(
            match_id,
            {},
        )

    def get_best_odds_for_multiple_matches(
        self,
        match_ids: Sequence[int],
        bet_type_id: int = 1,
    ) -> dict[int, OddsByOutcome]:
        """Return best current odds keyed by match ID and outcome."""
        rows = self._fetch_latest_odds_rows(match_ids, bet_type_id)
        return _get_best_odds_from_rows(rows)

    def get_latest_match_odds(
        self,
        match_id: int,
        bet_type_id: int = 1,
    ) -> AllBookmakerOddsByOutcome:
        """Return latest odds from all bookmakers grouped by outcome."""
        return self.get_odds_for_multiple_matches(
            [match_id],
            bet_type_id=bet_type_id,
        ).get(match_id, {})

    def get_odds_for_multiple_matches(
        self,
        match_ids: Sequence[int],
        bet_type_id: int = 1,
    ) -> dict[int, AllBookmakerOddsByOutcome]:
        """Return latest odds from all bookmakers keyed by match ID."""
        rows = self._fetch_latest_odds_rows(match_ids, bet_type_id)
        return _group_odds_by_match_and_outcome(rows)

    def analyze_matches_for_value(
        self,
        match_ids: Sequence[int],
        kelly_fraction: float = 0.50,
        min_value_threshold: float = 0.05,
    ) -> dict[str, Any]:
        """Compare model probabilities with odds and return value opportunities."""
        if not match_ids:
            return {
                "total_matches_analyzed": 0,
                "matches_with_predictions": 0,
                "matches_with_odds": 0,
                "matches_with_value_bets": 0,
                "total_value_bets": 0,
                "all_value_bets": [],
                "error": "No match IDs provided",
            }

        predictions = self.get_multiple_match_predictions(match_ids)
        odds = self.get_best_odds_for_multiple_matches(match_ids)

        all_value_bets = []
        matches_processed = 0
        matches_with_value = 0
        for match_id in match_ids:
            if match_id not in predictions or match_id not in odds:
                continue

            matches_processed += 1
            prediction = predictions[match_id]
            analysis = _analyze_betting_opportunity(
                prediction,
                odds[match_id],
                kelly_fraction,
                min_value_threshold,
            )
            if not analysis["has_value_bets"]:
                continue

            matches_with_value += 1
            for bet in analysis["value_bets"]:
                bet_with_context = dict(bet)
                bet_with_context.update(
                    {
                        "match_id": match_id,
                        "home_team": prediction.get("home_team"),
                        "away_team": prediction.get("away_team"),
                        "predicted_result": prediction.get("predicted_result"),
                        "model_confidence": prediction.get("confidence"),
                        "prediction_date": prediction.get("prediction_date"),
                    }
                )
                all_value_bets.append(bet_with_context)

        all_value_bets.sort(key=lambda bet: bet["expected_value"], reverse=True)
        total_bet_percentage = sum(
            bet["recommended_bet_percentage"] for bet in all_value_bets
        )
        total_potential_profit = sum(
            bet["potential_profit_percentage"] for bet in all_value_bets
        )

        return {
            "total_matches_analyzed": len(match_ids),
            "matches_with_predictions": len(predictions),
            "matches_with_odds": len(odds),
            "matches_processed": matches_processed,
            "matches_with_value_bets": matches_with_value,
            "total_value_bets": len(all_value_bets),
            "all_value_bets": all_value_bets,
            "summary": {
                "total_bet_percentage": total_bet_percentage,
                "total_potential_profit_percentage": total_potential_profit,
                "average_expected_value": (
                    sum(bet["expected_value"] for bet in all_value_bets)
                    / len(all_value_bets)
                    if all_value_bets
                    else 0
                ),
                "kelly_fraction": kelly_fraction,
                "min_value_threshold": min_value_threshold,
            },
        }

    def _fetch_latest_odds_rows(
        self,
        match_ids: Sequence[int],
        bet_type_id: int,
    ) -> list[Row]:
        if not match_ids:
            return []

        query = f"""
            WITH latest_odds AS (
                SELECT
                    match_id,
                    bookmaker_id,
                    bookmaker_name,
                    bet_value,
                    odds_value,
                    retrieved_at,
                    ROW_NUMBER() OVER (
                        PARTITION BY match_id, bookmaker_id, bet_value
                        ORDER BY retrieved_at DESC
                    ) as rn
                FROM odds
                WHERE match_id IN ({_placeholders(match_ids)})
                AND bet_type_id = %s
            )
            SELECT
                match_id,
                bookmaker_id,
                bookmaker_name,
                bet_value,
                odds_value,
                retrieved_at
            FROM latest_odds
            WHERE rn = 1
            ORDER BY match_id, bet_value, odds_value DESC
        """
        try:
            return self._runner.fetch_all(query, tuple(match_ids) + (bet_type_id,))
        except Exception as exc:
            raise FootballQueryError(f"Error getting odds: {exc}") from exc


def _ensure_read_only_query(query: str) -> None:
    normalized = query.lstrip().upper()
    if not normalized.startswith(("SELECT", "WITH")):
        raise ValueError("read-only football queries may only use SELECT or WITH")


def _placeholders(values: Sequence[Any]) -> str:
    return ",".join(["%s"] * len(values))


def _recent_form_side_filter(
    team_id: int,
    at_home: bool | None,
) -> tuple[str, list[Any]]:
    if at_home is True:
        return "AND m.home_team_id = %s", [team_id]
    if at_home is False:
        return "AND m.away_team_id = %s", [team_id]
    return "AND (m.home_team_id = %s OR m.away_team_id = %s)", [team_id, team_id]


def _map_prediction(row: Row) -> Prediction:
    probs = [
        _number(row.get(probability_key), 0)
        for probability_key, _ in PROBABILITY_OUTCOMES
    ]
    return {
        "match_id": row["match_id"],
        "home_team": row["home_team_name"],
        "away_team": row["away_team_name"],
        "predicted_result": PREDICTED_RESULT_LABELS.get(
            row.get("predicted_result"),
            "Unknown",
        ),
        "confidence": max(probs) if any(probs) else 0.5,
        "prob_home_win": probs[0],
        "prob_draw": probs[1],
        "prob_away_win": probs[2],
        "model_type": row.get("model_type", "unknown"),
        "prediction_date": row.get("prediction_timestamp"),
    }


def _map_upcoming_match(row: Row) -> dict[str, Any]:
    return {
        "match_id": row["match_id"],
        "start_time": _isoformat(row.get("start_time")),
        "home_team": row["home_team_name"],
        "away_team": row["away_team_name"],
        "competition": row["competition_name"],
        "country": row["competition_country"],
        "competition_id": row.get("competition_id"),
    }


def _map_recent_form(
    rows: Sequence[Row],
    team_id: int,
    last_n_matches: int,
    competition_id: int | str | None,
    at_home: bool | None,
) -> dict[str, Any]:
    wins = 0
    draws = 0
    losses = 0
    processed_matches = []

    for row in rows:
        home_score = row["home_score"]
        away_score = row["away_score"]
        team_side = row["team_side"]
        match_result, team_result = _classify_match_result(
            home_score,
            away_score,
            team_side,
        )

        if team_result == "Win":
            wins += 1
        elif team_result == "Draw":
            draws += 1
        else:
            losses += 1

        processed_matches.append(
            {
                "match_id": row["match_id"],
                "date": _date_string(row.get("start_time")),
                "home_team": row["home_team_name"],
                "away_team": row["away_team_name"],
                "score": f"{home_score}-{away_score}",
                "match_result": match_result,
                "team_side": team_side,
                "team_result": team_result,
            }
        )

    total_matches = len(rows)
    first = rows[0]
    team_name = (
        first["home_team_name"]
        if first["team_side"] == "home"
        else first["away_team_name"]
    )
    home_matches = [match for match in processed_matches if match["team_side"] == "home"]
    away_matches = [match for match in processed_matches if match["team_side"] == "away"]
    home_wins = sum(1 for match in home_matches if match["team_result"] == "Win")
    away_wins = sum(1 for match in away_matches if match["team_result"] == "Win")

    competition_info = None
    if competition_id:
        competition_info = {
            "competition_id": first.get("competition_id"),
            "competition_name": first.get("competition_name"),
        }

    return {
        "success": True,
        "error": None,
        "data": {
            "team_id": team_id,
            "team_name": team_name,
            "analysis_period": f"Last {total_matches} matches",
            "total_matches": total_matches,
            "overall_stats": {
                "wins": wins,
                "draws": draws,
                "losses": losses,
                "win_rate": round((wins / total_matches) * 100, 1),
                "draw_rate": round((draws / total_matches) * 100, 1),
                "loss_rate": round((losses / total_matches) * 100, 1),
            },
            "home_away_breakdown": {
                "home_matches": len(home_matches),
                "away_matches": len(away_matches),
                "home_win_rate": round((home_wins / len(home_matches)) * 100, 1)
                if home_matches
                else 0,
                "away_win_rate": round((away_wins / len(away_matches)) * 100, 1)
                if away_matches
                else 0,
            },
            "competition_info": competition_info,
            "filters_applied": {
                "last_n_matches": last_n_matches,
                "competition_id": competition_id,
                "at_home": at_home,
            },
            "recent_matches": processed_matches[:RECENT_MATCH_LIMIT],
        },
    }


def _classify_match_result(
    home_score: int,
    away_score: int,
    team_side: str,
) -> tuple[str, str]:
    if home_score == away_score:
        return "Draw", "Draw"
    if home_score > away_score:
        return "Home Win", "Win" if team_side == "home" else "Loss"
    return "Away Win", "Win" if team_side == "away" else "Loss"


def _group_odds_by_match_and_outcome(
    rows: Sequence[Row],
) -> dict[int, AllBookmakerOddsByOutcome]:
    odds_by_match: dict[int, AllBookmakerOddsByOutcome] = {}
    for row in rows:
        match_id = int(row["match_id"])
        bet_value = _normalize_bet_value(row["bet_value"])
        odds_by_match.setdefault(match_id, {}).setdefault(bet_value, []).append(
            {
                "bookmaker_id": row["bookmaker_id"],
                "bookmaker_name": row["bookmaker_name"],
                "odds_value": float(row["odds_value"]),
                "retrieved_at": row["retrieved_at"],
            }
        )
    return odds_by_match


def _get_best_odds_from_rows(
    rows: Sequence[Row],
) -> dict[int, OddsByOutcome]:
    odds_by_match: dict[int, OddsByOutcome] = {}
    for row in rows:
        match_id = int(row["match_id"])
        bet_value = _normalize_bet_value(row["bet_value"])
        odds_value = float(row["odds_value"])
        match_odds = odds_by_match.setdefault(match_id, {})
        if bet_value not in match_odds:
            match_odds[bet_value] = {
                "odds_value": odds_value,
                "bookmaker_name": row["bookmaker_name"],
                "bookmaker_id": row["bookmaker_id"],
                "retrieved_at": row["retrieved_at"],
                "implied_probability": 1.0 / odds_value,
            }
    return odds_by_match


def _normalize_bet_value(bet_value: str) -> str:
    value = bet_value.lower().strip()
    if value in {"home", "1", "home win"} or value.startswith("home "):
        return "Home Win"
    if value in {"draw", "x", "tie"} or "draw" in value:
        return "Draw"
    if value in {"away", "2", "away win"} or value.startswith("away "):
        return "Away Win"
    return bet_value.title()


def _analyze_betting_opportunity(
    prediction: Mapping[str, Any],
    best_odds: OddsByOutcome,
    kelly_fraction: float,
    min_value_threshold: float,
) -> dict[str, Any]:
    value_bets = _calculate_value_bets(prediction, best_odds, min_value_threshold)
    bets_with_sizing = [
        _with_bet_sizing(bet, kelly_fraction, max_bet_percentage=0.50)
        for bet in value_bets
    ]
    return {
        "has_value_bets": len(bets_with_sizing) > 0,
        "number_of_value_bets": len(bets_with_sizing),
        "value_bets": bets_with_sizing,
        "total_bet_percentage": sum(
            bet["recommended_bet_percentage"] for bet in bets_with_sizing
        ),
        "total_potential_profit_percentage": sum(
            bet["potential_profit_percentage"] for bet in bets_with_sizing
        ),
        "kelly_fraction_used": kelly_fraction,
        "min_value_threshold": min_value_threshold,
    }


def _calculate_value_bets(
    prediction: Mapping[str, Any],
    best_odds: OddsByOutcome,
    min_value_threshold: float,
) -> list[dict[str, Any]]:
    value_bets = []
    for pred_key, odds_key in PROBABILITY_OUTCOMES:
        if pred_key not in prediction or odds_key not in best_odds:
            continue

        model_prob = _number(prediction[pred_key], 0)
        odds_info = best_odds[odds_key]
        odds_value = float(odds_info["odds_value"])
        expected_value = (model_prob * odds_value) - 1
        if expected_value > min_value_threshold:
            value_bets.append(
                {
                    "outcome": odds_key,
                    "model_probability": model_prob,
                    "odds_value": odds_value,
                    "implied_probability": odds_info["implied_probability"],
                    "expected_value": expected_value,
                    "value_percentage": expected_value * 100,
                    "bookmaker_name": odds_info["bookmaker_name"],
                    "bookmaker_id": odds_info["bookmaker_id"],
                }
            )

    value_bets.sort(key=lambda bet: bet["expected_value"], reverse=True)
    return value_bets


def _with_bet_sizing(
    bet: Mapping[str, Any],
    kelly_fraction: float,
    max_bet_percentage: float,
) -> dict[str, Any]:
    odds_value = float(bet["odds_value"])
    model_probability = float(bet["model_probability"])
    net_odds = odds_value - 1
    lose_probability = 1 - model_probability
    kelly_full = (net_odds * model_probability - lose_probability) / net_odds
    kelly_fractional = kelly_full * kelly_fraction
    recommended = min(max(kelly_fractional, 0), max_bet_percentage)
    potential_profit_ratio = recommended * net_odds

    bet_with_sizing = dict(bet)
    bet_with_sizing.update(
        {
            "kelly_info": {
                "kelly_full_percentage": kelly_full,
                "kelly_fractional_percentage": kelly_fractional,
                "recommended_percentage": recommended,
                "kelly_fraction_used": kelly_fraction,
                "max_bet_cap": max_bet_percentage,
                "is_capped": recommended >= max_bet_percentage,
            },
            "recommended_bet_percentage": recommended * 100,
            "potential_profit_percentage": potential_profit_ratio * 100,
            "risk_reward_ratio": potential_profit_ratio / recommended
            if recommended > 0
            else 0,
        }
    )
    return bet_with_sizing


def _number(value: Any, default: float) -> float:
    return float(value) if value is not None else default


def _isoformat(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _date_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


__all__ = [
    "FootballQueryError",
    "PostgresReadOnlyRunner",
    "ReadOnlyFootballQueries",
]
