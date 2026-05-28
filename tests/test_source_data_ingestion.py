import ast
from pathlib import Path

from football_intelligence.ingestion import (
    SourceDataIngestion,
    default_source_data_provider,
)
from football_intelligence.ingestion.api_football import ApiFootballSourceDataProvider


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FOOTBALL_INTELLIGENCE_PACKAGE = PROJECT_ROOT / "football_intelligence"
RETIRED_SOURCE_DATA_PACKAGE = PROJECT_ROOT / "data_scraping"


class RecordingProvider:
    def __init__(self):
        self.calls = []

    def refresh_league_catalogue(self, conn):
        self.calls.append(("league-catalogue", conn))

    def refresh_current_match_data(self):
        self.calls.append(("current-match-data",))

    def refresh_match_odds(self, conn):
        self.calls.append(("match-odds", conn))


def test_source_data_ingestion_workflow_delegates_to_provider_without_api_calls():
    conn = object()
    provider = RecordingProvider()
    ingestion = SourceDataIngestion(provider=provider)

    for step in ingestion.match_data_steps(conn):
        step.action()
    ingestion.odds_step(conn).action()

    assert [step.name for step in ingestion.match_data_steps(conn)] == [
        "refresh league catalogue",
        "refresh current match data",
    ]
    assert ingestion.odds_step(conn).name == "refresh odds"
    assert provider.calls == [
        ("league-catalogue", conn),
        ("current-match-data",),
        ("match-odds", conn),
    ]


def test_default_source_data_provider_is_api_football_adapter():
    assert isinstance(default_source_data_provider(), ApiFootballSourceDataProvider)


def test_ingestion_namespace_only_exports_product_level_interfaces():
    from football_intelligence import ingestion

    assert "get_all_leagues_on_api" not in ingestion.__all__
    assert "scrape_current_seasons" not in ingestion.__all__
    assert "scrape_future_match_odds" not in ingestion.__all__
    assert not hasattr(ingestion, "get_all_leagues_on_api")
    assert not hasattr(ingestion, "scrape_current_seasons")
    assert not hasattr(ingestion, "scrape_future_match_odds")


def test_retired_source_data_ingestion_package_is_deleted():
    assert not RETIRED_SOURCE_DATA_PACKAGE.exists()


def test_active_runtime_imports_do_not_use_retired_source_data_paths():
    offenders = []

    for path in FOOTBALL_INTELLIGENCE_PACKAGE.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue

        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_retired_source_data_module(alias.name):
                        offenders.append((path.relative_to(PROJECT_ROOT), alias.name))
            elif isinstance(node, ast.ImportFrom) and node.module:
                if _is_retired_source_data_module(node.module):
                    offenders.append((path.relative_to(PROJECT_ROOT), node.module))

    assert offenders == []


def _is_retired_source_data_module(module_name):
    return module_name == "data_scraping" or module_name.startswith("data_scraping.")
