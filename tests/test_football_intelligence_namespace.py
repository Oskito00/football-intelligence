import importlib

import pytest


MIGRATION_HOMES = (
    "football_intelligence.analyst",
    "football_intelligence.ingestion",
    "football_intelligence.features",
    "football_intelligence.predictions",
    "football_intelligence.api",
    "football_intelligence.database",
    "football_intelligence.cli",
)

LEGACY_ENTRYPOINTS = (
    ("scheduler.scheduler", "main"),
)

LEGACY_MODULE_ALIASES = (
    ("helpers.parsing_helpers.list", "utils.parsing.list"),
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


@pytest.mark.parametrize(("module_name", "attribute_name"), LEGACY_ENTRYPOINTS)
def test_legacy_entrypoint_imports_still_work(module_name, attribute_name):
    module = importlib.import_module(module_name)

    assert hasattr(module, attribute_name)


@pytest.mark.parametrize(("alias_name", "canonical_name"), LEGACY_MODULE_ALIASES)
def test_legacy_module_aliases_keep_old_import_paths_compatible(
    alias_name,
    canonical_name,
):
    alias_module = importlib.import_module(alias_name)
    canonical_module = importlib.import_module(canonical_name)

    assert alias_module is canonical_module


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
