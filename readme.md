# Football Intelligence

This is a public, code-only Football Intelligence repository. Football
Intelligence produces football **Predictions**, inspects odds context and
**Market Value Signals**, and answers **Natural-Language Football Questions**
through the **Football Intelligence Agent**. The dashboard is one read-only
surface of that product, not the whole architecture.

The project is not a betting tips app. **Market Value Signals**, **Paper
Stakes**, and **Value Backtests** are research outputs for inspecting model and
market behavior, not betting instructions, betting advice, or real-money
recommendations.

## Repository boundaries

The public repository ships code and schema, not private football data or
trained model artifacts.

- Application code belongs in the repository.
- Database schema belongs in Alembic migrations and is prepared through
  explicit **Database Setup**.
- No real match data, odds data, database dumps, generated training datasets,
  or trained model artifacts are shipped.
- Generated football data does not belong in Git. Rebuild or ingest it locally
  through operational workflows.
- Local model artifacts are generated product assets. **Model Training** writes
  them under the configured model artifact home, but trained artifacts remain
  local.
- Database dumps, exports, logs, caches, and other runtime outputs are generated
  data, not source.

## Local onboarding

Use this path on a fresh clone to reach a schema-only empty dashboard state.
That state has the database structure in place, but no private match data,
odds data, training datasets, or trained model artifacts.

Prerequisites:

- Python 3.11.
- PostgreSQL with an empty local database you control.
- Node.js and npm for the Svelte dashboard.

Install Python dependencies and copy the example environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

The example file uses safe local placeholders:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_intelligence
DB_USER=football
DB_PASSWORD=football
DATABASE_URL=postgresql+psycopg2://football:football@localhost:5432/football_intelligence
API_FOOTBALL_KEY=
GROQ_API_KEY=
VITE_API_URL=http://localhost:5000
```

Adjust those values to match your local PostgreSQL role and database. Leave
`API_FOOTBALL_KEY` empty until you run **Source Data Ingestion**. Leave
`GROQ_API_KEY` empty unless you use the **Football Intelligence Agent** chat
API with the default Groq adapter.

Run **Database Setup** before **Source Data Ingestion**, **Prediction Refresh**,
or **Model Training**:

```bash
make db-setup
make db-current
```

`make db-setup` applies the Alembic schema migrations. It does not import match
data, create training datasets, or download a trained model. After this step,
the API and dashboard can run against an empty schema and show honest empty
states.

Start the read-only API:

```bash
python -m uvicorn football_intelligence.api:app --host 0.0.0.0 --port 5000
```

Build and run the dashboard in another shell:

```bash
cd frontend
npm install
npm run build
npm start
```

Open the dashboard at the local frontend URL. With only **Database Setup**
complete, expect a schema-only empty dashboard state: **Football Data Status**,
the **Prediction Board**, **Market Value Signals**, and **Feature Snapshots**
can load without bundled data and without API startup mutating the database.

## Product surfaces

The API, frontend dashboard, operational workflows, and **Football Intelligence
Agent** are separate surfaces:

- The API exposes read-only HTTP endpoints for the dashboard and the agent chat
  contract. API startup does not run **Database Setup** and does not mutate
  schema.
- The frontend dashboard is a read-only Svelte inspection surface for
  **Football Data Status**, the **Prediction Board**, **Market Value Signals**,
  and **Feature Snapshots**.
- Operational workflows are CLI commands for **Source Data Ingestion**,
  **Prediction Refresh**, **Model Training**, status, boards, value scans, and
  backtests. These workflows assume **Database Setup** has already run.
- The **Football Intelligence Agent** answers **Natural-Language Football
  Questions** through curated read-only **Analyst Tools**. It is not the
  dashboard and it does not run operational workflows.

## Deployment boundaries

Operational football workflows are CLI-first application interfaces. Deployment
platforms decide when and where to run them, but they do not own the core
architecture.

- **Database Setup** prepares or upgrades schema before the API or operational
  workflows run. Alembic is the canonical schema mechanism, and API startup is
  read-only.

- **Source Data Ingestion** brings external football source data into a schema
  that has already been prepared by **Database Setup**.

- **Prediction Refresh** runs the **Match Intelligence Lifecycle** without
  training a new model. It updates match data, incorporates newly
  **Completed Matches** into feature state, builds the **Future Feature Set**,
  creates **Predictions** for **Upcoming Matches**, and can refresh odds.

  ```bash
  python -m football_intelligence.cli prediction-refresh
  ```

  To test the refresh in parts, use `--only`:

  ```bash
  python -m football_intelligence.cli prediction-refresh --list-parts
  python -m football_intelligence.cli prediction-refresh --only source-data
  python -m football_intelligence.cli prediction-refresh --only features
  python -m football_intelligence.cli prediction-refresh --only inference
  python -m football_intelligence.cli prediction-refresh --only odds
  ```

- **Model Training** is separate and intentional. It learns a new prediction
  model from the **Historical Feature Set** and writes model artifacts when the
  run is not a dry run. Trained model artifacts are local generated outputs
  saved under `models/`; the public repository tracks only the directory
  placeholder and does not include private `.pkl` artifacts.

  ```bash
  python -m football_intelligence.cli model-training
  ```

- **Football Data Status** shows read-only football-data readiness facts and
  warnings without collapsing them into a single score.

  ```bash
  make status
  ```

- The **Football Intelligence Agent** answers natural-language questions via
  the API chat contract when its optional LLM environment is configured.

Docker, cron, or another host can run those same commands. The repository keeps
one backend `Dockerfile`, one `docker-compose.yml`, and one root
`requirements.txt` so runtime wiring stays tidy and does not become the
conceptual owner of **Prediction Refresh**, **Model Training**, or the
**Match Intelligence Lifecycle**.
