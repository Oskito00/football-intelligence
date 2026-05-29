"""Read-only football query interfaces for Analyst Tool consumers.

The public methods in this module return stable Python dictionaries while
hiding SQL and connection handling behind an injectable read-only runner.
These contracts are stable for Analyst Tools:

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

import json
import logging
import sqlite3
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol

import pandas as pd
from psycopg2.extras import execute_values

from football_intelligence.features.schema import FORM_FEATURE_SCHEMA

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
FEATURE_SNAPSHOT_FACT_QUERIES = (
    (
        "match_info",
        """
        SELECT competition_season_name
        FROM match_info_future
        WHERE match_id = %s
        ORDER BY start_time DESC
        LIMIT 1
        """,
    ),
    (
        "stage_of_season",
        """
        SELECT stage_of_season, stage_of_season_category
        FROM stage_of_season_future
        WHERE match_id = %s
        ORDER BY start_time DESC
        LIMIT 1
        """,
    ),
    (
        "formation",
        """
        SELECT home_team_formation, away_team_formation
        FROM formation_future
        WHERE match_id = %s
        ORDER BY start_time DESC
        LIMIT 1
        """,
    ),
    (
        "team_strength",
        """
        SELECT
            home_team_elo_K40,
            away_team_elo_K40,
            k_draw_parameter,
            eta_home_advantage
        FROM elo_future
        WHERE match_id = %s
        ORDER BY start_time DESC
        LIMIT 1
        """,
    ),
    (
        "league_standings",
        """
        SELECT
            home_standing,
            home_points,
            away_standing,
            away_points
        FROM league_standings_future
        WHERE match_id = %s
        ORDER BY start_time DESC
        LIMIT 1
        """,
    ),
    (
        "head_to_head",
        """
        SELECT
            h2h_home_wins_last_10,
            h2h_draws_last_10,
            h2h_away_wins_last_10,
            h2h_avg_total_goals
        FROM h2h_future
        WHERE match_id = %s
        LIMIT 1
        """,
    ),
    (
        "form",
        f"""
        SELECT home_team_form, away_team_form, draw_features
        FROM {FORM_FEATURE_SCHEMA.table_for_mode("inference")}
        WHERE match_id = %s
        LIMIT 1
        """,
    ),
)


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

    def get_upcoming_matches_between(
        self,
        *,
        starts_at: datetime,
        ends_at: datetime,
    ) -> list[dict[str, Any]]:
        """Return remaining Upcoming Matches in an explicit date window."""
        query = """
            SELECT
                match_id,
                start_time,
                home_team_name,
                away_team_name,
                competition_name,
                competition_country,
                competition_id
            FROM matches
            WHERE match_status = 'NS'
            AND start_time >= %s
            AND start_time < %s
            AND home_team_name IS NOT NULL
            AND away_team_name IS NOT NULL
            ORDER BY start_time ASC, match_id ASC
        """
        try:
            rows = self._runner.fetch_all(query, (starts_at, ends_at))
        except Exception as exc:
            raise FootballQueryError(
                f"Error getting Prediction Board matches: {exc}"
            ) from exc

        return [_map_upcoming_match(row) for row in rows]

    def get_match(self, match_id: int) -> dict[str, Any] | None:
        """Return one match by ID for match detail."""
        query = """
            SELECT
                match_id,
                start_time,
                home_team_name,
                away_team_name,
                competition_name,
                competition_country,
                competition_id,
                match_status,
                home_score,
                away_score
            FROM matches
            WHERE match_id = %s
            LIMIT 1
        """
        try:
            row = self._runner.fetch_one(query, (match_id,))
        except Exception as exc:
            raise FootballQueryError(f"Error getting match {match_id}: {exc}") from exc

        return _map_match_detail(row) if row else None

    def get_feature_snapshot_facts(self, match_id: int) -> dict[str, Any]:
        """Return factual Future Feature Set inputs for a Feature Snapshot."""
        facts = {}
        try:
            for family, query in FEATURE_SNAPSHOT_FACT_QUERIES:
                rows = self._runner.fetch_all(query, (match_id,))
                if rows:
                    facts[family] = _map_feature_snapshot_family(family, rows[0])
        except Exception as exc:
            raise FootballQueryError(
                f"Error getting Feature Snapshot for match {match_id}: {exc}"
            ) from exc

        return facts

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

    def get_odds_freshness_for_matches(
        self,
        match_ids: Sequence[int],
    ) -> dict[int, dict[str, Any]]:
        """Return odds freshness keyed by match ID."""
        if not match_ids:
            return {}

        query = f"""
            SELECT
                match_id,
                MAX(retrieved_at) AS latest_retrieved_at,
                MAX(api_last_updated) AS latest_api_last_updated
            FROM odds
            WHERE match_id IN ({_placeholders(match_ids)})
            GROUP BY match_id
        """
        try:
            rows = self._runner.fetch_all(query, tuple(match_ids))
        except Exception as exc:
            raise FootballQueryError(
                f"Error getting odds freshness for Prediction Board: {exc}"
            ) from exc

        return {
            int(row["match_id"]): {
                "latest_retrieved_at": row.get("latest_retrieved_at"),
                "latest_api_last_updated": row.get("latest_api_last_updated"),
            }
            for row in rows
        }

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

    def get_football_data_status_facts(
        self,
        *,
        days: int = 7,
        top_team_limit: int = 5,
        elo_competition: str = "Premier League",
        elo_country: str = "England",
    ) -> dict[str, Any]:
        """Return read-only facts backing Football Data Status."""
        try:
            latest_completed_match = self._runner.fetch_one(
                """
                SELECT
                    match_id,
                    start_time,
                    home_team_name,
                    away_team_name,
                    competition_name,
                    competition_country,
                    home_score,
                    away_score
                FROM matches
                WHERE home_score IS NOT NULL
                AND away_score IS NOT NULL
                ORDER BY start_time DESC
                LIMIT 1
                """
            )
            unprocessed_completed_matches = self._runner.fetch_one(
                """
                SELECT COUNT(*) AS count
                FROM matches m
                LEFT JOIN processed_info p ON (
                    m.match_id = p.match_id
                    AND p.is_processed = true
                    AND p.processing_mode = 'training'
                )
                WHERE m.home_score IS NOT NULL
                AND m.away_score IS NOT NULL
                AND p.match_id IS NULL
                """
            )
            latest_elo_history_date = self._runner.fetch_one(
                """
                SELECT MAX(start_time) AS latest_elo_history_date
                FROM elo_history
                """
            )
            future_feature_set_count = self._runner.fetch_one(
                """
                SELECT COUNT(DISTINCT match_id) AS count
                FROM match_info_future
                WHERE start_time >= CURRENT_TIMESTAMP
                AND start_time <= CURRENT_TIMESTAMP + (%s * INTERVAL '1 day')
                """,
                (days,),
            )
            prediction_count = self._runner.fetch_one(
                """
                SELECT COUNT(DISTINCT match_id) AS count
                FROM match_result_predictions
                WHERE start_time >= CURRENT_TIMESTAMP
                AND start_time <= CURRENT_TIMESTAMP + (%s * INTERVAL '1 day')
                """,
                (days,),
            )
            odds_freshness = self._runner.fetch_one(
                """
                SELECT
                    MAX(o.retrieved_at) AS latest_retrieved_at,
                    MAX(o.api_last_updated) AS latest_api_last_updated,
                    COUNT(DISTINCT o.match_id) AS matches_with_odds_next_7_days
                FROM odds o
                JOIN matches m ON m.match_id = o.match_id
                WHERE m.home_score IS NULL
                AND m.away_score IS NULL
                AND m.start_time >= CURRENT_TIMESTAMP
                AND m.start_time <= CURRENT_TIMESTAMP + (%s * INTERVAL '1 day')
                """,
                (days,),
            )
            top_elo_teams = self._runner.fetch_all(
                """
                SELECT
                    c.team_id,
                    COALESCE(t.team_name, c.team_name) AS team_name,
                    c.elo_K40 AS elo,
                    t.main_competition_name AS competition,
                    t.main_competition_country AS country
                FROM club_elo_ratings c
                JOIN team_main_competition t ON t.team_id = c.team_id
                WHERE t.main_competition_name ILIKE %s
                AND t.main_competition_country ILIKE %s
                AND c.elo_K40 IS NOT NULL
                ORDER BY c.elo_K40 DESC, COALESCE(t.team_name, c.team_name) ASC
                LIMIT %s
                """,
                (elo_competition, elo_country, top_team_limit),
            )
        except Exception as exc:
            raise FootballQueryError(f"Error getting Football Data Status: {exc}") from exc

        return {
            "latest_completed_match": _map_completed_match(latest_completed_match)
            if latest_completed_match
            else None,
            "unprocessed_completed_matches": _count_value(
                unprocessed_completed_matches
            ),
            "latest_elo_history_date": (latest_elo_history_date or {}).get(
                "latest_elo_history_date"
            ),
            "future_feature_set_count": _count_value(future_feature_set_count),
            "prediction_count_next_7_days": _count_value(prediction_count),
            "odds_freshness": {
                "latest_retrieved_at": (odds_freshness or {}).get(
                    "latest_retrieved_at"
                ),
                "latest_api_last_updated": (odds_freshness or {}).get(
                    "latest_api_last_updated"
                ),
                "matches_with_odds_next_7_days": _count_value(
                    odds_freshness,
                    "matches_with_odds_next_7_days",
                ),
            },
            "top_premier_league_elo_teams": [_map_elo_team(row) for row in top_elo_teams],
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


def _map_match_detail(row: Row) -> dict[str, Any]:
    home_score = row.get("home_score")
    away_score = row.get("away_score")
    score = (
        f"{home_score}-{away_score}"
        if home_score is not None and away_score is not None
        else None
    )
    return {
        "match_id": row["match_id"],
        "start_time": row.get("start_time"),
        "home_team": row["home_team_name"],
        "away_team": row["away_team_name"],
        "competition": row["competition_name"],
        "country": row["competition_country"],
        "competition_id": row.get("competition_id"),
        "status": row.get("match_status"),
        "score": score,
    }


def _map_feature_snapshot_family(family: str, row: Row) -> dict[str, Any]:
    mapped = {key: _json_value(value) for key, value in dict(row).items()}
    if family == "match_info":
        return {
            "competition_season": mapped.get("competition_season_name"),
        }
    return mapped


def _json_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped or stripped[0] not in "[{":
        return value
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return value


def _map_completed_match(row: Row) -> dict[str, Any]:
    return {
        "match_id": row["match_id"],
        "start_time": row.get("start_time"),
        "home_team": row["home_team_name"],
        "away_team": row["away_team_name"],
        "competition": row["competition_name"],
        "country": row["competition_country"],
        "score": f"{row['home_score']}-{row['away_score']}",
    }


def _map_elo_team(row: Row) -> dict[str, Any]:
    return {
        "team_id": row["team_id"],
        "team_name": row["team_name"],
        "elo": row.get("elo"),
        "competition": row.get("competition"),
        "country": row.get("country"),
    }


def _count_value(row: Row | None, key: str = "count") -> int:
    if not row:
        return 0
    return int(row.get(key) or 0)


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
    "bulk_insert_formations",
    "bulk_insert_odds",
    "combine_stats",
    "create_future_tables",
    "create_match_result_predictions_table",
    "create_odds_table",
    "create_tables",
    "dict_to_sqlite",
    "drop_future_tables",
    "drop_tables",
    "get_from_matches",
    "get_from_standings",
    "get_future_matches_with_odds",
    "get_latest_predictions",
    "load_from_postgres",
    "prune_all_future_features",
    "prune_old_future_features",
    "save_predictions_to_db",
    "update_processed_status",
    "upsert_records",
]


# Active football persistence and database support used by the Match
# Intelligence Lifecycle and prediction workflows.

def create_tables(conn):
    """Creates tables of use to processing functions"""
    create_team_match_history_table(conn)
    create_counter_table(conn)
    create_elo_history_table(conn)
    create_club_elo_rating_table(conn)
    create_league_elo_table(conn)
    create_nation_elo_table(conn)
    create_continent_elo_table(conn)
    create_match_info_table(conn)
    create_stage_of_season_table(conn)
    # create_league_standings_table(conn)
    # create_league_standings_history_table(conn)
    create_formation_history_table(conn)
    create_form_history_table(conn)
    create_form_matches_cache_table(conn)
    create_processed_info_table(conn)
    create_h2h_tables(conn)

def create_match_result_predictions_table(conn):
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS match_result_predictions (
        match_id INTEGER PRIMARY KEY,
        predicted_result INTEGER,
        start_time TIMESTAMP,
        home_team_name TEXT,
        away_team_name TEXT,
        prob_home_win REAL,
        prob_draw REAL,
        prob_away_win REAL,
        model_type TEXT,  -- 'basic' or 'with_formation'
        prediction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    cursor.close()

def create_processed_info_table(conn):
    """Creates table to track processing status of matches"""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS processed_info (
                match_id BIGINT PRIMARY KEY,
                is_processed BOOLEAN DEFAULT FALSE,
                with_formation BOOLEAN DEFAULT FALSE,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processing_mode VARCHAR(20) DEFAULT 'training',
                FOREIGN KEY (match_id) REFERENCES matches(match_id)
            )
        """)

