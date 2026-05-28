import ast
from pathlib import Path

import pytest

from football_intelligence.features import (
    FeaturePipelineDependencies,
    FeatureSetMode,
    run_feature_pipeline,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RecordingManager:
    manager_name = "manager"

    def __init__(self, conn, matches, mode="training", **kwargs):
        self.conn = conn
        self.matches = matches
        self.mode = mode
        self.calls = conn["calls"]
        self.kwargs = kwargs

    def __enter__(self):
        self.calls.append(("enter", self.manager_name, self.mode))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.calls.append(("exit", self.manager_name, self.mode))
        return False

    def process_match(self, match):
        self.calls.append(("process", self.manager_name, match["match_id"], self.mode))


def manager_type(name):
    return type(f"{name.title()}Manager", (RecordingManager,), {"manager_name": name})


@pytest.mark.parametrize(
    ("feature_set", "processing_mode", "expected_setup"),
    (
        (
            FeatureSetMode.HISTORICAL,
            "training",
            ("drop_historical", "create_historical", "process_match_history"),
        ),
        (
            FeatureSetMode.FUTURE,
            "inference",
            ("drop_future", "create_future", "prune_future:2"),
        ),
    ),
)
def test_shared_feature_pipeline_runs_historical_and_future_modes(
    feature_set,
    processing_mode,
    expected_setup,
):
    connection = {"calls": []}
    matches = [
        {
            "match_id": 10,
            "home_team_formation": "4-3-3",
            "away_team_formation": "4-2-3-1",
        },
        {
            "match_id": 11,
            "home_team_formation": None,
            "away_team_formation": "4-4-2",
        },
    ]
    queries = []
    processed_updates = []

    def record_setup(name):
        def action(conn):
            conn["calls"].append(("setup", name))

        return action

    def fake_get_matches(conn, **kwargs):
        queries.append(kwargs)
        return matches

    def fake_update_processed_status(conn, match_ids, with_formation_flags, mode):
        processed_updates.append((tuple(match_ids), tuple(with_formation_flags), mode))
        conn["calls"].append(("processed_status", mode, tuple(match_ids)))

    dependencies = FeaturePipelineDependencies(
        get_matches=fake_get_matches,
        update_processed_status=fake_update_processed_status,
        drop_historical_tables=record_setup("drop_historical"),
        create_historical_tables=record_setup("create_historical"),
        process_matches_to_history=lambda conn, batch_size: conn["calls"].append(
            ("setup", "process_match_history")
        ),
        drop_future_tables=record_setup("drop_future"),
        create_future_tables=record_setup("create_future"),
        prune_old_future_features=lambda conn, days_threshold: conn["calls"].append(
            ("setup", f"prune_future:{days_threshold}")
        ),
        match_info_manager=manager_type("match_info"),
        stage_of_season_manager=manager_type("stage"),
        formation_manager=manager_type("formation"),
        elo_manager=manager_type("elo"),
        form_manager=manager_type("form"),
        h2h_manager=manager_type("h2h"),
    )

    result = run_feature_pipeline(
        connection,
        feature_set,
        dependencies=dependencies,
        batch_size=1000,
    )

    assert [call[1] for call in connection["calls"] if call[0] == "setup"] == list(
        expected_setup
    )
    assert [call[1] for call in connection["calls"] if call[0] == "process"] == [
        "match_info",
        "stage",
        "form",
        "elo",
        "h2h",
        "formation",
        "match_info",
        "stage",
        "form",
        "elo",
        "h2h",
    ]
    assert processed_updates == [((10, 11), (True, False), processing_mode)]
    assert result.feature_set is feature_set
    assert result.processing_mode == processing_mode
    assert result.matches_processed == 2
    assert queries


def test_feature_set_construction_no_longer_imports_data_processing():
    feature_files = sorted(
        path
        for path in (PROJECT_ROOT / "football_intelligence" / "features").rglob("*.py")
        if "__pycache__" not in path.parts
    )

    offenders = [
        path.relative_to(PROJECT_ROOT)
        for path in feature_files
        if _imports_data_processing(path)
    ]

    assert offenders == []


def _imports_data_processing(path):
    module = ast.parse(path.read_text())

    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            if any(_is_data_processing_module(alias.name) for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom) and _is_data_processing_module(node.module):
            return True

    return False


def _is_data_processing_module(module_name):
    if module_name is None:
        return False

    return module_name == "data_processing" or module_name.startswith("data_processing.")


def test_old_data_processing_feature_files_are_deleted():
    deleted_paths = [
        PROJECT_ROOT / "data_processing" / "for_training" / "match_result_features.py",
        PROJECT_ROOT / "data_processing" / "for_inferencing" / "match_result_features.py",
        PROJECT_ROOT / "data_processing" / "helpers",
        PROJECT_ROOT / "helpers" / "data_processing",
    ]

    assert [path for path in deleted_paths if path.exists()] == []
