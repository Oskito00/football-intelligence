from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADR_0003 = ROOT / "docs" / "adr" / "0003-use-alembic-for-database-setup.md"


def test_database_setup_adr_records_canonical_alembic_decision():
    adr = read_text(ADR_0003)
    normalized_adr = normalize_text(adr)

    required_statements = (
        "Alembic is the canonical **Database Setup** mechanism",
        "API startup is read-only",
        "does not create, migrate, or mutate schema",
        "Operational workflows assume **Database Setup** has already run",
        "new schema changes must be expressed as Alembic migrations",
    )

    for statement in required_statements:
        assert normalize_text(statement) in normalized_adr


def test_domain_glossary_uses_public_football_intelligence_terms():
    context = read_text(ROOT / "CONTEXT.md")

    required_glossary_entries = (
        "**Football Intelligence**:",
        "**Database Setup**:",
        "**Football Intelligence Agent**:",
        "_Avoid_: FootballPredictor, betting bot, tips app",
        "_Avoid_: API startup, implicit migration",
    )

    for entry in required_glossary_entries:
        assert entry in context


def test_public_docs_distinguish_source_schema_data_and_artifacts():
    readme = read_text(ROOT / "readme.md")
    normalized_readme = normalize_text(readme)

    required_guidance = (
        "code belongs in the repository",
        "schema belongs in Alembic migrations",
        "generated football data does not belong in Git",
        "local model artifacts are generated product assets",
        "The public repository ships code and schema, not private football data or trained model artifacts",
    )

    for guidance in required_guidance:
        assert normalize_text(guidance) in normalized_readme


def test_agent_domain_documentation_mentions_database_setup_boundary():
    domain_docs = read_text(ROOT / "docs" / "agents" / "domain.md")
    normalized_domain_docs = normalize_text(domain_docs)

    required_guidance = (
        "Use **Database Setup** for schema preparation language",
        "Alembic owns schema setup and upgrades",
        "API startup and read-only inspection surfaces must not create or mutate schema",
        "**Paper Stakes** and **Market Value Signals** are research outputs",
        "not betting advice",
    )

    for guidance in required_guidance:
        assert normalize_text(guidance) in normalized_domain_docs


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def normalize_text(text: str) -> str:
    return " ".join(text.casefold().split())