def create_future_tables(conn):
    """Creates tables of use to processing functions"""
    create_elo_future_table(conn)
    create_stage_of_season_future_table(conn)
    create_match_info_future_table(conn)
    create_league_standings_future_table(conn)
    create_formation_future_table(conn)
    create_h2h_future_table(conn)
    create_form_future_table(conn)

def create_form_future_table(conn):
    """Creates table to store processed form match data"""
    _create_form_feature_table(conn, FORM_FEATURE_SCHEMA.table_for_mode("inference"))

def create_h2h_future_table(conn):
    """Creates table to store processed H2H match data"""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS h2h_future (
                match_id INTEGER PRIMARY KEY,
                h2h_draws_last_3 FLOAT,
                h2h_draws_last_5 FLOAT,
                h2h_draws_last_10 FLOAT,
                h2h_home_wins_last_3 FLOAT,
                h2h_home_wins_last_5 FLOAT,
                h2h_home_wins_last_10 FLOAT,
                h2h_away_wins_last_3 FLOAT,
                h2h_away_wins_last_5 FLOAT,
                h2h_away_wins_last_10 FLOAT,
                h2h_avg_total_goals FLOAT,
                h2h_avg_goal_diff FLOAT,
                h2h_home_goals_avg_last_3 FLOAT,
                h2h_home_goals_avg_last_5 FLOAT,
                h2h_home_goals_avg_last_10 FLOAT,
                h2h_away_goals_avg_last_3 FLOAT,
                h2h_away_goals_avg_last_5 FLOAT,
                h2h_away_goals_avg_last_10 FLOAT,
                h2h_both_teams_scored_rate FLOAT,
                h2h_zero_goal_rate FLOAT,
                raw_h2h_matches JSONB
            )
        """)

def create_stage_of_season_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stage_of_season_history (
            match_id INTEGER,
            start_time TIMESTAMP,
            season_start_date TIMESTAMP,
            season_end_date TIMESTAMP,
            stage_of_season REAL,
            stage_of_season_category TEXT
        )
    """)
    conn.commit()
    cursor.close()

