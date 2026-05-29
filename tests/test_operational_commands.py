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
VALUE_BACKTEST_COMMAND = "python -m football_intelligence.cli value-backtest"
REQUIRED_VALUE_BACKTEST_TERMS = (
    VALUE_BACKTEST_COMMAND,
    "100 became X",
    "--kelly-fraction 0.25",
    "--min-expected-value 0.05",
    "--odds-mode best",
    "--odds-mode average",
    "**Paper Stakes** are hypothetical research stakes, not betting advice",
    "profitable historical result is evidence to inspect, not proof of future profitability",
    "retained **Predictions**",
    "true prediction-snapshot history",
    "calibration diagnostics",
    "Brier score",
    "log loss",
    "prediction snapshots",
    "walk-forward analysis",
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


def test_command_handbook_documents_value_backtest_usage_and_limits():
    handbook = read_text(ROOT / "COMMANDS.md")
    normalized_handbook = " ".join(handbook.split())

    for term in REQUIRED_VALUE_BACKTEST_TERMS:
        assert " ".join(term.split()) in normalized_handbook


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")
