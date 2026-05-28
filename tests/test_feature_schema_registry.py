from football_intelligence.features import FORM_FEATURE_SCHEMA, get_feature_schema
from football_intelligence.features.construction.form_manager import FormManager
from football_intelligence.predictions import ResultFeatureLoader


def test_form_feature_schema_centralizes_table_pair_and_loader_expectations():
    schema = get_feature_schema("form")

    assert schema is FORM_FEATURE_SCHEMA
    assert schema.table_for_mode("training") == "form_history"
    assert schema.table_for_mode("inference") == "form_future"
    assert schema.storage_columns == (
        "match_id",
        "home_team_id",
        "away_team_id",
        "home_name",
        "away_name",
        "home_team_form",
        "away_team_form",
        "draw_features",
    )
    assert schema.json_columns == (
        "home_team_form",
        "away_team_form",
        "draw_features",
    )
    assert schema.expanded_json_features["draw_features"] == (
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


def test_result_feature_loader_uses_form_schema_for_mode_tables_and_query_parts():
    loader = ResultFeatureLoader(
        conn=None,
        config={"feature_tables": ["form_future"], "feature_requirements": {}},
        mode="inference",
    )

    query_parts = loader._build_dynamic_query()

    assert loader.form_history_table == "form_future"
    assert "fh.home_team_form::jsonb as home_team_form" in query_parts["select_fields"]
    assert "fh.draw_features::jsonb as draw_features" in query_parts["select_fields"]
    assert "INNER JOIN form_future fh" in query_parts["joins"]
    assert "jsonb_array_length(fh.home_team_form) >= 10" in query_parts["joins"]
    assert "jsonb_array_length(fh.away_team_form) >= 10" in query_parts["joins"]


class RecordingCursor:
    def __init__(self):
        self.executemany_calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def executemany(self, query, params):
        self.executemany_calls.append((query, params))


class RecordingConnection:
    def __init__(self):
        self.cursor_instance = RecordingCursor()
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def test_form_manager_uses_schema_for_future_table_and_storage_columns():
    connection = RecordingConnection()
    manager = FormManager(connection, [], mode="inference")
    manager.form_history = [
        {
            "match_id": 7,
            "home_team_id": 1,
            "away_team_id": 2,
            "home_name": "Home",
            "away_name": "Away",
            "home_team_form": [],
            "away_team_form": [],
            "draw_features": {},
        }
    ]

    manager.__exit__(None, None, None)

    query, params = connection.cursor_instance.executemany_calls[0]
    assert "INSERT INTO form_future" in query
    assert ", ".join(FORM_FEATURE_SCHEMA.storage_columns) in query
    assert params[0]["match_id"] == 7
    assert params[0]["home_team_form"] == "[]"
    assert connection.committed