def create_formation_history_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS formation_history (
            match_id INTEGER,
            start_time TIMESTAMP,
            home_team_formation TEXT,
            away_team_formation TEXT
        )
    """)
    conn.commit()
    cursor.close()

def create_formation_future_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS formation_future (
            match_id INTEGER,
            start_time TIMESTAMP,
            home_team_formation TEXT,
            away_team_formation TEXT
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_formation_future_start_time
        ON formation_future(start_time)
    """)
    conn.commit()
    cursor.close()

def create_stage_of_season_future_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stage_of_season_future (
            match_id INTEGER,
            start_time TIMESTAMP,
            season_start_date TIMESTAMP,
            season_end_date TIMESTAMP,
            stage_of_season REAL,
            stage_of_season_category TEXT
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_stage_of_season_future_start_time
        ON stage_of_season_future(start_time)
    """)
    conn.commit()
    cursor.close()

def create_elo_future_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS elo_future (
            match_id INTEGER,
            start_time TIMESTAMP,
            home_team_id INTEGER,
            away_team_id INTEGER,
            home_team_name TEXT,
            away_team_name TEXT,
            k_draw_parameter REAL,
            eta_home_advantage REAL,

            -- HOME TEAM ELO RATINGS
            home_team_nation_elo_K5 INTEGER,
            home_team_nation_elo_K10 INTEGER,
            home_team_nation_elo_K20 INTEGER,
            home_team_nation_elo_K30 INTEGER,
            home_team_nation_elo_K40 INTEGER,
            home_team_nation_elo_K80 INTEGER,
            home_team_league_domestic_elo_K5 INTEGER,
            home_team_league_domestic_elo_K10 INTEGER,
            home_team_league_domestic_elo_K20 INTEGER,
            home_team_league_domestic_elo_K30 INTEGER,
            home_team_league_domestic_elo_K40 INTEGER,
            home_team_league_domestic_elo_K80 INTEGER,
            home_team_league_continental_elo_K5 INTEGER,
            home_team_league_continental_elo_K10 INTEGER,
            home_team_league_continental_elo_K20 INTEGER,
            home_team_league_continental_elo_K30 INTEGER,
            home_team_league_continental_elo_K40 INTEGER,
            home_team_league_continental_elo_K80 INTEGER,
            home_team_league_intercontinental_elo_K5 INTEGER,
            home_team_league_intercontinental_elo_K10 INTEGER,
            home_team_league_intercontinental_elo_K20 INTEGER,
            home_team_league_intercontinental_elo_K30 INTEGER,
            home_team_league_intercontinental_elo_K40 INTEGER,
            home_team_league_intercontinental_elo_K80 INTEGER,
            home_team_continent_elo_K5 INTEGER,
            home_team_continent_elo_K10 INTEGER,
            home_team_continent_elo_K20 INTEGER,
            home_team_continent_elo_K30 INTEGER,
            home_team_continent_elo_K40 INTEGER,
            home_team_continent_elo_K80 INTEGER,
            home_team_elo_home_matches_K5 INTEGER,
            home_team_elo_home_matches_K10 INTEGER,
            home_team_elo_home_matches_K20 INTEGER,
            home_team_elo_home_matches_K30 INTEGER,
            home_team_elo_home_matches_K40 INTEGER,
            home_team_elo_home_matches_K80 INTEGER,
            home_team_elo_away_matches_K5 INTEGER,
            home_team_elo_away_matches_K10 INTEGER,
            home_team_elo_away_matches_K20 INTEGER,
            home_team_elo_away_matches_K30 INTEGER,
            home_team_elo_away_matches_K40 INTEGER,
            home_team_elo_away_matches_K80 INTEGER,
            home_team_elo_K5 INTEGER,
            home_team_elo_K10 INTEGER,
            home_team_elo_K20 INTEGER,
            home_team_elo_K30 INTEGER,
            home_team_elo_K40 INTEGER,
            home_team_elo_K80 INTEGER,
            home_team_elo_domestic_K5 INTEGER,
            home_team_elo_domestic_K10 INTEGER,
            home_team_elo_domestic_K20 INTEGER,
            home_team_elo_domestic_K30 INTEGER,
            home_team_elo_domestic_K40 INTEGER,
            home_team_elo_domestic_K80 INTEGER,
            home_team_elo_intraleague_K5 INTEGER,
            home_team_elo_intraleague_K10 INTEGER,
            home_team_elo_intraleague_K20 INTEGER,
            home_team_elo_intraleague_K30 INTEGER,
            home_team_elo_intraleague_K40 INTEGER,
            home_team_elo_intraleague_K80 INTEGER,
            home_team_elo_international_K5 INTEGER,
            home_team_elo_international_K10 INTEGER,
            home_team_elo_international_K20 INTEGER,
            home_team_elo_international_K30 INTEGER,
            home_team_elo_international_K40 INTEGER,
            home_team_elo_international_K80 INTEGER,


            -- AWAY TEAM ELO RATINGS
            away_team_nation_elo_K5 INTEGER,
            away_team_nation_elo_K10 INTEGER,
            away_team_nation_elo_K20 INTEGER,
            away_team_nation_elo_K30 INTEGER,
            away_team_nation_elo_K40 INTEGER,
            away_team_nation_elo_K80 INTEGER,
            away_team_league_domestic_elo_K5 INTEGER,
            away_team_league_domestic_elo_K10 INTEGER,
            away_team_league_domestic_elo_K20 INTEGER,
            away_team_league_domestic_elo_K30 INTEGER,
            away_team_league_domestic_elo_K40 INTEGER,
            away_team_league_domestic_elo_K80 INTEGER,
            away_team_league_continental_elo_K5 INTEGER,
            away_team_league_continental_elo_K10 INTEGER,
            away_team_league_continental_elo_K20 INTEGER,
            away_team_league_continental_elo_K30 INTEGER,
            away_team_league_continental_elo_K40 INTEGER,
            away_team_league_continental_elo_K80 INTEGER,
            away_team_league_intercontinental_elo_K5 INTEGER,
            away_team_league_intercontinental_elo_K10 INTEGER,
            away_team_league_intercontinental_elo_K20 INTEGER,
            away_team_league_intercontinental_elo_K30 INTEGER,
            away_team_league_intercontinental_elo_K40 INTEGER,
            away_team_league_intercontinental_elo_K80 INTEGER,
            away_team_continent_elo_K5 INTEGER,
            away_team_continent_elo_K10 INTEGER,
            away_team_continent_elo_K20 INTEGER,
            away_team_continent_elo_K30 INTEGER,
            away_team_continent_elo_K40 INTEGER,
            away_team_continent_elo_K80 INTEGER,
            away_team_elo_home_matches_K5 INTEGER,
            away_team_elo_home_matches_K10 INTEGER,
            away_team_elo_home_matches_K20 INTEGER,
            away_team_elo_home_matches_K30 INTEGER,
            away_team_elo_home_matches_K40 INTEGER,
            away_team_elo_home_matches_K80 INTEGER,
            away_team_elo_away_matches_K5 INTEGER,
            away_team_elo_away_matches_K10 INTEGER,
            away_team_elo_away_matches_K20 INTEGER,
            away_team_elo_away_matches_K30 INTEGER,
            away_team_elo_away_matches_K40 INTEGER,
            away_team_elo_away_matches_K80 INTEGER,
            away_team_elo_K5 INTEGER,
            away_team_elo_K10 INTEGER,
            away_team_elo_K20 INTEGER,
            away_team_elo_K30 INTEGER,
            away_team_elo_K40 INTEGER,
            away_team_elo_K80 INTEGER,
            away_team_elo_domestic_K5 INTEGER,
            away_team_elo_domestic_K10 INTEGER,
            away_team_elo_domestic_K20 INTEGER,
            away_team_elo_domestic_K30 INTEGER,
            away_team_elo_domestic_K40 INTEGER,
            away_team_elo_domestic_K80 INTEGER,
            away_team_elo_intraleague_K5 INTEGER,
            away_team_elo_intraleague_K10 INTEGER,
            away_team_elo_intraleague_K20 INTEGER,
            away_team_elo_intraleague_K30 INTEGER,
            away_team_elo_intraleague_K40 INTEGER,
            away_team_elo_intraleague_K80 INTEGER,
            away_team_elo_international_K5 INTEGER,
            away_team_elo_international_K10 INTEGER,
            away_team_elo_international_K20 INTEGER,
            away_team_elo_international_K30 INTEGER,
            away_team_elo_international_K40 INTEGER,
            away_team_elo_international_K80 INTEGER
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_elo_future_start_time
        ON elo_future(start_time)
    """)
    conn.commit()
    cursor.close()

