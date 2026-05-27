"""Database access home for football data queries and mutations.

The Analyst Agent should depend on read-only interfaces here as they are
introduced; existing mutation helpers remain available through compatibility
exports for operational workflows.
"""

from football_intelligence._compat import LegacyExport, make_legacy_getattr
from football_intelligence.database.football import (
    FootballQueryError,
    PostgresReadOnlyRunner,
    ReadOnlyFootballQueries,
)

_LEGACY_EXPORTS = {
    "get_from_matches": LegacyExport(
        "utils.database.get_and_set_functions",
        "get_from_matches",
    ),
    "upsert_records": LegacyExport("utils.database.postgresql", "upsert_records"),
    "create_match_result_predictions_table": LegacyExport(
        "utils.database.create_tables",
        "create_match_result_predictions_table",
    ),
}

__all__ = [
    "FootballQueryError",
    "PostgresReadOnlyRunner",
    "ReadOnlyFootballQueries",
    *list(_LEGACY_EXPORTS),
]
__getattr__ = make_legacy_getattr(_LEGACY_EXPORTS)
