WITH SeasonProgress AS (
    SELECT 
        match_id,
        home_score,
        away_score,
        start_time,
        season_start_date,
        season_end_date,
        -- Calculate days from season start
        JULIANDAY(start_time) - JULIANDAY(season_start_date) AS days_from_season_start,
        -- Calculate total season length in days
        JULIANDAY(season_end_date) - JULIANDAY(season_start_date) AS season_length_days,
        -- Calculate normalized position in season (0 to 1)
        (JULIANDAY(start_time) - JULIANDAY(season_start_date)) / 
        (JULIANDAY(season_end_date) - JULIANDAY(season_start_date)) AS season_progress
    FROM matches
    WHERE 
        season_start_date IS NOT NULL
        AND season_end_date IS NOT NULL
        AND start_time IS NOT NULL
        AND home_score IS NOT NULL
        AND away_score IS NOT NULL
        -- Ensure valid season dates (end comes after start)
        AND JULIANDAY(season_end_date) > JULIANDAY(season_start_date)
        -- Ensure match is within season dates
        AND JULIANDAY(start_time) >= JULIANDAY(season_start_date)
        AND JULIANDAY(start_time) <= JULIANDAY(season_end_date)
),

SeasonProgressDeciles AS (
    SELECT 
        match_id,
        home_score,
        away_score,
        -- Create decile groups (0-0.1, 0.1-0.2, etc.)
        CAST(FLOOR(season_progress * 10) / 10.0 AS TEXT) || '-' || 
        CAST(CEIL(season_progress * 10) / 10.0 AS TEXT) AS season_stage,
        -- Alternative grouping approach using CASE
        CASE
            WHEN season_progress < 0.1 THEN 'Early Season (0-10%)'
            WHEN season_progress < 0.3 THEN 'Early-Mid Season (10-30%)'
            WHEN season_progress < 0.7 THEN 'Mid Season (30-70%)'
            WHEN season_progress < 0.9 THEN 'Mid-Late Season (70-90%)'
            ELSE 'Late Season (90-100%)'
        END AS season_phase,
        CASE 
            WHEN home_score = away_score THEN 1 
            ELSE 0 
        END AS is_draw
    FROM SeasonProgress
),

DecileStats AS (
    SELECT 
        season_stage,
        COUNT(*) AS total_matches,
        SUM(is_draw) AS total_draws,
        ROUND(100.0 * SUM(is_draw) / COUNT(*), 2) AS draw_percentage
    FROM SeasonProgressDeciles
    GROUP BY season_stage
    ORDER BY season_stage
),

PhaseStats AS (
    SELECT 
        season_phase,
        COUNT(*) AS total_matches,
        SUM(is_draw) AS total_draws,
        ROUND(100.0 * SUM(is_draw) / COUNT(*), 2) AS draw_percentage
    FROM SeasonProgressDeciles
    GROUP BY season_phase
    ORDER BY 
        CASE season_phase
            WHEN 'Early Season (0-10%)' THEN 1
            WHEN 'Early-Mid Season (10-30%)' THEN 2
            WHEN 'Mid Season (30-70%)' THEN 3
            WHEN 'Mid-Late Season (70-90%)' THEN 4
            WHEN 'Late Season (90-100%)' THEN 5
        END
),

OverallStats AS (
    SELECT 
        'Overall' AS comparison,
        COUNT(*) AS total_matches,
        SUM(CASE WHEN home_score = away_score THEN 1 ELSE 0 END) AS total_draws,
        ROUND(100.0 * SUM(CASE WHEN home_score = away_score THEN 1 ELSE 0 END) / COUNT(*), 2) AS draw_percentage
    FROM matches
    WHERE 
        home_score IS NOT NULL
        AND away_score IS NOT NULL
)

-- Use UNION ALL to combine all results into a single output
SELECT 'By Deciles:' AS analysis_type, NULL AS metric, NULL AS total_matches, NULL AS total_draws, NULL AS draw_percentage
UNION ALL
SELECT 
    NULL AS analysis_type,
    season_stage AS metric, 
    total_matches, 
    total_draws, 
    draw_percentage 
FROM DecileStats

UNION ALL
SELECT '' AS analysis_type, NULL AS metric, NULL AS total_matches, NULL AS total_draws, NULL AS draw_percentage
UNION ALL
SELECT 'By Season Phase:' AS analysis_type, NULL AS metric, NULL AS total_matches, NULL AS total_draws, NULL AS draw_percentage
UNION ALL
SELECT 
    NULL AS analysis_type,
    season_phase AS metric, 
    total_matches, 
    total_draws, 
    draw_percentage 
FROM PhaseStats

UNION ALL
SELECT '' AS analysis_type, NULL AS metric, NULL AS total_matches, NULL AS total_draws, NULL AS draw_percentage
UNION ALL
SELECT 
    NULL AS analysis_type,
    comparison AS metric, 
    total_matches, 
    total_draws, 
    draw_percentage 
FROM OverallStats;

/* Comment out or remove the feature generation query
SELECT 
    match_id,
    (JULIANDAY(start_time) - JULIANDAY(season_start_date)) / 
    (JULIANDAY(season_end_date) - JULIANDAY(season_start_date)) AS season_progress,
    CASE
        WHEN (JULIANDAY(start_time) - JULIANDAY(season_start_date)) / 
             (JULIANDAY(season_end_date) - JULIANDAY(season_start_date)) < 0.1 THEN 'Early Season (0-10%)'
        WHEN (JULIANDAY(start_time) - JULIANDAY(season_start_date)) / 
             (JULIANDAY(season_end_date) - JULIANDAY(season_start_date)) < 0.3 THEN 'Early-Mid Season (10-30%)'
        WHEN (JULIANDAY(start_time) - JULIANDAY(season_start_date)) / 
             (JULIANDAY(season_end_date) - JULIANDAY(season_start_date)) < 0.7 THEN 'Mid Season (30-70%)'
        WHEN (JULIANDAY(start_time) - JULIANDAY(season_start_date)) / 
             (JULIANDAY(season_end_date) - JULIANDAY(season_start_date)) < 0.9 THEN 'Mid-Late Season (70-90%)'
        ELSE 'Late Season (90-100%)'
    END AS season_phase
FROM matches
WHERE 
    season_start_date IS NOT NULL
    AND season_end_date IS NOT NULL
    AND start_time IS NOT NULL
    AND JULIANDAY(season_end_date) > JULIANDAY(season_start_date)
    AND JULIANDAY(start_time) >= JULIANDAY(season_start_date)
    AND JULIANDAY(start_time) <= JULIANDAY(season_end_date);
*/