def create_elo_history_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS elo_history (
            match_id INTEGER,
            start_time TIMESTAMP,
            home_team_id INTEGER,
            away_team_id INTEGER,
            home_team_name TEXT,
            away_team_name TEXT,
            k_draw_parameter REAL,
            eta_home_advantage REAL,

            -- HOME TEAM ELO RATINGS
            home_team_nation_elo_K5 INTEGER,
            home_team_nation_elo_K10 INTEGER,
            home_team_nation_elo_K20 INTEGER,
            home_team_nation_elo_K30 INTEGER,
            home_team_nation_elo_K40 INTEGER,
            home_team_nation_elo_K80 INTEGER,
            home_team_league_domestic_elo_K5 INTEGER,
            home_team_league_domestic_elo_K10 INTEGER,
            home_team_league_domestic_elo_K20 INTEGER,
            home_team_league_domestic_elo_K30 INTEGER,
            home_team_league_domestic_elo_K40 INTEGER,
            home_team_league_domestic_elo_K80 INTEGER,
            home_team_league_continental_elo_K5 INTEGER,
            home_team_league_continental_elo_K10 INTEGER,
            home_team_league_continental_elo_K20 INTEGER,
            home_team_league_continental_elo_K30 INTEGER,
            home_team_league_continental_elo_K40 INTEGER,
            home_team_league_continental_elo_K80 INTEGER,
            home_team_league_intercontinental_elo_K5 INTEGER,
            home_team_league_intercontinental_elo_K10 INTEGER,
            home_team_league_intercontinental_elo_K20 INTEGER,
            home_team_league_intercontinental_elo_K30 INTEGER,
            home_team_league_intercontinental_elo_K40 INTEGER,
            home_team_league_intercontinental_elo_K80 INTEGER,
            home_team_continent_elo_K5 INTEGER,
            home_team_continent_elo_K10 INTEGER,
            home_team_continent_elo_K20 INTEGER,
            home_team_continent_elo_K30 INTEGER,
            home_team_continent_elo_K40 INTEGER,
            home_team_continent_elo_K80 INTEGER,
            home_team_elo_home_matches_K5 INTEGER,
            home_team_elo_home_matches_K10 INTEGER,
            home_team_elo_home_matches_K20 INTEGER,
            home_team_elo_home_matches_K30 INTEGER,
            home_team_elo_home_matches_K40 INTEGER,
            home_team_elo_home_matches_K80 INTEGER,
            home_team_elo_away_matches_K5 INTEGER,
            home_team_elo_away_matches_K10 INTEGER,
            home_team_elo_away_matches_K20 INTEGER,
            home_team_elo_away_matches_K30 INTEGER,
            home_team_elo_away_matches_K40 INTEGER,
            home_team_elo_away_matches_K80 INTEGER,
            home_team_elo_K5 INTEGER,
            home_team_elo_K10 INTEGER,
            home_team_elo_K20 INTEGER,
            home_team_elo_K30 INTEGER,
            home_team_elo_K40 INTEGER,
            home_team_elo_K80 INTEGER,
            home_team_elo_domestic_K5 INTEGER,
            home_team_elo_domestic_K10 INTEGER,
            home_team_elo_domestic_K20 INTEGER,
            home_team_elo_domestic_K30 INTEGER,
            home_team_elo_domestic_K40 INTEGER,
            home_team_elo_domestic_K80 INTEGER,
            home_team_elo_intraleague_K5 INTEGER,
            home_team_elo_intraleague_K10 INTEGER,
            home_team_elo_intraleague_K20 INTEGER,
            home_team_elo_intraleague_K30 INTEGER,
            home_team_elo_intraleague_K40 INTEGER,
            home_team_elo_intraleague_K80 INTEGER,
            home_team_elo_international_K5 INTEGER,
            home_team_elo_international_K10 INTEGER,
            home_team_elo_international_K20 INTEGER,
            home_team_elo_international_K30 INTEGER,
            home_team_elo_international_K40 INTEGER,
            home_team_elo_international_K80 INTEGER,

            -- AWAY TEAM ELO RATINGS
            away_team_nation_elo_K5 INTEGER,
            away_team_nation_elo_K10 INTEGER,
            away_team_nation_elo_K20 INTEGER,
            away_team_nation_elo_K30 INTEGER,
            away_team_nation_elo_K40 INTEGER,
            away_team_nation_elo_K80 INTEGER,
            away_team_league_domestic_elo_K5 INTEGER,
            away_team_league_domestic_elo_K10 INTEGER,
            away_team_league_domestic_elo_K20 INTEGER,
            away_team_league_domestic_elo_K30 INTEGER,
            away_team_league_domestic_elo_K40 INTEGER,
            away_team_league_domestic_elo_K80 INTEGER,
            away_team_league_continental_elo_K5 INTEGER,
            away_team_league_continental_elo_K10 INTEGER,
            away_team_league_continental_elo_K20 INTEGER,
            away_team_league_continental_elo_K30 INTEGER,
            away_team_league_continental_elo_K40 INTEGER,
            away_team_league_continental_elo_K80 INTEGER,
            away_team_league_intercontinental_elo_K5 INTEGER,
            away_team_league_intercontinental_elo_K10 INTEGER,
            away_team_league_intercontinental_elo_K20 INTEGER,
            away_team_league_intercontinental_elo_K30 INTEGER,
            away_team_league_intercontinental_elo_K40 INTEGER,
            away_team_league_intercontinental_elo_K80 INTEGER,
            away_team_continent_elo_K5 INTEGER,
            away_team_continent_elo_K10 INTEGER,
            away_team_continent_elo_K20 INTEGER,
            away_team_continent_elo_K30 INTEGER,
            away_team_continent_elo_K40 INTEGER,
            away_team_continent_elo_K80 INTEGER,
            away_team_elo_home_matches_K5 INTEGER,
            away_team_elo_home_matches_K10 INTEGER,
            away_team_elo_home_matches_K20 INTEGER,
            away_team_elo_home_matches_K30 INTEGER,
            away_team_elo_home_matches_K40 INTEGER,
            away_team_elo_home_matches_K80 INTEGER,
            away_team_elo_away_matches_K5 INTEGER,
            away_team_elo_away_matches_K10 INTEGER,
            away_team_elo_away_matches_K20 INTEGER,
            away_team_elo_away_matches_K30 INTEGER,
            away_team_elo_away_matches_K40 INTEGER,
            away_team_elo_away_matches_K80 INTEGER,
            away_team_elo_K5 INTEGER,
            away_team_elo_K10 INTEGER,
            away_team_elo_K20 INTEGER,
            away_team_elo_K30 INTEGER,
            away_team_elo_K40 INTEGER,
            away_team_elo_K80 INTEGER,
            away_team_elo_domestic_K5 INTEGER,
            away_team_elo_domestic_K10 INTEGER,
            away_team_elo_domestic_K20 INTEGER,
            away_team_elo_domestic_K30 INTEGER,
            away_team_elo_domestic_K40 INTEGER,
            away_team_elo_domestic_K80 INTEGER,
            away_team_elo_intraleague_K5 INTEGER,
            away_team_elo_intraleague_K10 INTEGER,
            away_team_elo_intraleague_K20 INTEGER,
            away_team_elo_intraleague_K30 INTEGER,
            away_team_elo_intraleague_K40 INTEGER,
            away_team_elo_intraleague_K80 INTEGER,
            away_team_elo_international_K5 INTEGER,
            away_team_elo_international_K10 INTEGER,
            away_team_elo_international_K20 INTEGER,
            away_team_elo_international_K30 INTEGER,
            away_team_elo_international_K40 INTEGER,
            away_team_elo_international_K80 INTEGER,

            -- MATCH RESULT
            home_team_score INTEGER,
            away_team_score INTEGER
        )
    """)
    conn.commit()
    cursor.close()

def create_club_elo_rating_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS club_elo_ratings (
            team_id INTEGER PRIMARY KEY,
            team_name TEXT,
            elo_home_matches_K5 INTEGER,
            elo_home_matches_K10 INTEGER,
            elo_home_matches_K20 INTEGER,
            elo_home_matches_K30 INTEGER,
            elo_home_matches_K40 INTEGER,
            elo_home_matches_K80 INTEGER,
            elo_away_matches_K5 INTEGER,
            elo_away_matches_K10 INTEGER,
            elo_away_matches_K20 INTEGER,
            elo_away_matches_K30 INTEGER,
            elo_away_matches_K40 INTEGER,
            elo_away_matches_K80 INTEGER,
            elo_K5 INTEGER,
            elo_K10 INTEGER,
            elo_K20 INTEGER,
            elo_K30 INTEGER,
            elo_K40 INTEGER,
            elo_K80 INTEGER,
            elo_domestic_K5 INTEGER,
            elo_domestic_K10 INTEGER,
            elo_domestic_K20 INTEGER,
            elo_domestic_K30 INTEGER,
            elo_domestic_K40 INTEGER,
            elo_domestic_K80 INTEGER,
            elo_intraleague_K5 INTEGER,
            elo_intraleague_K10 INTEGER,
            elo_intraleague_K20 INTEGER,
            elo_intraleague_K30 INTEGER,
            elo_intraleague_K40 INTEGER,
            elo_intraleague_K80 INTEGER,
            elo_international_K5 INTEGER,
            elo_international_K10 INTEGER,
            elo_international_K20 INTEGER,
            elo_international_K30 INTEGER,
            elo_international_K40 INTEGER,
            elo_international_K80 INTEGER
        )
    """)
    conn.commit()
    cursor.close()

