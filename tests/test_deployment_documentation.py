from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_readme_documents_cli_first_deployment_boundaries():
    readme = (ROOT / "readme.md").read_text(encoding="utf-8")

    assert "## Deployment boundaries" in readme
    assert "**Prediction Refresh**" in readme
    assert "**Model Training**" in readme
    assert "python -m football_intelligence.cli prediction-refresh" in readme
    assert "python -m football_intelligence.cli model-training" in readme

    for runner in ("Heroku", "Docker", "cron"):
        assert runner in readme

    assert "Heroku scheduler" in readme
    assert "one runner" in readme
    assert "Follow-up work" in readme
