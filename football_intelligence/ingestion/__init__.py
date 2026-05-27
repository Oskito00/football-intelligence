"""Football data ingestion home for keeping source match data current.

Compatibility exports point at existing API-Football scrapers during the
staged migration.
"""

from football_intelligence._compat import LegacyExport, resolve_legacy_export

_LEGACY_EXPORTS = {
    "get_all_leagues_on_api": LegacyExport(
        "data_scraping.api_football.all_data.scrape_league_ids",
        "get_all_leagues_on_api",
    ),
    "scrape_current_seasons": LegacyExport(
        "data_scraping.api_football.current_season.current_seasons_scrape",
        "scrape_current_seasons",
    ),
    "scrape_future_match_odds": LegacyExport(
        "data_scraping.api_football.odds.scrape_future_match_odds",
        "scrape_future_match_odds",
    ),
}

__all__ = list(_LEGACY_EXPORTS)


def __getattr__(name: str):
    return resolve_legacy_export(_LEGACY_EXPORTS, name)
