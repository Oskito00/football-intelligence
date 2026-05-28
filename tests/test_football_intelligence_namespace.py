import importlib
from pathlib import Path

import pytest

from tests.import_audit import find_imports_matching, is_module_or_child


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_HOMES = (
    "football_intelligence.analyst",
    "football_intelligence.ingestion",
    "football_intelligence.features",
    "football_intelligence.predictions",
    "football_intelligence.api",
    "football_intelligence.database",
    "football_intelligence.cli",
)

ACTIVE_RUNTIME_ROOTS = (
    PROJECT_ROOT / "football_intelligence",
)
PROHIBITED_IMPLEMENTATION_MODULES = (
    "data_scraping",
    "data_processing",
    "ml_pipeline",
    "utils.database",
    "chatbot",
    "scheduler",
)


def test_football_intelligence_namespace_exposes_product_name():
    package = importlib.import_module("football_intelligence")

    assert package.PRODUCT_NAME == "Football Intelligence Agent"


@pytest.mark.parametrize("module_name", MIGRATION_HOMES)
def test_football_intelligence_namespace_exposes_migration_homes(module_name):
    module = importlib.import_module(module_name)

    assert module.__doc__


def test_analyst_namespace_does_not_export_legacy_chatbot_compatibility():
    import football_intelligence.analyst as analyst

    assert "LegacyAnalystAgent" not in analyst.__all__
    assert "LegacyFunctionDispatcher" not in analyst.__all__
    assert "LegacyMemoryManager" not in analyst.__all__


def test_analyst_namespace_exposes_read_only_tools():
    from football_intelligence.analyst import (
        ANALYST_TOOL_DEFINITIONS,
        AnalystAgent,
        AnalystAgentResponse,
        AnalystFootballTools,
        AnalystToolCall,
        AnalystToolDefinition,
    )
    from football_intelligence.analyst.agent import (
        AnalystAgent as ModuleAnalystAgent,
        AnalystAgentResponse as ModuleAnalystAgentResponse,
        AnalystToolCall as ModuleAnalystToolCall,
    )
    from football_intelligence.analyst.tools import (
        ANALYST_TOOL_DEFINITIONS as ModuleAnalystToolDefinitions,
        AnalystFootballTools as ModuleAnalystFootballTools,
        AnalystToolDefinition as ModuleAnalystToolDefinition,
    )

    assert ANALYST_TOOL_DEFINITIONS is ModuleAnalystToolDefinitions
    assert AnalystAgent is ModuleAnalystAgent
    assert AnalystAgentResponse is ModuleAnalystAgentResponse
    assert AnalystFootballTools is ModuleAnalystFootballTools
    assert AnalystToolCall is ModuleAnalystToolCall
    assert AnalystToolDefinition is ModuleAnalystToolDefinition


def test_database_namespace_exposes_read_only_football_queries():
    from football_intelligence.database import (
        FootballQueryError,
        PostgresReadOnlyRunner,
        ReadOnlyFootballQueries,
    )
    from football_intelligence.database.football import (
        FootballQueryError as ModuleFootballQueryError,
        PostgresReadOnlyRunner as ModulePostgresReadOnlyRunner,
        ReadOnlyFootballQueries as ModuleReadOnlyFootballQueries,
    )

    assert FootballQueryError is ModuleFootballQueryError
    assert PostgresReadOnlyRunner is ModulePostgresReadOnlyRunner
    assert ReadOnlyFootballQueries is ModuleReadOnlyFootballQueries


def test_cli_namespace_does_not_export_legacy_scheduler_compatibility():
    import football_intelligence.cli as cli

    assert "run_legacy_prediction_refresh" not in cli.__all__
    assert not hasattr(cli, "run_legacy_prediction_refresh")


def test_active_runtime_imports_only_use_product_namespace_for_migrated_areas():
    offenders = find_imports_matching(
        ACTIVE_RUNTIME_ROOTS,
        _is_prohibited_implementation_module,
        PROJECT_ROOT,
    )

    assert offenders == []


def test_remaining_experiment_source_is_outside_active_runtime_audit():
    assert (PROJECT_ROOT / "ml_pipeline_cnn" / "main_train.py").exists()
    assert PROJECT_ROOT / "ml_pipeline_cnn" not in ACTIVE_RUNTIME_ROOTS


def test_retired_helper_alias_package_is_deleted():
    assert not (PROJECT_ROOT / "helpers" / "parsing_helpers").exists()


def _is_prohibited_implementation_module(module_name):
    return any(
        is_module_or_child(module_name, prohibited)
        for prohibited in PROHIBITED_IMPLEMENTATION_MODULES
    )
