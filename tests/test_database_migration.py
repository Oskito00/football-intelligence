from pathlib import Path

from football_intelligence.database import get_from_matches, upsert_records
from tests.import_audit import find_imports_matching, is_module_or_child


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ACTIVE_RUNTIME_FILES = (
    PROJECT_ROOT / "football_intelligence",
)

DELETED_DATABASE_HELPER_PATHS = (
    PROJECT_ROOT / "utils" / "database" / "get_and_set_functions.py",
    PROJECT_ROOT / "utils" / "database" / "create_tables.py",
    PROJECT_ROOT / "utils" / "database" / "postgresql.py",
    PROJECT_ROOT / "utils" / "database" / "clean_tables.py",
    PROJECT_ROOT / "utils" / "database" / "prune_future_features.py",
    PROJECT_ROOT / "utils" / "database" / "dict_to_sqlite.py",
    PROJECT_ROOT / "utils" / "database_helpers" / "get_and_set_functions.py",
)


def test_database_namespace_owns_active_persistence_helpers():
    assert get_from_matches.__module__ == "football_intelligence.database.football"
    assert upsert_records.__module__ == "football_intelligence.database.football"


def test_active_runtime_imports_do_not_use_deleted_database_paths():
    offenders = find_imports_matching(
        ACTIVE_RUNTIME_FILES,
        _is_deleted_database_module,
        PROJECT_ROOT,
    )

    assert offenders == []


def test_migrated_old_database_helper_files_are_deleted():
    assert [path for path in DELETED_DATABASE_HELPER_PATHS if path.exists()] == []


def _is_deleted_database_module(module_name: str) -> bool:
    return any(
        is_module_or_child(module_name, package_name)
        for package_name in ("utils.database", "utils.database_helpers")
    )
