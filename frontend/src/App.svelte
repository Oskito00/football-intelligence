<script lang="ts">
  type CompletedMatch = {
    match_id: number;
    start_time: string | null;
    home_team: string;
    away_team: string;
    competition: string;
    country: string;
    score: string;
  };

  type OddsFreshness = {
    latest_retrieved_at: string | null;
    latest_api_last_updated: string | null;
    matches_with_odds_next_7_days: number;
    stale_after_hours: number;
  };

  type EloTeam = {
    team_id: number;
    team_name: string;
    elo: number | null;
    competition: string;
    country: string;
  };

  type StatusWarning = {
    code: string;
    severity: string;
    message: string;
  };

  type FootballDataStatus = {
    title: string;
    latest_completed_match: CompletedMatch | null;
    unprocessed_completed_matches: number;
    latest_elo_history_date: string | null;
    future_feature_set_count: number;
    prediction_count_next_7_days: number;
    odds_freshness: OddsFreshness;
    top_premier_league_elo_teams: EloTeam[];
    warnings: StatusWarning[];
  };

  const API_URL = import.meta.env.VITE_API_URL || "";

  let status: FootballDataStatus | null = null;
  let loading = true;
  let errorMessage = "";

  const loadStatus = async () => {
    loading = true;
    errorMessage = "";

    try {
      const response = await fetch(`${API_URL}/api/status`);
      if (!response.ok) {
        throw new Error(`Status request failed with ${response.status}`);
      }
      status = await response.json();
    } catch (error) {
      status = null;
      errorMessage =
        error instanceof Error
          ? error.message
          : "Football Data Status is unavailable.";
    } finally {
      loading = false;
    }
  };

  const formatValue = (value: string | number | null | undefined) =>
    value === null || value === undefined || value === "" ? "None" : String(value);

  loadStatus();
</script>

<main class="dashboard">
  <section class="panel" aria-labelledby="status-title">
    <div class="panel-header">
      <div>
        <p class="eyebrow">Read-only dashboard</p>
        <h1 id="status-title">Football Data Status</h1>
      </div>
      <button class="refresh-button" type="button" onclick={loadStatus}>
        Refresh
      </button>
    </div>

    {#if loading}
      <div class="state">Loading Football Data Status...</div>
    {:else if errorMessage}
      <div class="state error">{errorMessage}</div>
    {:else if status}
      <div class="status-grid">
        <article class="fact wide">
          <span>Latest Completed Match</span>
          {#if status.latest_completed_match}
            <strong>
              {status.latest_completed_match.home_team}
              {status.latest_completed_match.score}
              {status.latest_completed_match.away_team}
            </strong>
            <small>
              {status.latest_completed_match.competition} /
              {formatValue(status.latest_completed_match.start_time)}
            </small>
          {:else}
            <strong>None</strong>
          {/if}
        </article>

        <article class="fact">
          <span>Unprocessed Completed Matches</span>
          <strong>{status.unprocessed_completed_matches}</strong>
        </article>

        <article class="fact">
          <span>Latest Elo History Date</span>
          <strong>{formatValue(status.latest_elo_history_date)}</strong>
        </article>

        <article class="fact">
          <span>Future Feature Set</span>
          <strong>{status.future_feature_set_count}</strong>
        </article>

        <article class="fact">
          <span>Next 7 Days Predictions</span>
          <strong>{status.prediction_count_next_7_days}</strong>
        </article>

        <article class="fact wide">
          <span>Odds Freshness</span>
          <strong>
            {formatValue(status.odds_freshness.latest_retrieved_at)}
          </strong>
          <small>
            {status.odds_freshness.matches_with_odds_next_7_days} matches with
            odds in the next 7 days
          </small>
        </article>
      </div>

      <div class="split">
        <section class="list-section" aria-labelledby="elo-title">
          <h2 id="elo-title">Top Premier League Elo Teams</h2>
          {#if status.top_premier_league_elo_teams.length}
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

        <section class="list-section" aria-labelledby="warnings-title">
          <h2 id="warnings-title">Warnings</h2>
          {#if status.warnings.length}
            <ul class="warning-list">
              {#each status.warnings as warning}
                <li>{warning.message}</li>
              {/each}
            </ul>
          {:else}
            <p class="empty">No warnings.</p>
          {/if}
        </section>
      </div>
    {:else}
      <div class="state">Football Data Status is empty.</div>
    {/if}
  </section>
</main>
