from football_intelligence.ingestion import (
    SourceDataIngestion,
    default_source_data_provider,
)
from football_intelligence.ingestion.api_football import ApiFootballSourceDataProvider


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
