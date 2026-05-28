import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _python_files(path):
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


def test_active_runtime_imports_do_not_use_retired_chatbot_paths():
    offenders = []

    for path in _python_files(PROJECT_ROOT / "football_intelligence"):
        for module in _imported_modules(path):
            if module == "chatbot" or module.startswith("chatbot."):
                offenders.append((path.relative_to(PROJECT_ROOT), module))

    assert offenders == []


def test_superseded_chatbot_package_is_deleted():
    assert not (PROJECT_ROOT / "chatbot").exists()


def test_web_startup_uses_football_intelligence_api_entrypoint():
    dockerfile = (PROJECT_ROOT / "Dockerfile.web").read_text()
    heroku_config = (PROJECT_ROOT / "heroku.yml").read_text()
    compose_configs = [
        (PROJECT_ROOT / "docker-compose.yml").read_text(),
        (PROJECT_ROOT / "docker-compose.dev.yml").read_text(),
        (PROJECT_ROOT / "docker-compose.prod.yml").read_text(),
    ]

    assert "football_intelligence.api:app" in dockerfile
    assert "football_intelligence.api:app" in heroku_config
    assert all("Dockerfile.web" in config for config in compose_configs)
    assert "chatbot.api" not in dockerfile
    assert "chatbot.api" not in heroku_config
    assert all("chatbot/Dockerfile" not in config for config in compose_configs)
