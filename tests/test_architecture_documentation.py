from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADR_0003 = ROOT / "docs" / "adr" / "0003-use-alembic-for-database-setup.md"
CONTEXT = ROOT / "CONTEXT.md"
DOMAIN_DOCS = ROOT / "docs" / "agents" / "domain.md"
PUBLIC_README = ROOT / "readme.md"
ENV_EXAMPLE = ROOT / ".env.example"


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


def test_public_readme_documents_code_only_onboarding_path():
    assert_contains_all(
        read_text(PUBLIC_README),
        (
            "code-only Football Intelligence repository",
            "No real match data, odds data, database dumps, generated training datasets, or trained model artifacts are shipped",
            "cp .env.example .env",
            "DATABASE_URL=postgresql+psycopg2://football:football@localhost:5432/football_intelligence",
            "make db-setup",
            "Run **Database Setup** before **Source Data Ingestion**, **Prediction Refresh**, or **Model Training**",
            "python -m uvicorn football_intelligence.api:app --host 0.0.0.0 --port 5000",
            "npm run build",
            "schema-only empty dashboard state",
            "The API, frontend dashboard, operational workflows, and **Football Intelligence Agent** are separate surfaces",
        ),
        normalize=True,
    )


def test_env_example_documents_safe_local_defaults():
    assert_contains_all(
        read_text(ENV_EXAMPLE),
        (
            "ENV=dev",
            "DB_HOST=localhost",
            "DB_PORT=5432",
            "DB_NAME=football_intelligence",
            "DB_USER=football",
            "DB_PASSWORD=football",
            "DATABASE_URL=postgresql+psycopg2://football:football@localhost:5432/football_intelligence",
            "API_FOOTBALL_KEY=",
            "GROQ_API_KEY=",
            "VITE_API_URL=http://localhost:5000",
        ),
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
