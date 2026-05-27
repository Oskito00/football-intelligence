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

Migration pattern:

1. Keep existing import paths working while behavior moves gradually.
2. Add product-language interfaces in this namespace before changing callers.
3. Use lazy compatibility exports only as temporary bridges to legacy modules.
4. Move real implementation into these package homes in follow-up issues, then delete the bridge export when no callers need it.
