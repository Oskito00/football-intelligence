"""Prediction Refresh workflow for the Match Intelligence Lifecycle."""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any


DEFAULT_MODEL_CONFIG = "result_model_early"


@dataclass(frozen=True)
class PredictionRefreshStep:
    """A named operation in the Prediction Refresh workflow."""

    name: str
    action: Callable[[], None]


@dataclass(frozen=True)
class PredictionRefreshResult:
    """Summary of a completed Prediction Refresh run."""

    steps_run: tuple[str, ...]
    steps_failed: tuple[str, ...] = ()


StepFactory = Callable[[Any, str, bool], Iterable[PredictionRefreshStep]]
ConnectionFactory = Callable[[], Any]


def create_database_connection():
    """Create the database connection used by operational refresh steps."""
    import psycopg2
    from psycopg2.extras import RealDictCursor

    from config import get_config

    config = get_config()
    return psycopg2.connect(
        host=config.DB_HOST,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        cursor_factory=RealDictCursor,
    )


def run_result_model_inference(conn, model_config: str = DEFAULT_MODEL_CONFIG) -> None:
    """Run inference through the legacy entrypoint without leaking CLI argv."""
    from ml_pipeline.main_infer import main as infer_results

    previous_argv = sys.argv[:]
    try:
        sys.argv = ["main_infer.py", model_config, "--mode", "inference"]
        infer_results(conn)
    finally:
        sys.argv = previous_argv


def build_prediction_refresh_steps(
    conn,
    model_config: str = DEFAULT_MODEL_CONFIG,
    include_odds: bool = True,
) -> list[PredictionRefreshStep]:
    """Build the current Prediction Refresh sequence around legacy behavior."""
    from data_processing.for_inferencing.match_result_features import (
        process_future_matches,
    )
    from data_processing.for_training.match_result_features import process_matches
    from data_scraping.api_football.all_data.scrape_league_ids import (
        get_all_leagues_on_api,
    )
    from data_scraping.api_football.current_season.current_seasons_scrape import (
        scrape_current_seasons,
    )
    from data_scraping.api_football.odds.scrape_future_match_odds import (
        scrape_future_match_odds,
    )

    steps = [
        PredictionRefreshStep(
            "refresh league catalogue",
            lambda: get_all_leagues_on_api(conn),
        ),
        PredictionRefreshStep(
            "refresh current match data",
            scrape_current_seasons,
        ),
        PredictionRefreshStep(
            "build Historical Feature Set",
            lambda: process_matches(conn),
        ),
        PredictionRefreshStep(
            "build Future Feature Set",
            lambda: process_future_matches(conn),
        ),
        PredictionRefreshStep(
            "run Prediction inference",
            lambda: run_result_model_inference(conn, model_config),
        ),
    ]

    if include_odds:
        steps.append(
            PredictionRefreshStep(
                "refresh odds",
                lambda: scrape_future_match_odds(conn),
            )
        )

    return steps


def run_prediction_refresh(
    *,
    connection=None,
    connection_factory: ConnectionFactory = create_database_connection,
    model_config: str = DEFAULT_MODEL_CONFIG,
    include_odds: bool = True,
    step_factory: StepFactory = build_prediction_refresh_steps,
    logger: logging.Logger | None = None,
    continue_on_error: bool = True,
) -> PredictionRefreshResult:
    """Run Prediction Refresh without performing Model Training."""
    logger = logger or logging.getLogger(__name__)
    should_close_connection = connection is None
    conn = connection if connection is not None else connection_factory()
    steps_run: list[str] = []
    steps_failed: list[str] = []

    try:
        for step in step_factory(conn, model_config, include_odds):
            logger.info("Starting %s", step.name)
            try:
                step.action()
            except Exception:
                steps_failed.append(step.name)
                logger.exception("Error in %s", step.name)
                if not continue_on_error:
                    raise
            else:
                steps_run.append(step.name)
                logger.info("Completed %s", step.name)
    finally:
        if should_close_connection and conn is not None:
            conn.close()

    return PredictionRefreshResult(
        steps_run=tuple(steps_run),
        steps_failed=tuple(steps_failed),
    )
