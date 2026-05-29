from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREDICTION_REFRESH_COMMAND = "python -m football_intelligence.cli prediction-refresh"

EXPECTED_MAKE_SHORTCUTS = {
    "scrape": f"{PREDICTION_REFRESH_COMMAND} --only source-data-ingestion",
    "process-history": f"{PREDICTION_REFRESH_COMMAND} --only historical-feature-set",
    "build-future": f"{PREDICTION_REFRESH_COMMAND} --only future-feature-set",
    "predict": f"{PREDICTION_REFRESH_COMMAND} --only prediction-inference",
    "odds": f"{PREDICTION_REFRESH_COMMAND} --only odds-refresh",
}

REQUIRED_HANDBOOK_TERMS = (
    "**Prediction Refresh**",
    "**Source Data Ingestion**",
    "**Historical Feature Set**",
    "**Future Feature Set**",
    "**Prediction Board**",
    "`scrape` is shortcut slang for **Source Data Ingestion**",
    "`make tonight`",
)


def test_makefile_shortcuts_are_documented_operational_commands():
    makefile = read_text(ROOT / "Makefile")

    for target, command in EXPECTED_MAKE_SHORTCUTS.items():
        assert f"{target}:" in makefile
        assert command in makefile


def test_command_handbook_uses_product_language_and_shortcuts():
    handbook = read_text(ROOT / "COMMANDS.md")

    for term in REQUIRED_HANDBOOK_TERMS:
        assert term in handbook

    for target in EXPECTED_MAKE_SHORTCUTS:
        assert f"`make {target}`" in handbook


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")
