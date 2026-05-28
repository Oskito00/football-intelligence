import ast
from pathlib import Path

import pytest


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


@pytest.mark.parametrize(("document_path", "heading"), DEPLOYMENT_DOCUMENTS)
def test_documentation_describes_cli_first_deployment_boundary(
    document_path,
    heading,
):
    document = document_path.read_text(encoding="utf-8")

    assert heading in document

    for term in REQUIRED_DEPLOYMENT_TERMS:
        assert term in document


def test_deployment_configs_use_football_intelligence_operational_entrypoints():
    web_dockerfile = (ROOT / "Dockerfile.web").read_text(encoding="utf-8")
    operations_dockerfile = (ROOT / "Dockerfile.operations").read_text(
        encoding="utf-8"
    )
    heroku_config = (ROOT / "heroku.yml").read_text(encoding="utf-8")
    compose_configs = [
        config.read_text(encoding="utf-8") for config in COMPOSE_CONFIGS
    ]
    combined_config = "\n".join(
        config.read_text(encoding="utf-8") for config in DEPLOYMENT_CONFIGS
    )

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
    retired_paths = (
        ROOT / "scheduler",
        ROOT / "Dockerfile.scheduler",
    )

    assert [path for path in retired_paths if path.exists()] == []


def test_active_runtime_imports_do_not_reference_retired_scheduler_paths():
    offenders = []

    for path in (ROOT / "football_intelligence").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue

        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "scheduler" or alias.name.startswith("scheduler."):
                        offenders.append((path.relative_to(ROOT), alias.name))
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module == "scheduler" or node.module.startswith("scheduler."):
                    offenders.append((path.relative_to(ROOT), node.module))

    assert offenders == []
