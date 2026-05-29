"""Database Setup for Football Intelligence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import URL, create_engine, inspect, text

from config import get_config


MIGRATIONS_PATH = Path(__file__).resolve().parent / "migrations"


def build_alembic_config(database_url: str | None = None) -> AlembicConfig:
    """Build Alembic configuration from the app's existing database config."""

    config = AlembicConfig()
    config.set_main_option("script_location", str(MIGRATIONS_PATH))
    config.set_main_option("sqlalchemy.url", database_url or database_url_from_config())
    return config


def database_url_from_config() -> str:
    app_config = get_config()
    port = int(getattr(app_config, "DB_PORT", 5432) or 5432)
    url = URL.create(
        "postgresql+psycopg2",
        username=app_config.DB_USER,
        password=app_config.DB_PASSWORD,
        host=app_config.DB_HOST,
        port=port,
        database=app_config.DB_NAME,
    )
    return url.render_as_string(hide_password=False)


def setup_database(*, database_url: str | None = None) -> None:
    upgrade_database(database_url=database_url, revision="head")


def upgrade_database(
    *,
    database_url: str | None = None,
    revision: str = "head",
) -> None:
    command.upgrade(build_alembic_config(database_url), revision)


def show_current_database_revision(
    *,
    database_url: str | None = None,
    verbose: bool = False,
) -> None:
    if verbose:
        command.current(build_alembic_config(database_url), verbose=True)
        return

    revisions = current_database_revisions(database_url=database_url)
    if not revisions:
        print("No migration revision recorded.")
        return

    for revision in revisions:
        print(f"Current database revision: {revision}")


def stamp_existing_database_baseline(*, database_url: str | None = None) -> None:
    command.stamp(build_alembic_config(database_url), "head")


def current_database_revisions(*, database_url: str | None = None) -> list[str]:
    engine = create_engine(database_url or database_url_from_config())
    with engine.connect() as connection:
        if not inspect(connection).has_table("alembic_version"):
            return []
        rows = connection.execute(text("SELECT version_num FROM alembic_version"))
        return [row[0] for row in rows]


def migration_runner() -> dict[str, Any]:
    """Return the small surface tests can patch without importing Alembic internals."""

    return {
        "setup_database": setup_database,
        "upgrade_database": upgrade_database,
        "show_current_database_revision": show_current_database_revision,
    }
