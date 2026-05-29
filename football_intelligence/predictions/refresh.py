"""Prediction Refresh workflow for the Match Intelligence Lifecycle."""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from football_intelligence.features import (
    build_future_feature_set,
    build_historical_feature_set,
)
from football_intelligence.ingestion import SourceDataIngestion


DEFAULT_MODEL_CONFIG = "result_model_early"

STEP_LEAGUE_CATALOGUE = "league-catalogue"
STEP_CURRENT_MATCH_DATA = "current-match-data"
STEP_HISTORICAL_FEATURES = "historical-features"
STEP_FUTURE_FEATURES = "future-features"
STEP_INFERENCE = "inference"
STEP_ODDS = "odds"

STEP_SOURCE_DATA = "source-data"
STEP_FEATURES = "features"
STEP_SOURCE_DATA_INGESTION = "source-data-ingestion"
STEP_HISTORICAL_FEATURE_SET = "historical-feature-set"
STEP_FUTURE_FEATURE_SET = "future-feature-set"
STEP_PREDICTION_INFERENCE = "prediction-inference"
STEP_ODDS_REFRESH = "odds-refresh"

PREDICTION_REFRESH_STEP_GROUPS = {
    STEP_SOURCE_DATA: (
        STEP_LEAGUE_CATALOGUE,
        STEP_CURRENT_MATCH_DATA,
    ),
    STEP_FEATURES: (
        STEP_HISTORICAL_FEATURES,
        STEP_FUTURE_FEATURES,
    ),
    STEP_SOURCE_DATA_INGESTION: (
        STEP_LEAGUE_CATALOGUE,
        STEP_CURRENT_MATCH_DATA,
    ),
    STEP_HISTORICAL_FEATURE_SET: (STEP_HISTORICAL_FEATURES,),
    STEP_FUTURE_FEATURE_SET: (STEP_FUTURE_FEATURES,),
    STEP_PREDICTION_INFERENCE: (STEP_INFERENCE,),
    STEP_ODDS_REFRESH: (STEP_ODDS,),
}

PREDICTION_REFRESH_STEP_HELP = (
    (STEP_SOURCE_DATA, "refresh league catalogue and current match data"),
    (STEP_FEATURES, "rebuild Historical and Future Feature Sets"),
    (STEP_INFERENCE, "run Prediction inference only"),
    (STEP_ODDS, "refresh future match odds only"),
    (STEP_LEAGUE_CATALOGUE, "refresh available API-Football leagues"),
    (STEP_CURRENT_MATCH_DATA, "refresh current-season match data"),
    (STEP_HISTORICAL_FEATURES, "rebuild the Historical Feature Set"),
    (STEP_FUTURE_FEATURES, "rebuild the Future Feature Set"),
)

AVAILABLE_PREDICTION_REFRESH_SELECTORS = tuple(
    dict.fromkeys(
        [
            *(selector for selector, _description in PREDICTION_REFRESH_STEP_HELP),
            *PREDICTION_REFRESH_STEP_GROUPS,
        ]
    )
)

_STEP_NAME_KEYS = {
    "refresh league catalogue": STEP_LEAGUE_CATALOGUE,
    "refresh current match data": STEP_CURRENT_MATCH_DATA,
    "build Historical Feature Set": STEP_HISTORICAL_FEATURES,
    "build Future Feature Set": STEP_FUTURE_FEATURES,
    "run Prediction inference": STEP_INFERENCE,
    "refresh odds": STEP_ODDS,
}


@dataclass(frozen=True)
class PredictionRefreshStep:
    """A named operation in the Prediction Refresh workflow."""

    name: str
    action: Callable[[], None]
    key: str | None = None


@dataclass(frozen=True)
class PredictionRefreshResult:
    """Summary of a completed Prediction Refresh run."""

    steps_run: tuple[str, ...]
    steps_failed: tuple[str, ...] = ()


StepFactory = Callable[
    [Any, str, bool, Sequence[str] | None],
    Iterable[PredictionRefreshStep],
]
ConnectionFactory = Callable[[], Any]


def resolve_prediction_refresh_step_keys(
    selected_steps: Sequence[str] | None,
) -> frozenset[str] | None:
    """Resolve CLI step selectors into concrete workflow step keys."""
    if selected_steps is None:
        return None

    resolved: set[str] = set()
    for selected_step in selected_steps:
        if selected_step in PREDICTION_REFRESH_STEP_GROUPS:
            resolved.update(PREDICTION_REFRESH_STEP_GROUPS[selected_step])
        elif selected_step in AVAILABLE_PREDICTION_REFRESH_SELECTORS:
            resolved.add(selected_step)
        else:
            options = ", ".join(AVAILABLE_PREDICTION_REFRESH_SELECTORS)
            raise ValueError(
                f"Unknown Prediction Refresh part '{selected_step}'. "
                f"Available parts: {options}"
            )

    return frozenset(resolved)


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
    selected_steps: Sequence[str] | None = None,
) -> list[PredictionRefreshStep]:
    """Build the current Prediction Refresh sequence."""
    selected_step_keys = resolve_prediction_refresh_step_keys(selected_steps)
    source_data_ingestion = SourceDataIngestion()
    steps = [
        *(
            PredictionRefreshStep(
                step.name,
                step.action,
                _STEP_NAME_KEYS.get(step.name),
            )
            for step in source_data_ingestion.match_data_steps(conn)
        ),
        PredictionRefreshStep(
            "build Historical Feature Set",
            lambda: build_historical_feature_set(conn),
            STEP_HISTORICAL_FEATURES,
        ),
        PredictionRefreshStep(
            "build Future Feature Set",
            lambda: build_future_feature_set(conn),
            STEP_FUTURE_FEATURES,
        ),
        PredictionRefreshStep(
            "run Prediction inference",
            lambda: run_result_model_inference(conn, model_config),
            STEP_INFERENCE,
        ),
    ]

    should_include_odds = include_odds or (
        selected_step_keys is not None and STEP_ODDS in selected_step_keys
    )
    if should_include_odds:
        odds_step = source_data_ingestion.odds_step(conn)
        steps.append(
            PredictionRefreshStep(
                odds_step.name,
                odds_step.action,
                _STEP_NAME_KEYS.get(odds_step.name, STEP_ODDS),
            )
        )

    if selected_step_keys is not None:
        steps = [
            step
            for step in steps
            if (step.key or _STEP_NAME_KEYS.get(step.name)) in selected_step_keys
        ]

    return steps


def run_prediction_refresh(
    *,
    connection: Any | None = None,
    connection_factory: ConnectionFactory = create_database_connection,
    model_config: str = DEFAULT_MODEL_CONFIG,
    include_odds: bool = True,
    selected_steps: Sequence[str] | None = None,
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
        for step in step_factory(conn, model_config, include_odds, selected_steps):
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