def create_league_elo_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS league_elo_ratings (
            league_id INTEGER PRIMARY KEY,
            league_domestic_elo_K5 INTEGER,
            league_domestic_elo_K10 INTEGER,
            league_domestic_elo_K20 INTEGER,
            league_domestic_elo_K30 INTEGER,
            league_domestic_elo_K40 INTEGER,
            league_domestic_elo_K80 INTEGER,
            league_continental_elo_K5 INTEGER,
            league_continental_elo_K10 INTEGER,
            league_continental_elo_K20 INTEGER,
            league_continental_elo_K30 INTEGER,
            league_continental_elo_K40 INTEGER,
            league_continental_elo_K80 INTEGER,
            league_intercontinental_elo_K5 INTEGER,
            league_intercontinental_elo_K10 INTEGER,
            league_intercontinental_elo_K20 INTEGER,
            league_intercontinental_elo_K30 INTEGER,
            league_intercontinental_elo_K40 INTEGER,
            league_intercontinental_elo_K80 INTEGER
        )
    """)
    conn.commit()
    cursor.close()

def create_nation_elo_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nation_elo_ratings (
            nation_name TEXT PRIMARY KEY,
            nation_elo_K5 INTEGER,
            nation_elo_K10 INTEGER,
            nation_elo_K20 INTEGER,
            nation_elo_K30 INTEGER,
            nation_elo_K40 INTEGER,
            nation_elo_K80 INTEGER
        )
    """)
    conn.commit()
    cursor.close()

#MAIN COMPETITION
def create_team_main_competition_table(conn):
    """Create a table to store the main competition and country for each team"""
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS team_main_competition (
        team_id INTEGER PRIMARY KEY,
        team_name TEXT,
        main_competition_id INTEGER,
        main_competition_name TEXT,
        main_competition_country TEXT,
        match_count INTEGER
    )
    ''')
    conn.commit()

#MATCH HISTORY
def create_team_match_history_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS TeamMatchHistory (
            team_id      INTEGER,
            match_id     INTEGER,
            start_time   TIMESTAMP,
            competition_season_name TEXT,
            competition_id TEXT,
            competition_name TEXT,
            competition_country TEXT,
            goals_scored INT,
            goals_conceded INT,
            result       VARCHAR(4),  -- 'win', 'loss', 'draw'
            is_home      INTEGER,     -- 0 for away, 1 for home
            is_intraleague_match INTEGER,
            is_domestic_cup_match INTEGER,
            is_continental_cup_match INTEGER,
            PRIMARY KEY (team_id, match_id)
        )
    """)
    conn.commit()
    cursor.close()

#COUNTER FOR ALL MATCH RESULTS
def create_counter_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS counter_table (
            competition_id TEXT,
            home_wins FLOAT,
            draw_wins FLOAT,
            away_wins FLOAT,
            count INTEGER,
            last_updated TEXT,
            PRIMARY KEY (competition_id)
        )
    """)
    conn.commit()
    cursor.close()

#MATCH INFO
def create_match_info_table(conn):
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS match_info_history (
        match_id INTEGER,
        start_time TIMESTAMP,
        competition_season_name TEXT,
        competition_id TEXT,
        competition_name TEXT,
        competition_country TEXT,
        home_team_name TEXT,
        away_team_name TEXT,
        PRIMARY KEY (match_id, competition_id)
    )
    ''')
    conn.commit()
    cursor.close()

