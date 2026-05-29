import importlib
from pathlib import Path
from types import SimpleNamespace

from football_intelligence.cli import main as cli_main
from football_intelligence.database import setup as database_setup


baseline_schema = importlib.import_module(
    "football_intelligence.database.migrations.versions.0001_baseline_schema"
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASELINE_TABLES = {
    statement.split()[2]
    for statement in baseline_schema._schema_statements(
        baseline_schema.BASELINE_SCHEMA_SQL
    )
    if statement.startswith("CREATE TABLE ")
}


def test_database_setup_commands_are_exposed_by_cli(monkeypatch):
    calls = []

    monkeypatch.setattr(cli_main, "setup_database", lambda: calls.append("setup"))
    monkeypatch.setattr(cli_main, "upgrade_database", lambda: calls.append("upgrade"))
    monkeypatch.setattr(
        cli_main,
        "stamp_existing_database_baseline",
        lambda: calls.append("stamp-baseline"),
    )
    monkeypatch.setattr(
        cli_main,
        "show_current_database_revision",
        lambda *, verbose=False: calls.append(("current", verbose)),
    )

    assert cli_main.main(["db", "setup"]) == 0
    assert cli_main.main(["db", "upgrade"]) == 0
    assert cli_main.main(["db", "current", "--verbose"]) == 0
    assert cli_main.main(["db", "stamp-baseline"]) == 0

    assert calls == ["setup", "upgrade", ("current", True), "stamp-baseline"]


def test_database_setup_makefile_shortcuts_exist():
    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "db-setup:" in makefile
    assert "python -m football_intelligence.cli db setup" in makefile
    assert "db-upgrade:" in makefile
    assert "python -m football_intelligence.cli db upgrade" in makefile
    assert "db-current:" in makefile
    assert "python -m football_intelligence.cli db current" in makefile
    assert "db-stamp-baseline:" in makefile
    assert "python -m football_intelligence.cli db stamp-baseline" in makefile


def test_database_setup_uses_package_migrations(monkeypatch):
    calls = []

    def fake_upgrade(config, revision):
        calls.append((config, revision))

    monkeypatch.setattr(database_setup.command, "upgrade", fake_upgrade)

    database_setup.setup_database(database_url="postgresql+psycopg2://u:p@h:5432/db")

    config, revision = calls[0]
    assert revision == "head"
    assert config.get_main_option("script_location").endswith(
        "football_intelligence/database/migrations"
    )
    assert config.get_main_option("sqlalchemy.url") == (
        "postgresql+psycopg2://u:p@h:5432/db"
    )


def test_database_current_reports_unversioned_database(monkeypatch, capsys):
    monkeypatch.setattr(database_setup, "current_database_revisions", lambda **_: [])

    database_setup.show_current_database_revision()

    assert "No migration revision recorded." in capsys.readouterr().out


def test_database_current_reports_revision(monkeypatch, capsys):
    monkeypatch.setattr(
        database_setup,
        "current_database_revisions",
        lambda **_: ["0001_baseline_schema"],
    )

    database_setup.show_current_database_revision()

    assert "Current database revision: 0001_baseline_schema" in capsys.readouterr().out


def test_database_current_verbose_delegates_to_alembic(monkeypatch):
    calls = []

    monkeypatch.setattr(
        database_setup,
        "build_alembic_config",
        lambda database_url=None: SimpleNamespace(database_url=database_url),
    )
    monkeypatch.setattr(
        database_setup.command,
        "current",
        lambda config, *, verbose=False: calls.append((config.database_url, verbose)),
    )

    database_setup.show_current_database_revision(
        database_url="postgresql+psycopg2://u:p@h:5432/db",
        verbose=True,
    )

    assert calls == [("postgresql+psycopg2://u:p@h:5432/db", True)]


def test_database_stamp_baseline_delegates_to_alembic(monkeypatch):
    calls = []

    def fake_stamp(config, revision):
        calls.append((config, revision))

    monkeypatch.setattr(database_setup.command, "stamp", fake_stamp)

    database_setup.stamp_existing_database_baseline(
        database_url="postgresql+psycopg2://u:p@h:5432/db"
    )

    config, revision = calls[0]
    assert revision == "head"
    assert config.get_main_option("sqlalchemy.url") == (
        "postgresql+psycopg2://u:p@h:5432/db"
    )


def test_baseline_migration_is_schema_only_and_covers_current_tables():
    required_tables = {
        "matches",
        "odds",
        "match_result_predictions",
        "processed_info",
        "elo_history",
        "elo_future",
        "form_history",
        "form_future",
        "match_info_history",
        "match_info_future",
        "league_standings_future",
        "team_main_competition",
        "teams_mapping",
    }

    assert required_tables.issubset(BASELINE_TABLES)
    assert len(BASELINE_TABLES) == 28
    assert "INSERT INTO" not in baseline_schema.BASELINE_SCHEMA_SQL
    assert "COPY " not in baseline_schema.BASELINE_SCHEMA_SQL
