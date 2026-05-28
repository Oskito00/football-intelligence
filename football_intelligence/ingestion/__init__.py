"""Source Data Ingestion workflows for the Match Intelligence Lifecycle."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from football_intelligence._compat import LegacyExport, make_legacy_getattr


_SOURCE_DATA_EXPORTS = {
    "get_all_leagues_on_api": LegacyExport(
        "football_intelligence.ingestion.api_football",
        "get_all_leagues_on_api",
    ),
    "scrape_current_seasons": LegacyExport(
        "football_intelligence.ingestion.api_football",
        "scrape_current_seasons",
    ),
    "scrape_future_match_odds": LegacyExport(
        "football_intelligence.ingestion.api_football",
        "scrape_future_match_odds",
    ),
}


@dataclass(frozen=True)
class SourceDataIngestionStep:
    """A named Source Data Ingestion operation."""

    name: str
    action: Callable[[], None]


class SourceDataProvider(Protocol):
    """Provider-specific behavior needed by Source Data Ingestion."""

    def refresh_league_catalogue(self, conn: Any) -> None:
        """Refresh the provider's league catalogue."""

    def refresh_current_match_data(self) -> None:
        """Refresh current source match data."""

    def refresh_match_odds(self, conn: Any) -> None:
        """Refresh provider odds for Upcoming Matches."""


def default_source_data_provider() -> SourceDataProvider:
    """Build the default API-Football provider adapter."""
    from football_intelligence.ingestion.api_football import ApiFootballSourceDataProvider

    return ApiFootballSourceDataProvider()


class SourceDataIngestion:
    """Product-level Source Data Ingestion workflow."""

    def __init__(self, provider: SourceDataProvider | None = None):
        self.provider = provider if provider is not None else default_source_data_provider()

    def match_data_steps(self, conn: Any) -> tuple[SourceDataIngestionStep, ...]:
        """Build the Source Data Ingestion steps that update match data."""
        return (
            SourceDataIngestionStep(
                "refresh league catalogue",
                lambda: self.provider.refresh_league_catalogue(conn),
            ),
            SourceDataIngestionStep(
                "refresh current match data",
                self.provider.refresh_current_match_data,
            ),
        )

    def odds_step(self, conn: Any) -> SourceDataIngestionStep:
        """Build the Source Data Ingestion step that updates match odds."""
        return SourceDataIngestionStep(
            "refresh odds",
            lambda: self.provider.refresh_match_odds(conn),
        )


__all__ = [
    "SourceDataIngestion",
    "SourceDataIngestionStep",
    "SourceDataProvider",
    "default_source_data_provider",
    *_SOURCE_DATA_EXPORTS,
]
__getattr__ = make_legacy_getattr(_SOURCE_DATA_EXPORTS)