def create_match_info_future_table(conn):
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS match_info_future (
        match_id INTEGER,
        start_time TIMESTAMP,
        competition_season_name TEXT,
        competition_id TEXT,
        competition_name TEXT,
        competition_country TEXT,
        home_team_name TEXT,
        away_team_name TEXT,
        PRIMARY KEY (match_id, competition_id)
    )
    ''')
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_match_info_future_start_time
        ON match_info_future(start_time)
    """)
    conn.commit()
    cursor.close()

#LEAGUE STANDINGS
def create_league_standings_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS league_standings (
            team_id INTEGER,
            competition_season_id TEXT,
            matches_played INTEGER,
            wins INTEGER,
            draws INTEGER,
            losses INTEGER,
            goals_for INTEGER,
            goals_against INTEGER,
            goal_difference INTEGER,
            points INTEGER,
            PRIMARY KEY (team_id, competition_season_id)
        )
    """)
    conn.commit()
    cursor.close()

def create_league_standings_history_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS league_standings_history (
            match_id INTEGER,
            home_standing INTEGER,
            home_matches_played INTEGER,
            home_wins INTEGER,
            home_draws INTEGER,
            home_losses INTEGER,
            home_goals_for INTEGER,
            home_goals_against INTEGER,
            home_goal_difference INTEGER,
            home_points INTEGER,
            away_standing INTEGER,
            away_matches_played INTEGER,
            away_wins INTEGER,
            away_draws INTEGER,
            away_losses INTEGER,
            away_goals_for INTEGER,
            away_goals_against INTEGER,
            away_goal_difference INTEGER,
            away_points INTEGER
        )
    """)
    conn.commit()
    cursor.close()

def create_league_standings_future_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS league_standings_future (
            match_id INTEGER,
            start_time TIMESTAMP,
            home_standing INTEGER,
            home_matches_played INTEGER,
            home_wins INTEGER,
            home_draws INTEGER,
            home_losses INTEGER,
            home_goals_for INTEGER,
            home_goals_against INTEGER,
            home_goal_difference INTEGER,
            home_points INTEGER,
            away_standing INTEGER,
            away_matches_played INTEGER,
            away_wins INTEGER,
            away_draws INTEGER,
            away_losses INTEGER,
            away_goals_for INTEGER,
            away_goals_against INTEGER,
            away_goal_difference INTEGER,
            away_points INTEGER
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_league_standings_future_start_time
        ON league_standings_future(start_time)
    """)
    conn.commit()
    cursor.close()

def create_odds_table(conn):
    """Create the odds table if it doesn't exist"""
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS odds (
        id SERIAL PRIMARY KEY,
        match_id INTEGER NOT NULL,
        bookmaker_id INTEGER NOT NULL,
        bookmaker_name TEXT NOT NULL,
        bet_type_id INTEGER NOT NULL,
        bet_type_name TEXT NOT NULL,
        bet_value TEXT NOT NULL,
        odds_value DECIMAL(10,2) NOT NULL,
        retrieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        api_last_updated TIMESTAMP
    )
    ''')

    # Create index for faster queries
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_odds_match_id
    ON odds(match_id)
    ''')

    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_odds_retrieved_at
    ON odds(retrieved_at)
    ''')

    conn.commit()
    cursor.close()

def create_form_history_table(conn):
    """Creates table to store form history for each match"""
    _create_form_feature_table(conn, FORM_FEATURE_SCHEMA.table_for_mode("training"))


def _create_form_feature_table(conn, table_name):
    columns_sql = ",\n                ".join(FORM_FEATURE_SCHEMA.ddl_columns())
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                {columns_sql}
            )
        """)

def create_form_matches_cache_table(conn):
    """Creates table to store processed form match data"""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS form_matches_cache (
                match_id INTEGER PRIMARY KEY,
                start_time TIMESTAMP,
                home_team_id INTEGER,
                away_team_id INTEGER,
                home_name VARCHAR(255),
                away_name VARCHAR(255),
                home_score INTEGER,
                away_score INTEGER,
                home_team_elo INTEGER,
                away_team_elo INTEGER,
                home_team_international_elo INTEGER,
                away_team_international_elo INTEGER
            )
        """)
        # Add indexes for faster queries
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_form_matches_home_team
            ON form_matches_cache(home_team_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_form_matches_away_team
            ON form_matches_cache(away_team_id)
        """)

def create_h2h_tables(conn):
    """Creates tables for H2H stats and history"""
    with conn.cursor() as cur:
        # Create h2h_stats table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS h2h_stats (
                team_pair_id SERIAL PRIMARY KEY,
                team1_id INTEGER,
                team2_id INTEGER,
                team1_name TEXT,
                team2_name TEXT,
                total_matches INTEGER DEFAULT 0,
                team1_wins INTEGER DEFAULT 0,
                team2_wins INTEGER DEFAULT 0,
                draws INTEGER DEFAULT 0,
                team1_goals INTEGER DEFAULT 0,
                team2_goals INTEGER DEFAULT 0,
                recent_matches JSONB,  -- Array of last 10 matches with timestamps
                last_updated TIMESTAMP,
                UNIQUE(team1_id, team2_id)
            )
        """)

        # Create h2h_history table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS h2h_history (
                match_id INTEGER PRIMARY KEY,
                h2h_draws_last_3 FLOAT,
                h2h_draws_last_5 FLOAT,
                h2h_draws_last_10 FLOAT,
                h2h_home_wins_last_3 FLOAT,
                h2h_home_wins_last_5 FLOAT,
                h2h_home_wins_last_10 FLOAT,
                h2h_away_wins_last_3 FLOAT,
                h2h_away_wins_last_5 FLOAT,
                h2h_away_wins_last_10 FLOAT,
                h2h_avg_total_goals FLOAT,
                h2h_avg_goal_diff FLOAT,
                h2h_home_goals_avg_last_3 FLOAT,
                h2h_home_goals_avg_last_5 FLOAT,
                h2h_home_goals_avg_last_10 FLOAT,
                h2h_away_goals_avg_last_3 FLOAT,
                h2h_away_goals_avg_last_5 FLOAT,
                h2h_away_goals_avg_last_10 FLOAT,
                h2h_both_teams_scored_rate FLOAT,
                h2h_zero_goal_rate FLOAT,
                raw_h2h_matches JSONB
            )
        """)

        # Add indexes for faster lookups
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_h2h_stats_team_pair
            ON h2h_stats(team1_id, team2_id)
        """)

