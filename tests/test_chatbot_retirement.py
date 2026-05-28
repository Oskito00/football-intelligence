import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FOOTBALL_INTELLIGENCE_PACKAGE = PROJECT_ROOT / "football_intelligence"
RETIRED_CHATBOT_PACKAGE = PROJECT_ROOT / "chatbot"
WEB_DOCKERFILE = PROJECT_ROOT / "Dockerfile.web"
WEB_REQUIREMENTS = "requirements.web.txt"
API_ENTRYPOINT = "football_intelligence.api:app"
RETIRED_API_ENTRYPOINT = "chatbot.api"
RETIRED_DOCKERFILE = "chatbot/Dockerfile"
RETIRED_REQUIREMENTS = "chatbot/requirements.txt"
COMPOSE_CONFIGS = (
    "docker-compose.yml",
    "docker-compose.dev.yml",
    "docker-compose.prod.yml",
)


def _python_files(path):
    return sorted(
        child for child in path.rglob("*.py") if "__pycache__" not in child.parts
    )


def _imported_modules(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def _is_retired_chatbot_module(module):
    return module == "chatbot" or module.startswith("chatbot.")


def test_football_intelligence_imports_do_not_use_retired_chatbot_paths():
    offenders = []

    for path in _python_files(FOOTBALL_INTELLIGENCE_PACKAGE):
        for module in _imported_modules(path):
            if _is_retired_chatbot_module(module):
                offenders.append((path.relative_to(PROJECT_ROOT), module))

    assert offenders == []


def test_superseded_chatbot_package_is_deleted():
    assert not RETIRED_CHATBOT_PACKAGE.exists()


def test_web_startup_uses_football_intelligence_api_entrypoint():
    dockerfile = WEB_DOCKERFILE.read_text(encoding="utf-8")
    heroku_config = (PROJECT_ROOT / "heroku.yml").read_text(encoding="utf-8")
    compose_configs = [
        (PROJECT_ROOT / config).read_text(encoding="utf-8")
        for config in COMPOSE_CONFIGS
    ]

    assert API_ENTRYPOINT in dockerfile
    assert WEB_REQUIREMENTS in dockerfile
    assert RETIRED_API_ENTRYPOINT not in dockerfile
    assert RETIRED_REQUIREMENTS not in dockerfile

    assert API_ENTRYPOINT in heroku_config
    assert RETIRED_API_ENTRYPOINT not in heroku_config

    assert all(WEB_DOCKERFILE.name in config for config in compose_configs)
    assert all(RETIRED_DOCKERFILE not in config for config in compose_configs)
