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
    ("chatbot.api", "app"),
    ("chatbot.main", "main"),
    ("scheduler.scheduler", "main"),
    ("ml_pipeline.main_infer", "main"),
)

LEGACY_MODULE_ALIASES = (
    (
        "helpers.data_processing.processing_functions.elo_manager",
        "data_processing.helpers.processing_functions.elo_manager",
    ),
    ("helpers.parsing_helpers.list", "utils.parsing.list"),
)


def test_football_intelligence_namespace_exposes_product_name():
    package = importlib.import_module("football_intelligence")

    assert package.PRODUCT_NAME == "Football Intelligence Agent"


@pytest.mark.parametrize("module_name", MIGRATION_HOMES)
def test_football_intelligence_namespace_exposes_migration_homes(module_name):
    module = importlib.import_module(module_name)

    assert module.__doc__


def test_analyst_namespace_keeps_legacy_chatbot_import_compatible():
    from chatbot.core.chatbot import FootballChatbot
    from football_intelligence.analyst import LegacyAnalystAgent

    assert LegacyAnalystAgent is FootballChatbot


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


def test_legacy_database_helper_wrapper_keeps_old_import_path_compatible():
    from utils.database.get_and_set_functions import get_from_matches
    from utils.database_helpers.get_and_set_functions import (
        get_from_matches as legacy_get_from_matches,
    )

    assert legacy_get_from_matches is get_from_matches
