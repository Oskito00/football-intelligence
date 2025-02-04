# Previous matches query with team stats
PREVIOUS_MATCHES_QUERY = """
    WITH TeamMatches AS (
        SELECT 
            m.match_id,
            m.start_time,
            m.competition_name,
            m.home_team_name,
            m.away_team_name,
            m.home_score,
            m.away_score,
            m.season_id,
            CASE 
                WHEN m.home_team_name = ? THEN 'home'
                ELSE 'away'
            END as team_position
        FROM matches m
        WHERE (m.home_team_name = ? OR m.away_team_name = ?)
            AND m.start_time < ?
            AND m.match_status = 'ended'
        ORDER BY m.start_time DESC
        LIMIT ?
    )
    SELECT 
        tm.*,
        ts.ball_possession,
        ts.passes_successful,
        ts.passes_total,
        ts.shots_total,
        ts.shots_on_target,
        ts.chances_created,
        ts.tackles_successful,
        ts.tackles_total,
        ts.shots_saved
    FROM TeamMatches tm
    LEFT JOIN team_stats ts ON tm.match_id = ts.match_id 
        AND ((tm.team_position = 'home' AND ts.qualifier = 'home')
         OR (tm.team_position = 'away' AND ts.qualifier = 'away'))
    """

ENDED_MATCHES_QUERY = """
SELECT 
    m.match_id as fixture_id,
    m.start_time,
    m.competition_name,
    m.competition_id,
    m.competition_type,
    m.competition_phase,
    m.round_display,
    m.season_id,
    m.home_team_id, --See if this works
    m.away_team_id, --See if this works
    m.home_team_name as home_team,
    m.away_team_name as away_team,
    m.home_score as home_goals,
    m.away_score as away_goals,
    m.referee_id,
    
    -- Home team stats (all metrics)
    home_stats.ball_possession as home_ball_possession,
    home_stats.cards_given as home_cards_given,
    home_stats.chances_created as home_chances_created,
    home_stats.clearances as home_clearances,
    home_stats.corner_kicks as home_corner_kicks,
    home_stats.crosses_successful as home_crosses_successful,
    home_stats.crosses_total as home_crosses_total,
    home_stats.crosses_unsuccessful as home_crosses_unsuccessful,
    home_stats.defensive_blocks as home_defensive_blocks,
    home_stats.diving_saves as home_diving_saves,
    home_stats.dribbles_completed as home_dribbles_completed,
    home_stats.fouls as home_fouls,
    home_stats.free_kicks as home_free_kicks,
    home_stats.goal_kicks as home_goal_kicks,
    home_stats.injuries as home_injuries,
    home_stats.interceptions as home_interceptions,
    home_stats.long_passes_successful as home_long_passes_successful,
    home_stats.long_passes_total as home_long_passes_total,
    home_stats.long_passes_unsuccessful as home_long_passes_unsuccessful,
    home_stats.loss_of_possession as home_loss_of_possession,
    home_stats.offsides as home_offsides,
    home_stats.passes_successful as home_passes_successful,
    home_stats.passes_total as home_passes_total,
    home_stats.passes_unsuccessful as home_passes_unsuccessful,
    home_stats.red_cards as home_red_cards,
    home_stats.shots_blocked as home_shots_blocked,
    home_stats.shots_off_target as home_shots_off_target,
    home_stats.shots_on_target as home_shots_on_target,
    home_stats.shots_saved as home_shots_saved,
    home_stats.shots_total as home_shots_total,
    home_stats.substitutions as home_substitutions,
    home_stats.tackles_successful as home_tackles_successful,
    home_stats.tackles_total as home_tackles_total,
    home_stats.tackles_unsuccessful as home_tackles_unsuccessful,
    home_stats.throw_ins as home_throw_ins,
    home_stats.was_fouled as home_was_fouled,
    home_stats.yellow_cards as home_yellow_cards,
    home_stats.yellow_red_cards as home_yellow_red_cards,
    
    -- Away team stats (all metrics)
    away_stats.ball_possession as away_ball_possession,
    away_stats.cards_given as away_cards_given,
    away_stats.chances_created as away_chances_created,
    away_stats.clearances as away_clearances,
    away_stats.corner_kicks as away_corner_kicks,
    away_stats.crosses_successful as away_crosses_successful,
    away_stats.crosses_total as away_crosses_total,
    away_stats.crosses_unsuccessful as away_crosses_unsuccessful,
    away_stats.defensive_blocks as away_defensive_blocks,
    away_stats.diving_saves as away_diving_saves,
    away_stats.dribbles_completed as away_dribbles_completed,
    away_stats.fouls as away_fouls,
    away_stats.free_kicks as away_free_kicks,
    away_stats.goal_kicks as away_goal_kicks,
    away_stats.injuries as away_injuries,
    away_stats.interceptions as away_interceptions,
    away_stats.long_passes_successful as away_long_passes_successful,
    away_stats.long_passes_total as away_long_passes_total,
    away_stats.long_passes_unsuccessful as away_long_passes_unsuccessful,
    away_stats.loss_of_possession as away_loss_of_possession,
    away_stats.offsides as away_offsides,
    away_stats.passes_successful as away_passes_successful,
    away_stats.passes_total as away_passes_total,
    away_stats.passes_unsuccessful as away_passes_unsuccessful,
    away_stats.red_cards as away_red_cards,
    away_stats.shots_blocked as away_shots_blocked,
    away_stats.shots_off_target as away_shots_off_target,
    away_stats.shots_on_target as away_shots_on_target,
    away_stats.shots_saved as away_shots_saved,
    away_stats.shots_total as away_shots_total,
    away_stats.substitutions as away_substitutions,
    away_stats.tackles_successful as away_tackles_successful,
    away_stats.tackles_total as away_tackles_total,
    away_stats.tackles_unsuccessful as away_tackles_unsuccessful,
    away_stats.throw_ins as away_throw_ins,
    away_stats.was_fouled as away_was_fouled,
    away_stats.yellow_cards as away_yellow_cards,
    away_stats.yellow_red_cards as away_yellow_red_cards

FROM matches m
LEFT JOIN team_stats home_stats 
    ON m.match_id = home_stats.match_id 
    AND home_stats.qualifier = 'home'
LEFT JOIN team_stats away_stats 
    ON m.match_id = away_stats.match_id 
    AND away_stats.qualifier = 'away'
WHERE m.match_status = 'ended'
ORDER BY m.start_time
"""

# Query to check team stats table summary
STATS_CHECK_QUERY = """
SELECT COUNT(*) as count, 
       COUNT(DISTINCT match_id) as unique_matches,
       COUNT(DISTINCT team_name) as unique_teams
FROM team_stats
"""

