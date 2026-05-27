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

- **Model Training** is separate and intentional. It learns a new prediction
  model from the **Historical Feature Set** and writes model artifacts when the
  run is not a dry run.

  ```bash
  python -m football_intelligence.cli model-training
  ```

Heroku, Docker, cron, or another host can run those same commands. The existing
Heroku scheduler files are one runner kept for migration compatibility; they
should not be treated as the conceptual owner of **Prediction Refresh**,
**Model Training**, or the **Match Intelligence Lifecycle**.

Follow-up work can add Docker-native or host-specific entrypoints and remove
legacy Heroku scheduler files after callers have moved to the CLI commands.
That cleanup is intentionally outside this documentation slice.
