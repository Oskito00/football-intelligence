# Football Intelligence Package Migration

`football_intelligence` is the product namespace for the staged **Football Intelligence Agent** refactor.

Use these package homes for new code:

- `football_intelligence.analyst`: read-only **Analyst Agent** and **Analyst Tools**.
- `football_intelligence.ingestion`: source football data ingestion.
- `football_intelligence.features`: **Historical Feature Set** and **Future Feature Set** builders.
- `football_intelligence.predictions`: **Prediction** inference, evaluation, and **Model Training**.
- `football_intelligence.api`: API entrypoints that expose agent capabilities.
- `football_intelligence.database`: database access interfaces.
- `football_intelligence.cli`: operational commands such as **Prediction Refresh**.

Deployment boundary:

The durable operational interface is the CLI, not any host-specific scheduler
file. **Prediction Refresh** is available through
`python -m football_intelligence.cli prediction-refresh`, and **Model Training**
is available through `python -m football_intelligence.cli model-training`.
Heroku, Docker, cron, or another runtime can invoke those commands. Existing
Heroku scheduler files are compatibility runners during migration, not the
conceptual owner of the **Match Intelligence Lifecycle**.

Initial read-only football queries live in `football_intelligence.database`:

- `ReadOnlyFootballQueries.get_match_prediction(match_id)` returns one **Prediction** dictionary or `None`.
- `ReadOnlyFootballQueries.get_multiple_match_predictions(match_ids)` returns a dictionary keyed by match ID.
- `ReadOnlyFootballQueries.get_upcoming_matches(...)` returns **Upcoming Match** dictionaries.
- `ReadOnlyFootballQueries.get_recent_form(...)` returns `{"success", "error", "data"}` for completed-match form analysis.
- `ReadOnlyFootballQueries.get_best_odds_for_multiple_matches(match_ids)` returns best odds by match ID and outcome.
- `ReadOnlyFootballQueries.analyze_matches_for_value(match_ids)` returns model-vs-odds value analysis without mutating football data.

Database failures raise `FootballQueryError` so Analyst Tools can distinguish backend errors from valid no-result lookups.

Migration pattern:

1. Keep existing import paths working while behavior moves gradually.
2. Add product-language interfaces in this namespace before changing callers.
3. Use lazy compatibility exports only as temporary bridges to legacy modules.
4. Move real implementation into these package homes in follow-up issues, then delete the bridge export when no callers need it.
