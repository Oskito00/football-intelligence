from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADR_0003 = ROOT / "docs" / "adr" / "0003-use-alembic-for-database-setup.md"
CONTEXT = ROOT / "CONTEXT.md"
DOMAIN_DOCS = ROOT / "docs" / "agents" / "domain.md"
PUBLIC_README = ROOT / "readme.md"


def test_database_setup_adr_records_canonical_alembic_decision():
    assert_contains_all(
        read_text(ADR_0003),
        (
            "Alembic is the canonical **Database Setup** mechanism",
            "API startup is read-only",
            "does not create, migrate, or mutate schema",
            "Operational workflows assume **Database Setup** has already run",
            "new schema changes must be expressed as Alembic migrations",
        ),
        normalize=True,
    )


def test_domain_glossary_uses_public_football_intelligence_terms():
    assert_contains_all(
        read_text(CONTEXT),
        (
            "**Football Intelligence**:",
            "**Database Setup**:",
            "**Football Intelligence Agent**:",
            "_Avoid_: FootballPredictor, betting bot, tips app",
            "_Avoid_: API startup, implicit migration",
        ),
    )


def test_public_docs_distinguish_source_schema_data_and_artifacts():
    assert_contains_all(
        read_text(PUBLIC_README),
        (
            "code belongs in the repository",
            "schema belongs in Alembic migrations",
            "generated football data does not belong in Git",
            "local model artifacts are generated product assets",
            "The public repository ships code and schema, not private football data or trained model artifacts",
        ),
        normalize=True,
    )


def test_agent_domain_documentation_mentions_database_setup_boundary():
    assert_contains_all(
        read_text(DOMAIN_DOCS),
        (
            "Use **Database Setup** for schema preparation language",
            "Alembic owns schema setup and upgrades",
            "API startup and read-only inspection surfaces must not create or mutate schema",
            "**Paper Stakes** and **Market Value Signals** are research outputs",
            "not betting advice",
        ),
        normalize=True,
    )


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def assert_contains_all(
    text: str,
    expected_phrases: tuple[str, ...],
    *,
    normalize: bool = False,
) -> None:
    comparable_text = normalize_text(text) if normalize else text

    for phrase in expected_phrases:
        comparable_phrase = normalize_text(phrase) if normalize else phrase
        assert comparable_phrase in comparable_text, (
            f"Missing expected documentation: {phrase}"
        )


def normalize_text(text: str) -> str:
    return " ".join(text.casefold().split())
