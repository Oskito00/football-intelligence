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
    (ROOT / "readme.md", "## Deployment boundaries"),
    (ROOT / "football_intelligence" / "README.md", "## Deployment boundary"),
)
REQUIRED_DEPLOYMENT_TERMS = (
    "**Prediction Refresh**",
    "**Model Training**",
    "**Match Intelligence Lifecycle**",
    PREDICTION_REFRESH_COMMAND,
    MODEL_TRAINING_COMMAND,
    "Heroku",
    "Docker",
    "cron",
)
DEPLOYMENT_CONFIGS = (
    ROOT / "Dockerfile.web",
    ROOT / "Dockerfile.operations",
    ROOT / "docker-compose.yml",
    ROOT / "docker-compose.dev.yml",
    ROOT / "docker-compose.prod.yml",
    ROOT / "heroku.yml",
)
COMPOSE_CONFIGS = (
    ROOT / "docker-compose.yml",
    ROOT / "docker-compose.dev.yml",
    ROOT / "docker-compose.prod.yml",
)
RETIRED_ENTRYPOINT_PATHS = (
    ROOT / "scheduler",
    ROOT / "Dockerfile.scheduler",
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
    web_dockerfile = read_text(ROOT / "Dockerfile.web")
    operations_dockerfile = read_text(ROOT / "Dockerfile.operations")
    heroku_config = read_text(ROOT / "heroku.yml")
    compose_configs = [read_text(path) for path in COMPOSE_CONFIGS]
    combined_config = "\n".join(read_text(path) for path in DEPLOYMENT_CONFIGS)

    assert WEB_API_ENTRYPOINT in web_dockerfile
    assert "football_intelligence.cli" in operations_dockerfile
    assert "prediction-refresh" in operations_dockerfile
    assert PREDICTION_REFRESH_COMMAND in heroku_config
    assert MODEL_TRAINING_COMMAND in heroku_config
    assert all(PREDICTION_REFRESH_COMMAND in config for config in compose_configs)
    assert all(MODEL_TRAINING_COMMAND in config for config in compose_configs)

    for retired_entrypoint in RETIRED_ENTRYPOINT_TEXT:
        assert retired_entrypoint not in combined_config


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
