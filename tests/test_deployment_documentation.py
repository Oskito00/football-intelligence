from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
DEPLOYMENT_DOCUMENTS = (
    (ROOT / "readme.md", "## Deployment boundaries"),
    (ROOT / "football_intelligence" / "README.md", "## Deployment boundary"),
)
REQUIRED_DEPLOYMENT_TERMS = (
    "**Prediction Refresh**",
    "**Model Training**",
    "**Match Intelligence Lifecycle**",
    "python -m football_intelligence.cli prediction-refresh",
    "python -m football_intelligence.cli model-training",
    "Heroku",
    "Docker",
    "cron",
    "Heroku scheduler",
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
