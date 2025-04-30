WITH MatchStats AS (
    SELECT 
        team_id,
        match_id,
        start_time,
        result,
        -- Previous matches within last 10 days
        (
            SELECT COUNT(*) 
            FROM TeamMatchHistory t2 
            WHERE t2.team_id = t1.team_id
            AND t2.start_time < t1.start_time
            AND t2.start_time > datetime(t1.start_time, '-10 days')
        ) AS games_last_10,
        
        -- Draws in previous 10 days
        (
            SELECT COUNT(*) 
            FROM TeamMatchHistory t2 
            WHERE t2.team_id = t1.team_id
            AND t2.start_time < t1.start_time
            AND t2.start_time > datetime(t1.start_time, '-10 days')
            AND t2.result = 'draw'
        ) AS draws_last_10,
        
        -- Previous matches within last 20 days
        (
            SELECT COUNT(*) 
            FROM TeamMatchHistory t2 
            WHERE t2.team_id = t1.team_id
            AND t2.start_time < t1.start_time
            AND t2.start_time > datetime(t1.start_time, '-20 days')
        ) AS games_last_20,
        
        -- Draws in last 20 days
        (
            SELECT COUNT(*) 
            FROM TeamMatchHistory t2 
            WHERE t2.team_id = t1.team_id
            AND t2.start_time < t1.start_time
            AND t2.start_time > datetime(t1.start_time, '-20 days')
            AND t2.result = 'draw'
        ) AS draws_last_20
        
    FROM TeamMatchHistory t1
)

SELECT 
    period,
    games_in_period,
    COUNT(*) AS total_matches,
    SUM(CASE WHEN current_result = 'draw' THEN 1 ELSE 0 END) AS current_draws,
    1.0 * SUM(CASE WHEN current_result = 'draw' THEN 1 ELSE 0 END) / COUNT(*) AS draw_rate
FROM (
    SELECT 
        '10 Days' AS period,
        games_last_10 AS games_in_period,
        result AS current_result
    FROM MatchStats
    UNION ALL
    SELECT 
        '20 Days',
        games_last_20,
        result
    FROM MatchStats
) 
GROUP BY period, games_in_period
ORDER BY period, games_in_period;