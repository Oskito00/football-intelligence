<script lang="ts">
  type DashboardWarning = {
    code?: string;
    severity?: string;
    message: string;
  };

  type Prediction = {
    predicted_result: string;
    confidence: number | null;
    probabilities: {
      home_win: number | null;
      draw: number | null;
      away_win: number | null;
    };
    model_type?: string | null;
    prediction_date?: string | null;
  };

  type OddsFreshness = {
    has_odds: boolean;
    latest_retrieved_at: string | null;
    latest_api_last_updated: string | null;
  };

  type MarketValueSignal = {
    match_id?: number;
    start_time?: string | null;
    home_team?: string | null;
    away_team?: string | null;
    competition?: string | null;
    country?: string | null;
    outcome: string;
    model_probability: number | null;
    best_odds: number | null;
    implied_probability: number | null;
    edge: number | null;
    bookmaker: string | null;
    paper_stake_percentage: number | null;
  };

  type BoardMatch = {
    match_id: number;
    start_time: string | null;
    home_team: string;
    away_team: string;
    competition: string;
    country: string;
    competition_id?: number | null;
    prediction: Prediction | null;
    odds_freshness: OddsFreshness;
    market_value_signals: MarketValueSignal[];
  };

  type PredictionBoard = {
    title: string;
    date: string;
    generated_at?: string;
    window: {
      starts_at: string;
      ends_at: string;
      timezone: string;
    };
    summary: {
      upcoming_match_count: number;
      matches_with_predictions: number;
      matches_with_odds: number;
      market_value_signal_count: number;
    };
    matches: BoardMatch[];
    warnings: DashboardWarning[];
    empty_state: string | null;
  };

  type MarketValueSignalScan = {
    title: string;
    window: {
      starts_at: string;
      ends_at: string;
      timezone: string;
      label: string;
    };
    summary: {
      upcoming_match_count: number;
      matches_with_predictions: number;
      matches_with_odds: number;
      matches_with_value_signals: number;
      market_value_signal_count: number;
    };
    signals: MarketValueSignal[];
    warnings: DashboardWarning[];
    empty_state: string | null;
  };

  type FootballDataStatus = {
    odds_freshness: {
      latest_retrieved_at: string | null;
      matches_with_odds_next_7_days: number;
    };
    top_premier_league_elo_teams: {
      team_name: string;
      elo: number | null;
    }[];
    warnings: DashboardWarning[];
  };

  const API_URL = import.meta.env.VITE_API_URL || "";

  let board: PredictionBoard | null = null;
  let valueSignals: MarketValueSignalScan | null = null;
  let status: FootballDataStatus | null = null;
  let loading = true;
  let errorMessage = "";

  const fetchPredictionBoard = async () => {
    const response = await fetch(`${API_URL}/api/board/today`);

    if (!response.ok) {
      throw new Error(`Prediction Board request failed with ${response.status}`);
    }

    return (await response.json()) as PredictionBoard;
  };

  const fetchMarketValueSignals = async () => {
    const response = await fetch(`${API_URL}/api/value-signals?today=true`);

    if (!response.ok) {
      throw new Error(`Market Value Signals request failed with ${response.status}`);
    }

    return (await response.json()) as MarketValueSignalScan;
  };

  const fetchFootballDataStatus = async () => {
    const response = await fetch(`${API_URL}/api/status`);

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as FootballDataStatus;
  };

  const loadDashboard = async () => {
    loading = true;
    errorMessage = "";

    try {
      [board, valueSignals, status] = await Promise.all([
        fetchPredictionBoard(),
        fetchMarketValueSignals(),
        fetchFootballDataStatus(),
      ]);
    } catch (error) {
      board = null;
      valueSignals = null;
      status = null;
      errorMessage =
        error instanceof Error ? error.message : "Prediction Board is unavailable.";
    } finally {
      loading = false;
    }
  };

  const formatValue = (value: string | number | null | undefined) => {
    if (value === null || value === undefined || value === "") {
      return "None";
    }

    return String(value);
  };

  const formatPercent = (value: number | null | undefined) => {
    if (value === null || value === undefined) {
      return "None";
    }

    return `${(value * 100).toFixed(1)}%`;
  };

  const formatPlainPercent = (value: number | null | undefined) => {
    if (value === null || value === undefined) {
      return "None";
    }

    return `${value.toFixed(1)}%`;
  };

  loadDashboard();
</script>

