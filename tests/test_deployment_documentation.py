from pathlib import Path

import pytest

from tests.import_audit import find_imports_matching, is_module_or_child


ROOT = Path(__file__).resolve().parents[1]
WEB_API_ENTRYPOINT = "football_intelligence.api:app"
PREDICTION_REFRESH_COMMAND = "python -m football_intelligence.cli prediction-refresh"
MODEL_TRAINING_COMMAND = "python -m football_intelligence.cli model-training"
RETIRED_ENTRYPOINT_TEXT = (
    "chatbot.api",
    "scheduler.scheduler",
    "scheduler/Dockerfile",
    "Dockerfile.scheduler",
)
DEPLOYMENT_DOCUMENTS = (
    (ROOT / "README.md", "## Deployment boundaries"),
    (ROOT / "football_intelligence" / "README.md", "## Deployment boundary"),
)
REQUIRED_DEPLOYMENT_TERMS = (
    "**Prediction Refresh**",
    "**Model Training**",
    "**Match Intelligence Lifecycle**",
    PREDICTION_REFRESH_COMMAND,
    MODEL_TRAINING_COMMAND,
    "Docker",
    "cron",
)
DEPLOYMENT_CONFIGS = (
    ROOT / "Dockerfile",
    ROOT / "docker-compose.yml",
)
RETIRED_ENTRYPOINT_PATHS = (
    ROOT / "scheduler",
    ROOT / "Dockerfile.scheduler",
)
RETIRED_DEPLOYMENT_FILES = (
    ROOT / "Dockerfile.web",
    ROOT / "Dockerfile.operations",
    ROOT / "docker-compose.dev.yml",
    ROOT / "docker-compose.prod.yml",
    ROOT / "heroku.yml",
    ROOT / "requirements.web.txt",
    ROOT / "requirements.operations.txt",
    ROOT / "requirements_dev.txt",
)


@pytest.mark.parametrize(("document_path", "heading"), DEPLOYMENT_DOCUMENTS)
def test_documentation_describes_cli_first_deployment_boundary(
    document_path,
    heading,
):
    document = read_text(document_path)

    assert heading in document

    for term in REQUIRED_DEPLOYMENT_TERMS:
        assert term in document


def test_deployment_configs_use_football_intelligence_operational_entrypoints():
    dockerfile = read_text(ROOT / "Dockerfile")
    compose_config = read_text(ROOT / "docker-compose.yml")
    combined_config = "\n".join(read_text(path) for path in DEPLOYMENT_CONFIGS)

    assert WEB_API_ENTRYPOINT in dockerfile
    assert "requirements.txt" in dockerfile
    assert PREDICTION_REFRESH_COMMAND in compose_config
    assert MODEL_TRAINING_COMMAND in compose_config

    for retired_entrypoint in RETIRED_ENTRYPOINT_TEXT:
        assert retired_entrypoint not in combined_config


def test_redundant_deployment_files_are_deleted():
    existing_retired_files = [path for path in RETIRED_DEPLOYMENT_FILES if path.exists()]

    assert existing_retired_files == []


def test_retired_scheduler_package_and_entrypoint_files_are_deleted():
    existing_retired_paths = [path for path in RETIRED_ENTRYPOINT_PATHS if path.exists()]

    assert existing_retired_paths == []


def test_active_runtime_imports_do_not_reference_retired_scheduler_paths():
    assert find_retired_scheduler_imports() == []


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def find_retired_scheduler_imports() -> list[tuple[Path, str]]:
    return find_imports_matching(
        ROOT / "football_intelligence",
        is_retired_scheduler_module,
        ROOT,
    )


def is_retired_scheduler_module(module_name: str) -> bool:
    return is_module_or_child(module_name, "scheduler")
