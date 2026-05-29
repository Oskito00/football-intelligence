# Inbetments

Inbetments is evolving toward a **Football Intelligence Agent**: a user-facing
assistant that answers natural-language football questions using trusted
football data, **Predictions**, odds, and analysis.

## Deployment boundaries

Operational football workflows are CLI-first application interfaces. Deployment
platforms decide when and where to run them, but they do not own the core
architecture.

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
