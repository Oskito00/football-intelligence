# Football Intelligence Package Migration

`football_intelligence` is the product namespace for **Football Intelligence**:
prediction workflows, odds-aware inspection, research signals, and the staged
**Football Intelligence Agent**.

Use these package homes for new code:

- `football_intelligence.analyst`: read-only **Analyst Agent** and **Analyst Tools**.
- `football_intelligence.ingestion`: source football data ingestion.
- `football_intelligence.features`: **Historical Feature Set** and **Future Feature Set** builders.
- `football_intelligence.predictions`: **Prediction** inference, evaluation, and **Model Training**.
- `football_intelligence.status`: **Football Data Status** facts and warnings.
- `football_intelligence.api`: API entrypoints that expose agent capabilities.
- `football_intelligence.database`: **Database Setup** and database access interfaces.
- `football_intelligence.cli`: operational commands such as **Prediction Refresh**.

## Deployment boundary

The durable operational interface is the CLI, not any host-specific trigger
file:

- **Database Setup**: Alembic is the canonical schema setup and upgrade
  mechanism. API startup is read-only and assumes setup has already run.
- **Prediction Refresh**: `python -m football_intelligence.cli prediction-refresh`
- **Model Training**: `python -m football_intelligence.cli model-training`
- **Football Data Status**: `python -m football_intelligence.cli status`

Prediction Refresh can also be tested in parts:

```bash
python -m football_intelligence.cli prediction-refresh --list-parts
python -m football_intelligence.cli prediction-refresh --only source-data
python -m football_intelligence.cli prediction-refresh --only features
python -m football_intelligence.cli prediction-refresh --only inference
python -m football_intelligence.cli prediction-refresh --only odds
```

Docker, cron, or another runtime can invoke those commands. The repository keeps
one backend `Dockerfile`, one `docker-compose.yml`, and one root
`requirements.txt`; those files invoke the Football Intelligence CLI instead of
compatibility runners, so they are not the conceptual owner of
**Prediction Refresh**, **Model Training**, or the **Match Intelligence Lifecycle**.

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

Tool data is converted to agent-safe Python values, including ISO strings for dates and datetimes. Analyst Tools call `ReadOnlyFootballQueries`; they do not expose arbitrary SQL or reach into retired implementation internals.

The first read-only **Analyst Agent** also lives in `football_intelligence.analyst`:

- `AnalystAgent.answer_question(question)` routes a **Natural-Language Football Question** through a planner, executes only curated Analyst Tools, and synthesizes the final answer.
- `AnalystAgent.from_config(llm)` wires the configured read-only football queries to LangChain-backed planner and answer synthesis adapters.
- Planned tool calls are checked against `AnalystFootballTools.definitions` before execution, so operational requests such as scraping, Prediction Refresh, arbitrary SQL, inference, or Model Training are refused by the agent boundary.
- Answers that use Prediction data include a standard uncertainty note so model estimates are not presented as football facts.

LangChain imports are isolated to the analyst agent module and are loaded only when the default LangChain adapters are constructed.

The existing chat API contract is served from `football_intelligence.api`:

- `POST /api/chat` still accepts `{"text": "..."}` and returns `{"response": "..."}`.
- `POST /api/reset` still returns `{"message": "Conversation reset successfully"}`.
- `GET /api/status` returns deterministic **Football Data Status** facts and warnings.
- API conversation memory keeps recent user and assistant messages for follow-up context; reset clears that memory.
- The API delegates answers to the read-only **Analyst Agent**, so it does not expose Prediction Refresh, Model Training, ingestion, arbitrary SQL, or other operational capabilities.

Migration status:

1. Active product behavior is owned by `football_intelligence.*` modules.
2. New callers should use the product-level interfaces above instead of
   implementation-era package names.
3. Retired implementation-era packages and inactive experiments have been
   deleted rather than kept as compatibility surfaces.

## Feature schema registry

`football_intelligence.features.schema` is the tracer-bullet home for feature
family schema definitions. The first registered family is `form`, centralizing:

- Historical and Future Feature Set table names: `form_history` and
  `form_future`.
- Storage columns and JSON columns written by the form feature manager.
- JSON loader selects, minimum form-history length checks, and draw-feature
  expansion columns expected by the result model loader.

Follow-up feature-family migrations should add their table pairs, storage
columns, JSON expansion rules, and loader expectations to the registry first,
then update the manager, table DDL, and model loader to consume the same schema
definition before changing behavior.
