# Football Intelligence

Football Intelligence produces football **Predictions**, inspects odds context
and **Market Value Signals**, and answers **Natural-Language Football
Questions** through the **Football Intelligence Agent**. The dashboard is one
read-only surface of that product, not the whole architecture.

The project is not a betting tips app. **Market Value Signals**, **Paper
Stakes**, and **Value Backtests** are research outputs for inspecting model and
market behavior, not betting advice or real-money recommendations.

## Repository boundaries

The public repository ships code and schema, not private football data or
trained model artifacts.

- Application code belongs in the repository.
- Database schema belongs in Alembic migrations and is prepared through
  explicit **Database Setup**.
- Generated football data does not belong in Git. Rebuild or ingest it through
  operational workflows.
- Local model artifacts are generated product assets. **Model Training** writes
  them under the configured model artifact home, but trained artifacts remain
  local.
- Database dumps, exports, logs, caches, and other runtime outputs are generated
  data, not source.

## Deployment boundaries

Operational football workflows are CLI-first application interfaces. Deployment
platforms decide when and where to run them, but they do not own the core
architecture.

- **Database Setup** prepares or upgrades schema before the API or operational
  workflows run. Alembic is the canonical schema mechanism, and API startup is
  read-only.

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
  run is not a dry run.

  ```bash
  python -m football_intelligence.cli model-training
  ```

- **Football Data Status** shows read-only football-data readiness facts and
  warnings without collapsing them into a single score.

  ```bash
  make status
  ```

Docker, cron, or another host can run those same commands. The repository keeps
one backend `Dockerfile`, one `docker-compose.yml`, and one root
`requirements.txt` so runtime wiring stays tidy and does not become the
conceptual owner of **Prediction Refresh**, **Model Training**, or the
**Match Intelligence Lifecycle**.