def create_continent_elo_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS continent_elo_ratings (
            continent_name TEXT PRIMARY KEY,
            continent_elo_K5 INTEGER,
            continent_elo_K10 INTEGER,
            continent_elo_K20 INTEGER,
            continent_elo_K30 INTEGER,
            continent_elo_K40 INTEGER,
            continent_elo_K80 INTEGER
        )
    """)
    conn.commit()
    cursor.close()

def get_from_matches(conn, select_str, columns, where_clause=None, from_clause=None, order_by=None, limit=None, where_clause_args=None):
    """A dynamic function that gets data from the matches table.

    Args:
        conn (sqlite3.Connection): The database connection.
        columns (list): The columns to select.
        where_clause (str): The WHERE clause to filter the data.
        order_by (str): The ORDER BY clause to sort the data.
        limit (int): The LIMIT clause to limit the number of rows returned.
    """
    cursor = conn.cursor()

    columns_str = ', '.join(columns)
    select_str = f'{select_str} ' if select_str else ''
    where_clause_str = f'WHERE {where_clause}' if where_clause else ''
    from_clause_str = f'FROM {from_clause}' if from_clause else 'FROM matches'
    order_by_str = f'ORDER BY {order_by}' if order_by else ''
    limit_str = f'LIMIT {limit}' if limit else ''

    cursor.execute(f'{select_str} {columns_str} {from_clause_str} {where_clause_str} {order_by_str} {limit_str}')
    return cursor.fetchall()

def get_from_standings(conn, select_str, columns, where_clause=None, order_by=None, limit=None, where_clause_args=None):
    """A dynamic function that gets data from the standings table.

    Args:
        conn (sqlite3.Connection): The database connection.
        columns (list): The columns to select.
        where_clause (str): The WHERE clause to filter the data.
        order_by (str): The ORDER BY clause to sort the data.
        limit (int): The LIMIT clause to limit the number of rows returned.
    """
    cursor = conn.cursor()

    columns_str = ', '.join(columns)
    select_str = f'{select_str} ' if select_str else ''
    where_clause_str = f'WHERE {where_clause}' if where_clause else ''
    order_by_str = f'ORDER BY {order_by}' if order_by else ''
    limit_str = f'LIMIT {limit}' if limit else ''

    query = f'{select_str} {columns_str} FROM league_standings {where_clause_str} {order_by_str} {limit_str}'
    if where_clause_args:
        cursor.execute(query, where_clause_args)
    else:
        cursor.execute(query)
    return cursor.fetchall()

def load_from_postgres(
    engine,
    table: str,
    select: str = "*",
    where: str = None,
    drop_columns: list[str] = None,
    limit: int = None
) -> pd.DataFrame:
    """
    Load data from any PostgreSQL table using SQLAlchemy with flexible SELECT/WHERE/LIMIT clauses.
    Mostly used for loading data for training.
    #TODO: Use this function instead of the ones above

    Args:
        table (str): Table name to query.
        select (str): Comma-separated column list or "*" (default).
        where (str): Optional WHERE clause (without 'WHERE').
        drop_columns (list): List of column names to drop.
        limit (int): Optional LIMIT clause.

    Returns:
        pd.DataFrame: Resulting dataframe.
    """
    print(f"Loading data from {table}")
    query = f"SELECT {select} FROM {table}"
    if where:
        query += f" WHERE {where}"
    if limit:
        query += f" LIMIT {limit}"

    df = pd.read_sql_query(query, engine)

    if drop_columns:
        df.drop(columns=drop_columns, inplace=True, errors='ignore')

    return df

def update_processed_status(conn, match_ids, with_formation_flags, mode='training'):
    """Update processing status for processed matches"""
    cursor = conn.cursor()
    try:
        # Prepare data for bulk update
        update_data = [
            (match_id, True, with_formation, mode)
            for match_id, with_formation in zip(match_ids, with_formation_flags)
        ]

        cursor.executemany('''
            INSERT INTO processed_info (match_id, is_processed, with_formation, processing_mode)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (match_id) DO UPDATE SET
                is_processed = EXCLUDED.is_processed,
                with_formation = EXCLUDED.with_formation,
                processing_mode = EXCLUDED.processing_mode,
                processed_at = CURRENT_TIMESTAMP
        ''', update_data)

        conn.commit()
        print(f"Updated processing status for {len(match_ids)} matches")

    except Exception as e:
        print(f"Error updating processed status: {str(e)}")
        conn.rollback()
        raise
    finally:
        cursor.close()

def bulk_insert_formations(formations: list[dict], conn):
    """
    Bulk insert formations dictionaries into SQL table.

    Args:
        formations: List of dicts with keys:
                   - match_id (str)
                   - home_team_formation (str)
                   - away_team_formation (str)
        conn: Database connection
    """
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS formations (
        match_id TEXT PRIMARY KEY,
        home_team_formation TEXT,
        away_team_formation TEXT
    )
    """

    insert_sql = """
    INSERT INTO formations
        (match_id, home_team_formation, away_team_formation)
        VALUES (%s, %s, %s)
        ON CONFLICT (match_id)
        DO UPDATE SET
        home_team_formation = EXCLUDED.home_team_formation,
        away_team_formation = EXCLUDED.away_team_formation;
    """

    data = [
        (f['match_id'], f['home_team_formation'], f['away_team_formation'])
        for f in formations
    ]

    cursor = conn.cursor()
    cursor.execute(create_table_sql)
    cursor.executemany(insert_sql, data)
    conn.commit()

    print(f"Inserted/updated {len(data)} formations")

def bulk_insert_odds(conn, odds_records: list[dict[str, Any]]) -> int:
    """Bulk insert odds records using execute_values for better performance"""
    if not odds_records:
        return 0

    cursor = conn.cursor()

    try:
        values = [
            (
                record['match_id'],
                record['bookmaker_id'],
                record['bookmaker_name'],
                record['bet_type_id'],
                record['bet_type_name'],
                record['bet_value'],
                record['odds_value'],
                record['api_last_updated']
            )
            for record in odds_records
        ]

        insert_query = """
        INSERT INTO odds (
            match_id, bookmaker_id, bookmaker_name, bet_type_id,
            bet_type_name, bet_value, odds_value, api_last_updated
        ) VALUES %s
        """

        execute_values(cursor, insert_query, values, page_size=1000)
        conn.commit()

        rows_inserted = len(values)
        cursor.close()
        return rows_inserted

    except Exception as e:
        print(f"Error bulk inserting odds: {str(e)}")
        conn.rollback()
        cursor.close()
        return 0

def get_future_matches_with_odds(conn) -> list[int]:
    """Get match IDs for upcoming matches that have odds in the next 7 days."""
    cursor = conn.cursor()

    query = """
    SELECT match_id
    FROM matches
    WHERE has_odds = TRUE
    AND home_score IS NULL
    AND away_score IS NULL
    AND start_time > NOW()
    AND start_time <= NOW() + INTERVAL '7 days'
    ORDER BY start_time ASC
    """

    cursor.execute(query)
    # Handle both RealDictCursor (dictionaries) and regular cursor (tuples)
    rows = cursor.fetchall()
    if rows and isinstance(rows[0], dict):
        # RealDictCursor returns dictionaries
        match_ids = [row['match_id'] for row in rows]
    else:
        # Regular cursor returns tuples
        match_ids = [row[0] for row in rows]

    cursor.close()

    return match_ids

def drop_tables(conn):
    """Drops all processing tables"""
    table_names = [
        # 'teammatchhistory',
        # 'counter_table',
        # 'elo_history',
        # 'club_elo_ratings',
        # 'league_elo_ratings',
        # 'nation_elo_ratings',
        # 'continent_elo_ratings',
        # 'match_info_history',
        # 'stage_of_season_history',
        # 'form_history',
        # 'form_matches_cache',
        # 'h2h_history',
        # 'h2h_stats',
        # 'processed_info'

        # 'fatigue_history',
        # 'league_standings',
        # 'league_standings_history',
        # 'formations',
    ]

    with conn.cursor() as cur:
        for table in reversed(table_names):
            cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        conn.commit()