<main class="dashboard">
  <section class="board" aria-labelledby="board-title">
    <div class="page-header">
      <div>
        <p class="eyebrow">Read-only dashboard</p>
        <h1 id="board-title">Prediction Board</h1>
      </div>
      <button class="refresh-button" type="button" onclick={loadDashboard}>
        Refresh
      </button>
    </div>

    {#if loading}
      <div class="state">Loading Prediction Board...</div>
    {:else if errorMessage}
      <div class="state error">{errorMessage}</div>
    {:else if board}
      <div class="summary-grid" aria-label="Prediction Board summary">
        <article class="fact">
          <span>Upcoming Matches</span>
          <strong>{board.summary.upcoming_match_count}</strong>
        </article>
        <article class="fact">
          <span>With Predictions</span>
          <strong>{board.summary.matches_with_predictions}</strong>
        </article>
        <article class="fact">
          <span>With Odds</span>
          <strong>{board.summary.matches_with_odds}</strong>
        </article>
        <article class="fact">
          <span>Market Value Signals</span>
          <strong>{board.summary.market_value_signal_count}</strong>
        </article>
      </div>

      <div class="content-grid">
        <section class="match-list" aria-label="Today matches">
          {#if board.empty_state}
            <div class="state">{board.empty_state}</div>
          {:else}
            {#each board.matches as match}
              <article class="match-card">
                <div class="match-main">
                  <div>
                    <span class="kickoff">{formatValue(match.start_time)}</span>
                    <h2>{match.home_team} vs {match.away_team}</h2>
                    <p>{match.competition} / {match.country}</p>
                  </div>
                  <div class:missing={!match.prediction} class="prediction-pill">
                    {#if match.prediction}
                      <span>{match.prediction.predicted_result}</span>
                      <strong>{formatPercent(match.prediction.confidence)}</strong>
                    {:else}
                      <span>Prediction</span>
                      <strong>Missing</strong>
                    {/if}
                  </div>
                </div>

                {#if match.prediction}
                  <div class="probabilities">
                    <span>Home {formatPercent(match.prediction.probabilities.home_win)}</span>
                    <span>Draw {formatPercent(match.prediction.probabilities.draw)}</span>
                    <span>Away {formatPercent(match.prediction.probabilities.away_win)}</span>
                  </div>
                {/if}

                <div class="match-meta">
                  <span>
                    Odds:
                    {match.odds_freshness.has_odds
                      ? formatValue(match.odds_freshness.latest_retrieved_at)
                      : "Missing"}
                  </span>
                  {#if match.market_value_signals.length}
                    <span>{match.market_value_signals.length} signals</span>
                  {:else}
                    <span>No signals</span>
                  {/if}
                </div>

                {#if match.market_value_signals.length}
                  <ul class="signal-list">
                    {#each match.market_value_signals as signal}
                      <li>
                        <span>{signal.outcome}</span>
                        <span>{formatPercent(signal.edge)} edge</span>
                        <span>{formatPlainPercent(signal.paper_stake_percentage)} Paper Stake</span>
                      </li>
                    {/each}
                  </ul>
                {/if}
              </article>
            {/each}
          {/if}
        </section>

        <aside class="side-rail" aria-label="Dashboard context">
          <section class="context-panel">
            <h2>Market Value Signals</h2>
            <strong>
              {formatValue(valueSignals?.summary.market_value_signal_count)}
            </strong>
            {#if valueSignals?.signals.length}
              <ul class="signal-detail-list">
                {#each valueSignals.signals as signal}
                  <li>
                    <div>
                      <span>{formatValue(signal.home_team)} vs {formatValue(signal.away_team)}</span>
                      <small>{formatValue(signal.outcome)} / {formatValue(signal.bookmaker)}</small>
                    </div>
                    <div>
                      <strong>{formatPercent(signal.edge)}</strong>
                      <small>{formatPlainPercent(signal.paper_stake_percentage)} Paper Stake</small>
                    </div>
                  </li>
                {/each}
              </ul>
            {:else}
              <p class="empty">
                {valueSignals?.empty_state || "No Market Value Signals available."}
              </p>
            {/if}
          </section>

          <section class="context-panel">
            <h2>Odds Freshness</h2>
            <strong>{formatValue(status?.odds_freshness.latest_retrieved_at)}</strong>
            <p>
              {formatValue(status?.odds_freshness.matches_with_odds_next_7_days)}
              matches with odds in the next 7 days
            </p>
          </section>

          <section class="context-panel">
            <h2>Top Premier League Elo Teams</h2>
            {#if status?.top_premier_league_elo_teams.length}
              <ol class="team-list">
                {#each status.top_premier_league_elo_teams as team}
                  <li>
                    <span>{team.team_name}</span>
                    <strong>{formatValue(team.elo)}</strong>
                  </li>
                {/each}
              </ol>
            {:else}
              <p class="empty">No Elo teams available.</p>
            {/if}
          </section>

          <section class="context-panel">
            <h2>Warnings</h2>
            {#if board.warnings.length || valueSignals?.warnings.length || status?.warnings.length}
              <ul class="warning-list">
                {#each board.warnings as warning}
                  <li>{warning.message}</li>
                {/each}
                {#each valueSignals?.warnings || [] as warning}
                  <li>{warning.message}</li>
                {/each}
                {#each status?.warnings || [] as warning}
                  <li>{warning.message}</li>
                {/each}
              </ul>
            {:else}
              <p class="empty">No warnings.</p>
            {/if}
          </section>
        </aside>
      </div>
    {:else}
      <div class="state">Prediction Board is empty.</div>
    {/if}
  </section>
</main>
