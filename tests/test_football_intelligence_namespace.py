import importlib


def test_football_intelligence_namespace_exposes_migration_homes():
    package = importlib.import_module("football_intelligence")

    assert package.PRODUCT_NAME == "Football Intelligence Agent"

    for module_name in [
        "football_intelligence.analyst",
        "football_intelligence.ingestion",
        "football_intelligence.features",
        "football_intelligence.predictions",
        "football_intelligence.api",
        "football_intelligence.database",
        "football_intelligence.cli",
    ]:
        module = importlib.import_module(module_name)
        assert module.__doc__


def test_analyst_namespace_keeps_legacy_chatbot_import_compatible():
    from chatbot.core.chatbot import FootballChatbot
    from football_intelligence.analyst import LegacyAnalystAgent

    assert LegacyAnalystAgent is FootballChatbot


def test_legacy_entrypoint_imports_still_work():
    entrypoints = {
        "chatbot.api": "app",
        "chatbot.main": "main",
        "scheduler.scheduler": "main",
        "ml_pipeline.main_infer": "main",
    }

    for module_name, attribute_name in entrypoints.items():
        module = importlib.import_module(module_name)
        assert hasattr(module, attribute_name)