def drop_future_tables(conn):
    """Drops all future processing tables"""
    table_names = [
        # 'elo_future',
        # 'stage_of_season_future',
        # 'match_info_future',
        # 'league_standings_future',
        # 'formation_future',
        # 'form_future',
        # 'h2h_future',
    ]
    with conn.cursor() as cur:
        for table in reversed(table_names):
            cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        conn.commit()

def prune_old_future_features(conn, days_threshold=1):
    """
    Remove future features for matches that are more than X days in the past
    """
    cutoff_time = datetime.now() - timedelta(days=days_threshold)

    future_tables = [
        'elo_future',
        'formation_future',
        'stage_of_season_future',
        'match_info_future',
        #TODO: Add start time to these fields so that we can prune them
        # 'form_future',
        # 'h2h_future',
    ]

    cursor = conn.cursor()
    total_deleted = 0

    try:
        for table in future_tables:
            cursor.execute(f"""
                DELETE FROM {table}
                WHERE start_time < %s
            """, (cutoff_time,))

            deleted_count = cursor.rowcount
            total_deleted += deleted_count
            print(f"Deleted {deleted_count} old records from {table}")

        # Also clean up processed_info for inference mode
        cursor.execute("""
            DELETE FROM processed_info
            WHERE processing_mode = 'inference'
            AND match_id IN (
                SELECT match_id FROM matches
                WHERE start_time < %s
            )
        """, (cutoff_time,))

        deleted_processed = cursor.rowcount
        print(f"Deleted {deleted_processed} old processed_info records")

        conn.commit()
        print(f"Total deleted: {total_deleted} feature records + {deleted_processed} processed records")

    except Exception as e:
        print(f"Error pruning old features: {str(e)}")
        conn.rollback()
        raise
    finally:
        cursor.close()

def prune_all_future_features(conn):
    """
    Nuclear option: Delete ALL future features (for weekly cleanup)
    """
    future_tables = [
        'elo_future',
        'formation_future',
        'stage_of_season_future',
        'match_info_future'
    ]

    cursor = conn.cursor()
    total_deleted = 0

    try:
        for table in future_tables:
            cursor.execute(f"DELETE FROM {table}")
            deleted_count = cursor.rowcount
            total_deleted += deleted_count
            print(f"Deleted all {deleted_count} records from {table}")

        # Clean up processed_info for inference mode
        cursor.execute("DELETE FROM processed_info WHERE processing_mode = 'inference'")
        deleted_processed = cursor.rowcount

        conn.commit()
        print(f"Total deleted: {total_deleted} feature records + {deleted_processed} processed records")

    except Exception as e:
        print(f"Error pruning all features: {str(e)}")
        conn.rollback()
        raise
    finally:
        cursor.close()


def upsert_records(conn, table_name, records, conflict_keys, batch_size=1000):
    if not records:
        return

    columns = records[0].keys()
    update_columns = [col for col in columns if col not in conflict_keys]

    insert_query = f"""
        INSERT INTO {table_name} ({', '.join(columns)})
        VALUES %s
        ON CONFLICT ({', '.join(conflict_keys)}) DO UPDATE SET
        {', '.join([f"{col} = EXCLUDED.{col}" for col in update_columns])}
    """

    def batched(iterable, n):
        for i in range(0, len(iterable), n):
            yield iterable[i:i + n]

    with conn.cursor() as cursor:
        for batch in batched(records, batch_size):
            values = [tuple(record[col] for col in columns) for record in batch]
            execute_values(cursor, insert_query, values)
        conn.commit()

    print(f"Upserted {len(records)} records into {table_name}")

def save_predictions_to_db(conn, predictions_df, model_type='basic'):
    """
    Save match predictions to the database

    Args:
        conn: Database connection
        predictions_df: DataFrame with predictions
        model_type: 'basic' or 'with_formation'
    """
    logger = logging.getLogger(__name__)

    try:
        # Ensure the table exists
        create_match_result_predictions_table(conn)

        # Add model_type if not already present
        if 'model_type' not in predictions_df.columns:
            predictions_df = predictions_df.copy()
            predictions_df['model_type'] = model_type

        # Ensure we have the required columns
        required_columns = [
            'match_id', 'predicted_result', 'start_time',
            'home_team_name', 'away_team_name',
            'prob_home_win', 'prob_draw', 'prob_away_win',
            'model_type', 'prediction_timestamp'
        ]

        # Check if all required columns exist
        missing_columns = [col for col in required_columns if col not in predictions_df.columns]
        if missing_columns:
            logger.warning(f"Missing columns: {missing_columns}")
            # Add missing columns with default values
            for col in missing_columns:
                if col == 'prediction_timestamp':
                    predictions_df[col] = datetime.now()
                else:
                    predictions_df[col] = None

        # Convert DataFrame to records
        records = predictions_df[required_columns].to_dict('records')

        # Use existing upsert function
        upsert_records(
            conn=conn,
            table_name='match_result_predictions',
            records=records,
            conflict_keys=['match_id']
        )

        logger.info(f"Successfully saved {len(records)} predictions with model_type='{model_type}'")
        return True

    except Exception as e:
        logger.error(f"Failed to save predictions to database: {str(e)}")
        return False

def get_latest_predictions(conn, limit=None):
    """
    Get latest predictions from database

    Args:
        conn: Database connection
        limit: Optional limit on number of records

    Returns:
        List of prediction records
    """
    cursor = conn.cursor()

    query = """
        SELECT
            match_id, predicted_result, start_time,
            home_team_name, away_team_name,
            prob_home_win, prob_draw, prob_away_win,
            model_type, prediction_timestamp
        FROM match_result_predictions
        ORDER BY start_time ASC
    """

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    cursor.close()

    return results

def dict_to_sqlite(conn, table_name, data_dicts, batch_size=1000):
    """Insert a list of dictionaries into a SQLite table with match_id as INTEGER."""
    if not data_dicts:
        return

    cursor = conn.cursor()

    # Create table with proper types
    first = data_dicts[0]
    columns = []

    for k in first.keys():
        col_type = "INTEGER" if k == "match_id" else "TEXT"
        columns.append(f'"{k}" {col_type}')

    columns_sql = ", ".join(columns)
    cursor.execute(f'CREATE TABLE IF NOT EXISTS {table_name} ({columns_sql})')

    # Prepare insert statement
    placeholders = ', '.join(['?'] * len(first))  # Use '?' for SQLite
    columns_str = ', '.join(f'"{k}"' for k in first.keys())
    sql = f'INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})'

    # Ensure match_id is int before insertion
    for d in data_dicts:
        if "match_id" in d and d["match_id"] is not None:
            d["match_id"] = int(d["match_id"])

    # Batch insert
    for i in range(0, len(data_dicts), batch_size):
        batch = data_dicts[i:i+batch_size]
        try:
            cursor.executemany(sql, [tuple(d.values()) for d in batch])
            conn.commit()
        except sqlite3.IntegrityError as e:
            print(f"Skipping duplicate in batch {i//batch_size}: {str(e)}")
            conn.rollback()

def combine_stats(match_id, home_stats, away_stats):
    """A helper function to combine two dictionaries, prefix the data by either home_ or away_ and add match_id as the first key"""
    # Ensure match_id is first
    combined = {'match_id': match_id}

    # Add home stats
    combined.update(
        {f'home_{k}': v for k, v in home_stats.items()}
    )

    # Add away stats
    combined.update(
        {f'away_{k}': v for k, v in away_stats.items()}
    )

    return combined
