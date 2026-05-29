# Operational Commands

This handbook lists the boring commands for day-to-day Football Intelligence
operations. Use these shortcuts when running known workflows by hand; the Make
targets intentionally call the same CLI contracts that deployment runtimes use.

`scrape` is shortcut slang for **Source Data Ingestion**. It is convenient
operator shorthand, not the product term.

## Prediction Refresh Shortcuts

These targets are aliases over **Prediction Refresh** selectors. They do not
create a second workflow language.

| Shortcut | Command | What It Runs |
| --- | --- | --- |
| `make scrape` | `python -m football_intelligence.cli prediction-refresh --only source-data-ingestion` | **Source Data Ingestion** for source match data |
| `make process-history` | `python -m football_intelligence.cli prediction-refresh --only historical-feature-set` | Rebuild the **Historical Feature Set** from **Completed Matches** |
| `make build-future` | `python -m football_intelligence.cli prediction-refresh --only future-feature-set` | Rebuild the **Future Feature Set** from **Upcoming Matches** |
| `make predict` | `python -m football_intelligence.cli prediction-refresh --only prediction-inference` | Run current prediction inference |
| `make odds` | `python -m football_intelligence.cli prediction-refresh --only odds-refresh` | Refresh odds for **Upcoming Matches** |
| `make tonight` | `python -m football_intelligence.cli board today` | Show today's remaining **Prediction Board** |

Run the full **Prediction Refresh** when the whole **Match Intelligence
Lifecycle** should be updated without **Model Training**:

```bash
python -m football_intelligence.cli prediction-refresh
```

## Model Training

**Model Training** is separate from **Prediction Refresh**. Run it deliberately
when a new model should be learned from the **Historical Feature Set**:

```bash
python -m football_intelligence.cli model-training
```

## Read-Only Review

Use these commands to inspect current football data without changing it:

```bash
python -m football_intelligence.cli status
python -m football_intelligence.cli board today
```
