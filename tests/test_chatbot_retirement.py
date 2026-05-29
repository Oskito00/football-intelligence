from pathlib import Path

from tests.import_audit import find_imports_matching, is_module_or_child


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FOOTBALL_INTELLIGENCE_PACKAGE = PROJECT_ROOT / "football_intelligence"
RETIRED_CHATBOT_PACKAGE = PROJECT_ROOT / "chatbot"
WEB_DOCKERFILE = PROJECT_ROOT / "Dockerfile"
WEB_REQUIREMENTS = "requirements.txt"
API_ENTRYPOINT = "football_intelligence.api:app"
RETIRED_API_ENTRYPOINT = "chatbot.api"
RETIRED_DOCKERFILE = "chatbot/Dockerfile"
RETIRED_REQUIREMENTS = "chatbot/requirements.txt"
COMPOSE_CONFIG = "docker-compose.yml"


def _is_retired_chatbot_module(module):
    return is_module_or_child(module, "chatbot")


def test_football_intelligence_imports_do_not_use_retired_chatbot_paths():
    offenders = find_imports_matching(
        FOOTBALL_INTELLIGENCE_PACKAGE,
        _is_retired_chatbot_module,
        PROJECT_ROOT,
    )

    assert offenders == []


def test_superseded_chatbot_package_is_deleted():
    assert not RETIRED_CHATBOT_PACKAGE.exists()


def test_web_startup_uses_football_intelligence_api_entrypoint():
    dockerfile = WEB_DOCKERFILE.read_text(encoding="utf-8")
    compose_config = (PROJECT_ROOT / COMPOSE_CONFIG).read_text(encoding="utf-8")

    assert API_ENTRYPOINT in dockerfile
    assert WEB_REQUIREMENTS in dockerfile
    assert RETIRED_API_ENTRYPOINT not in dockerfile
    assert RETIRED_REQUIREMENTS not in dockerfile

    assert WEB_DOCKERFILE.name in compose_config
    assert RETIRED_DOCKERFILE not in compose_config
