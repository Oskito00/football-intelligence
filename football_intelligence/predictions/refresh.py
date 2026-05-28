"""Prediction Refresh workflow for the Match Intelligence Lifecycle."""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from football_intelligence.features import (
    build_future_feature_set,
    build_historical_feature_set,
)
from football_intelligence.ingestion import SourceDataIngestion


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


def create_database_connection() -> Any:
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
    """Run Prediction inference without leaking CLI argv."""
    from football_intelligence.predictions.inference_entrypoint import (
        main as infer_results,
    )

    previous_argv = sys.argv[:]
    try:
        sys.argv = ["prediction-inference", model_config, "--mode", "inference"]
        infer_results(conn)
    finally:
        sys.argv = previous_argv


def build_prediction_refresh_steps(
    conn,
    model_config: str = DEFAULT_MODEL_CONFIG,
    include_odds: bool = True,
) -> list[PredictionRefreshStep]:
    """Build the current Prediction Refresh sequence."""
    source_data_ingestion = SourceDataIngestion()
    steps = [
        *(
            PredictionRefreshStep(step.name, step.action)
            for step in source_data_ingestion.match_data_steps(conn)
        ),
        PredictionRefreshStep(
            "build Historical Feature Set",
            lambda: build_historical_feature_set(conn),
        ),
        PredictionRefreshStep(
            "build Future Feature Set",
            lambda: build_future_feature_set(conn),
        ),
        PredictionRefreshStep(
            "run Prediction inference",
            lambda: run_result_model_inference(conn, model_config),
        ),
    ]

    if include_odds:
        odds_step = source_data_ingestion.odds_step(conn)
        steps.append(
            PredictionRefreshStep(
                odds_step.name,
                odds_step.action,
            )
        )

    return steps


def run_prediction_refresh(
    *,
    connection: Any | None = None,
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
