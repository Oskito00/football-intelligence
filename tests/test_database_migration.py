import ast
from pathlib import Path

from football_intelligence.database import get_from_matches, upsert_records


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ACTIVE_RUNTIME_FILES = (
    PROJECT_ROOT / "football_intelligence",
    PROJECT_ROOT / "ml_pipeline" / "main_infer.py",
    PROJECT_ROOT / "ml_pipeline" / "inference" / "infer_result_model.py",
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


def _python_files(path):
    if path.is_file():
        return [path]
    return sorted(
        child
        for child in path.rglob("*.py")
        if "__pycache__" not in child.parts
    )


def _imported_modules(path):
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def test_database_namespace_owns_active_persistence_helpers():
    assert get_from_matches.__module__ == "football_intelligence.database.football"
    assert upsert_records.__module__ == "football_intelligence.database.football"


def test_active_runtime_imports_do_not_use_deleted_database_paths():
    offenders = []

    for root in ACTIVE_RUNTIME_FILES:
        for path in _python_files(root):
            for module in _imported_modules(path):
                if module == "utils.database" or module.startswith("utils.database."):
                    offenders.append((path.relative_to(PROJECT_ROOT), module))
                if (
                    module == "utils.database_helpers"
                    or module.startswith("utils.database_helpers.")
                ):
                    offenders.append((path.relative_to(PROJECT_ROOT), module))

    assert offenders == []


def test_migrated_old_database_helper_files_are_deleted():
    assert [path for path in DELETED_DATABASE_HELPER_PATHS if path.exists()] == []
