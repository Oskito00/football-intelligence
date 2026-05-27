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

## Deployment boundary

The durable operational interface is the CLI, not any host-specific scheduler
file:

- **Prediction Refresh**: `python -m football_intelligence.cli prediction-refresh`
- **Model Training**: `python -m football_intelligence.cli model-training`

Heroku, Docker, cron, or another runtime can invoke those commands. Existing
Heroku scheduler files are compatibility runners during migration, not the
conceptual owner of **Prediction Refresh**, **Model Training**, or the
**Match Intelligence Lifecycle**.

Initial read-only football queries live in `football_intelligence.database`:

- `ReadOnlyFootballQueries.get_match_prediction(match_id)` returns one **Prediction** dictionary or `None`.
- `ReadOnlyFootballQueries.get_multiple_match_predictions(match_ids)` returns a dictionary keyed by match ID.
- `ReadOnlyFootballQueries.get_upcoming_matches(...)` returns **Upcoming Match** dictionaries.
- `ReadOnlyFootballQueries.get_recent_form(...)` returns `{"success", "error", "data"}` for completed-match form analysis.
- `ReadOnlyFootballQueries.get_best_odds_for_multiple_matches(match_ids)` returns best odds by match ID and outcome.
- `ReadOnlyFootballQueries.analyze_matches_for_value(match_ids)` returns model-vs-odds value analysis without mutating football data.

Database failures raise `FootballQueryError` so Analyst Tools can distinguish backend errors from valid no-result lookups.

Initial **Analyst Tools** live in `football_intelligence.analyst`:

- `AnalystFootballTools.definitions` returns the curated tool catalogue for `match_prediction`, `upcoming_matches`, `recent_form`, `match_odds`, and `value_lookup`.
- `AnalystFootballTools.run(name, arguments)` dispatches one read-only tool by name.
- Direct methods are available for the same tools when deterministic Python callers do not need name-based dispatch.

Every Analyst Tool returns a stable envelope:

```python
{"success": bool, "tool": str, "error": dict | None, "data": object | None}
```

Tool data is converted to agent-safe Python values, including ISO strings for dates and datetimes. Analyst Tools call `ReadOnlyFootballQueries`; they do not expose arbitrary SQL or reach into legacy chatbot internals.

Migration pattern:

1. Keep existing import paths working while behavior moves gradually.
2. Add product-language interfaces in this namespace before changing callers.
3. Use lazy compatibility exports only as temporary bridges to legacy modules.
4. Move real implementation into these package homes in follow-up issues, then delete the bridge export when no callers need it.
