"""Shared feature pipeline for Historical and Future Feature Sets."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from contextlib import ExitStack
from dataclasses import dataclass
from enum import Enum
from typing import Any


DEFAULT_BATCH_SIZE = 1000
FUTURE_PRUNE_DAYS = 2

MatchRow = dict[str, Any]
ManagerFactory = Callable[..., Any]


class FeatureSetMode(Enum):
    """Feature set modes supported by the shared pipeline."""

    HISTORICAL = "historical"
    FUTURE = "future"


@dataclass(frozen=True)
class FeaturePipelineResult:
    """Summary of a feature pipeline run."""

    feature_set: FeatureSetMode
    processing_mode: str
    matches_found: int
    matches_processed: int
    batches_processed: int


@dataclass(frozen=True)
class FeaturePipelineDependencies:
    """Runtime dependencies used by the feature pipeline."""

    get_matches: Callable[..., Sequence[MatchRow]]
    update_processed_status: Callable[[Any, list[Any], list[bool], str], None]
    drop_historical_tables: Callable[[Any], None]
    create_historical_tables: Callable[[Any], None]
    process_matches_to_history: Callable[[Any, int], None]
    drop_future_tables: Callable[[Any], None]
    create_future_tables: Callable[[Any], None]
    prune_old_future_features: Callable[[Any, int], None]
    match_info_manager: ManagerFactory
    stage_of_season_manager: ManagerFactory
    formation_manager: ManagerFactory
    elo_manager: ManagerFactory
    form_manager: ManagerFactory
    h2h_manager: ManagerFactory


@dataclass(frozen=True)
class _FeatureSetConfig:
    feature_set: FeatureSetMode
    processing_mode: str
    display_name: str
    columns: tuple[str, ...]
    where_clause: str
    order_by: str
    select_str: str = "SELECT DISTINCT"
    from_clause: str | None = None


_HISTORICAL_CONFIG = _FeatureSetConfig(
    feature_set=FeatureSetMode.HISTORICAL,
    processing_mode="training",
    display_name="Historical Feature Set",
    columns=(
        "m.match_id",
        "m.start_time",
        "m.competition_id",
        "m.competition_name",
        "m.competition_country",
        "m.competition_season_name",
        "m.season_start_date",
        "m.season_end_date",
        "m.home_team_id",
        "m.home_team_name",
        "m.away_team_id",
        "m.away_team_name",
        "m.home_score",
        "m.away_score",
        "m.home_team_domestic_league_id",
        "m.home_team_domestic_country",
        "m.away_team_domestic_league_id",
        "m.away_team_domestic_country",
        "m.home_team_formation",
        "m.away_team_formation",
    ),
    from_clause="""matches m
            LEFT JOIN processed_info p ON (
                m.match_id = p.match_id
                AND p.is_processed = true
                AND p.processing_mode = 'training'
            )""",
    where_clause="""
            m.home_score IS NOT NULL AND m.away_score IS NOT NULL
            AND p.match_id IS NULL
        """,
    order_by="m.start_time",
)

_FUTURE_CONFIG = _FeatureSetConfig(
    feature_set=FeatureSetMode.FUTURE,
    processing_mode="inference",
    display_name="Future Feature Set",
    columns=(
        "match_id",
        "start_time",
        "competition_id",
        "competition_name",
        "competition_country",
        "competition_season_name",
        "season_start_date",
        "season_end_date",
        "home_team_id",
        "home_team_name",
        "away_team_id",
        "away_team_name",
        "home_team_domestic_league_id",
        "home_team_domestic_country",
        "away_team_domestic_league_id",
        "away_team_domestic_country",
        "home_team_formation",
        "away_team_formation",
    ),
    where_clause="""
            home_score IS NULL
            AND away_score IS NULL
            AND match_status = 'NS'
            AND start_time > NOW()
            AND start_time < NOW() + INTERVAL ' 7 days'
            AND match_id NOT IN (
                SELECT match_id FROM processed_info
                WHERE is_processed = true AND processing_mode = 'inference' AND with_formation = true
            )
        """,
    order_by="start_time",
)

_CONFIG_BY_MODE = {
    FeatureSetMode.HISTORICAL: _HISTORICAL_CONFIG,
    FeatureSetMode.FUTURE: _FUTURE_CONFIG,
}

_FEATURE_SET_ALIASES = {
    "historical": FeatureSetMode.HISTORICAL,
    "historical_feature_set": FeatureSetMode.HISTORICAL,
    "completed_matches": FeatureSetMode.HISTORICAL,
    "training": FeatureSetMode.HISTORICAL,
    "future": FeatureSetMode.FUTURE,
    "future_feature_set": FeatureSetMode.FUTURE,
    "upcoming_matches": FeatureSetMode.FUTURE,
    "inference": FeatureSetMode.FUTURE,
}


def default_feature_pipeline_dependencies() -> FeaturePipelineDependencies:
    """Build the production dependency bundle for the feature pipeline."""
    from data_processing.helpers.processing_functions.elo_manager import EloManager
    from data_processing.helpers.processing_functions.form_manager import FormManager
    from data_processing.helpers.processing_functions.formation_manager import (
        FormationManager,
    )
    from data_processing.helpers.processing_functions.h2h_manager import H2HManager
    from data_processing.helpers.processing_functions.match_history import (
        process_matches_to_history,
    )
    from data_processing.helpers.processing_functions.match_info_manager import (
        MatchInfoManager,
    )
    from data_processing.helpers.processing_functions.stage_of_season_manager import (
        StageOfSeasonManager,
    )
    from utils.database.clean_tables import drop_future_tables, drop_tables
    from utils.database.create_tables import create_future_tables, create_tables
    from utils.database.get_and_set_functions import (
        get_from_matches,
        update_processed_status,
    )
    from utils.database.prune_future_features import prune_old_future_features

    return FeaturePipelineDependencies(
        get_matches=get_from_matches,
        update_processed_status=update_processed_status,
        drop_historical_tables=drop_tables,
        create_historical_tables=create_tables,
        process_matches_to_history=process_matches_to_history,
        drop_future_tables=drop_future_tables,
        create_future_tables=create_future_tables,
        prune_old_future_features=prune_old_future_features,
        match_info_manager=MatchInfoManager,
        stage_of_season_manager=StageOfSeasonManager,
        formation_manager=FormationManager,
        elo_manager=EloManager,
        form_manager=FormManager,
        h2h_manager=H2HManager,
    )


def run_feature_pipeline(
    conn: Any,
    feature_set: FeatureSetMode | str,
    *,
    dependencies: FeaturePipelineDependencies | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> FeaturePipelineResult:
    """Run one feature pipeline mode through the shared lifecycle."""
    if batch_size < 1:
        raise ValueError("batch_size must be greater than zero")

    mode = _resolve_feature_set_mode(feature_set)
    config = _CONFIG_BY_MODE[mode]
    dependencies = dependencies or default_feature_pipeline_dependencies()

    _prepare_feature_set(conn, config, dependencies)

    matches = _get_unprocessed_matches(conn, config, dependencies)
    matches_found = len(matches)

    if not matches:
        print("No matches to process")
        return FeaturePipelineResult(
            feature_set=mode,
            processing_mode=config.processing_mode,
            matches_found=0,
            matches_processed=0,
            batches_processed=0,
        )

    if mode is FeatureSetMode.HISTORICAL:
        dependencies.process_matches_to_history(conn, batch_size=batch_size)

    matches_processed = 0
    batches_processed = 0
    total_batches = ((matches_found - 1) // batch_size) + 1

    for batch_index, batch in enumerate(_iter_batches(matches, batch_size), start=1):
        print(f"Processing {config.display_name} batch {batch_index} of {total_batches}")
        _process_batch(conn, batch, config, dependencies)
        matches_processed += len(batch)
        batches_processed += 1

    return FeaturePipelineResult(
        feature_set=mode,
        processing_mode=config.processing_mode,
        matches_found=matches_found,
        matches_processed=matches_processed,
        batches_processed=batches_processed,
    )


def build_historical_feature_set(
    conn: Any,
    *,
    dependencies: FeaturePipelineDependencies | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> FeaturePipelineResult:
    """Build the Historical Feature Set from Completed Matches."""
    return run_feature_pipeline(
        conn,
        FeatureSetMode.HISTORICAL,
        dependencies=dependencies,
        batch_size=batch_size,
    )


def build_future_feature_set(
    conn: Any,
    *,
    dependencies: FeaturePipelineDependencies | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> FeaturePipelineResult:
    """Build the Future Feature Set from Upcoming Matches."""
    return run_feature_pipeline(
        conn,
        FeatureSetMode.FUTURE,
        dependencies=dependencies,
        batch_size=batch_size,
    )


def _resolve_feature_set_mode(feature_set: FeatureSetMode | str) -> FeatureSetMode:
    if isinstance(feature_set, FeatureSetMode):
        return feature_set

    normalized = feature_set.strip().lower().replace("-", "_")
    try:
        return _FEATURE_SET_ALIASES[normalized]
    except KeyError as exc:
        raise ValueError(f"Unknown feature set mode: {feature_set!r}") from exc


def _get_unprocessed_matches(
    conn: Any,
    config: _FeatureSetConfig,
    dependencies: FeaturePipelineDependencies,
) -> list[MatchRow]:
    return list(
        dependencies.get_matches(
            conn,
            select_str=config.select_str,
            columns=list(config.columns),
            from_clause=config.from_clause,
            where_clause=config.where_clause,
            order_by=config.order_by,
        )
    )


def _iter_batches(
    matches: Sequence[MatchRow],
    batch_size: int,
) -> Iterator[Sequence[MatchRow]]:
    for start in range(0, len(matches), batch_size):
        yield matches[start : start + batch_size]


def _prepare_feature_set(
    conn: Any,
    config: _FeatureSetConfig,
    dependencies: FeaturePipelineDependencies,
) -> None:
    if config.feature_set is FeatureSetMode.HISTORICAL:
        dependencies.drop_historical_tables(conn)
        dependencies.create_historical_tables(conn)
        print("Getting Completed Matches")
        return

    dependencies.drop_future_tables(conn)
    dependencies.create_future_tables(conn)
    print("Pruning old future features...")
    dependencies.prune_old_future_features(conn, days_threshold=FUTURE_PRUNE_DAYS)


def _process_batch(
    conn: Any,
    batch: Sequence[MatchRow],
    config: _FeatureSetConfig,
    dependencies: FeaturePipelineDependencies,
) -> None:
    with ExitStack() as stack:
        match_info_manager = stack.enter_context(
            dependencies.match_info_manager(conn, batch, mode=config.processing_mode)
        )
        stage_of_season_manager = stack.enter_context(
            dependencies.stage_of_season_manager(conn, batch, mode=config.processing_mode)
        )
        formation_manager = stack.enter_context(
            dependencies.formation_manager(conn, batch, mode=config.processing_mode)
        )
        elo_manager = stack.enter_context(
            dependencies.elo_manager(conn, batch, mode=config.processing_mode)
        )
        form_manager = stack.enter_context(
            dependencies.form_manager(
                conn,
                batch,
                mode=config.processing_mode,
                elo_manager=elo_manager,
            )
        )
        h2h_manager = stack.enter_context(
            dependencies.h2h_manager(conn, batch, mode=config.processing_mode)
        )

        match_ids: list[Any] = []
        with_formation_flags: list[bool] = []

        for match in batch:
            match_info_manager.process_match(match)
            stage_of_season_manager.process_match(match)
            form_manager.process_match(match)
            elo_manager.process_match(match)
            h2h_manager.process_match(match)

            has_formation = bool(
                match.get("home_team_formation") and match.get("away_team_formation")
            )
            if has_formation:
                formation_manager.process_match(match)

            match_ids.append(match["match_id"])
            with_formation_flags.append(has_formation)

    dependencies.update_processed_status(
        conn,
        match_ids,
        with_formation_flags,
        mode=config.processing_mode,
    )
