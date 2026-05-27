"""Feature schema registry for Historical and Future Feature Sets."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class FeatureFamilySchema:
    """Central schema contract for one feature family."""

    name: str
    historical_table: str
    future_table: str
    storage_columns: tuple[str, ...]
    json_columns: tuple[str, ...] = ()
    column_types: Mapping[str, str] = field(default_factory=dict)
    loader_json_columns: tuple[str, ...] = ()
    loader_json_length_columns: tuple[str, ...] = ()
    expanded_json_features: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    def table_for_mode(self, mode: str) -> str:
        """Return the table name used by a feature processing mode."""
        if mode == "training":
            return self.historical_table
        if mode == "inference":
            return self.future_table
        raise ValueError(f"Unknown feature processing mode: {mode!r}")

    def loader_select_fields(self, table_alias: str) -> tuple[str, ...]:
        """Return JSON-aware select fields expected by model feature loaders."""
        return tuple(
            f"{table_alias}.{column}::jsonb as {column}"
            for column in self.loader_json_columns
        )

    def loader_join_conditions(self, table_alias: str) -> tuple[str, ...]:
        """Return loader join constraints for records usable by the model."""
        return tuple(
            f"jsonb_array_length({table_alias}.{column}) >= 10"
            for column in self.loader_json_length_columns
        )

    def ddl_columns(self) -> tuple[str, ...]:
        """Return storage columns with database types for CREATE TABLE statements."""
        ddl_columns = []
        for column in self.storage_columns:
            column_type = self.column_types.get(column)
            if column_type is None:
                column_type = "INTEGER" if column.endswith("_id") else "VARCHAR(255)"
            ddl_columns.append(f"{column} {column_type}")
        return tuple(ddl_columns)


FORM_FEATURE_SCHEMA = FeatureFamilySchema(
    name="form",
    historical_table="form_history",
    future_table="form_future",
    storage_columns=(
        "match_id",
        "home_team_id",
        "away_team_id",
        "home_name",
        "away_name",
        "home_team_form",
        "away_team_form",
        "draw_features",
    ),
    json_columns=("home_team_form", "away_team_form", "draw_features"),
    column_types={
        "match_id": "INTEGER PRIMARY KEY",
        "home_team_id": "INTEGER",
        "away_team_id": "INTEGER",
        "home_team_form": "JSONB",
        "away_team_form": "JSONB",
        "draw_features": "JSONB",
    },
    loader_json_columns=("home_team_form", "away_team_form", "draw_features"),
    loader_json_length_columns=("home_team_form", "away_team_form"),
    expanded_json_features={
        "draw_features": (
            "home_draw_rate_3",
            "home_draw_rate_5",
            "home_draw_rate_10",
            "away_draw_rate_3",
            "away_draw_rate_5",
            "away_draw_rate_10",
            "both_draw_rate_3",
            "both_draw_rate_5",
            "both_draw_rate_10",
            "zero_goals_rate_3",
            "zero_goals_rate_5",
            "zero_goals_rate_10",
            "home_avg_goal_diff_3",
            "home_avg_goal_diff_5",
            "home_avg_goal_diff_10",
            "away_avg_goal_diff_3",
            "away_avg_goal_diff_5",
            "away_avg_goal_diff_10",
        )
    },
)

_FEATURE_SCHEMAS = {
    FORM_FEATURE_SCHEMA.name: FORM_FEATURE_SCHEMA,
}


def get_feature_schema(name: str) -> FeatureFamilySchema:
    """Return a registered feature family schema by name."""
    try:
        return _FEATURE_SCHEMAS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown feature schema: {name!r}") from exc
