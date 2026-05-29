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
when a new model should be learned from the **Historical Feature Set**.
Artifacts are saved locally under `models/` when the run is not a dry run; the
repository tracks only a placeholder for that generated artifact home.

```bash
python -m football_intelligence.cli model-training
```

## Read-Only Review

Use these commands to inspect current football data without changing it:

```bash
python -m football_intelligence.cli status
python -m football_intelligence.cli board today
python -m football_intelligence.cli value-picks
python -m football_intelligence.cli value-picks --today
python -m football_intelligence.cli value-backtest
```

## Value Backtest

Run a **Value Backtest** when you want the research answer to: "If the
starting bankroll was 100, what did it become after replaying historical
**Market Value Signals**?" The default command starts with 100 and the report
headline answers the "100 became X" question directly:

```bash
python -m football_intelligence.cli value-backtest
```

Default strategy:

- Starting bankroll is 100.
- Kelly fraction is 1.0, meaning full Kelly.
- Minimum expected value is 0, so every **Market Value Signal** with a positive
  Kelly stake can qualify.
- Multiple qualifying outcomes in the same **Completed Match** can each receive
  a **Paper Stake**.
- Prediction timing is strict: retained **Predictions** must be before kickoff.
- **Backtest Odds Mode** is `best`, meaning the simulation uses the highest
  available pre-kickoff bookmaker odds for each outcome.

Use comparison runs to inspect whether the historical result survives different
assumptions:

| Question | Command |
| --- | --- |
| What happens with quarter Kelly? | `python -m football_intelligence.cli value-backtest --kelly-fraction 0.25` |
| What happens if signals need at least 5% expected value? | `python -m football_intelligence.cli value-backtest --min-expected-value 0.05` |
| What happens with the best retained pre-kickoff price? | `python -m football_intelligence.cli value-backtest --odds-mode best` |
| What happens with the average retained pre-kickoff price? | `python -m football_intelligence.cli value-backtest --odds-mode average` |

**Backtest Odds Mode** controls how historical pre-kickoff odds are selected.
`best` assumes the highest available price across retained bookmaker odds;
`average` uses the average available price and is a more conservative robustness
check.

Interpret the report as research output. **Paper Stakes** are hypothetical
research stakes, not betting advice, real-money recommendations, or proof that
the model should be followed with cash. A profitable historical result is
evidence to inspect, not proof of future profitability. Compare the headline
bankroll, ROI, max drawdown, bankroll peak and trough, skipped-match counts,
and individual **Paper Stake** audit rows before drawing conclusions.

The v1 limitation is the retained-prediction data model. This **Value Backtest**
uses retained **Predictions** per **Completed Match**; if old predictions were
overwritten, it may not reconstruct every historical prediction revision. That
is different from a true prediction-snapshot history, where every prediction
available at each historical decision time would be stored and replayed.

Future extensions should keep this distinction visible while adding stronger
diagnostics such as calibration diagnostics, Brier score, log loss, prediction
snapshots, and walk-forward analysis.
