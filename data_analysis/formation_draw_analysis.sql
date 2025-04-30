WITH FormationData AS (
    SELECT 
        match_id,
        json_extract(home_team_formation, '$.type') AS home_formation,
        json_extract(away_team_formation, '$.type') AS away_formation,
        CASE 
            WHEN home_score > away_score THEN 'win'
            WHEN away_score > home_score THEN 'loss'
            ELSE 'draw'
        END AS result
    FROM matches
    WHERE 
        home_score IS NOT NULL
        AND away_score IS NOT NULL
        AND json_valid(home_team_formation)
        AND json_valid(away_team_formation)
        AND json_extract(home_team_formation, '$.type') IS NOT NULL
        AND json_extract(away_team_formation, '$.type') IS NOT NULL
),

FormationMatchups AS (
    SELECT 
        home_formation,
        away_formation,
        COUNT(*) AS total_matches,
        SUM(CASE WHEN result = 'draw' THEN 1 ELSE 0 END) AS draws,
        1.0 * SUM(CASE WHEN result = 'draw' THEN 1 ELSE 0 END) / COUNT(*) AS draw_rate
    FROM FormationData
    GROUP BY home_formation, away_formation
),

SymmetricMatchups AS (
    SELECT 
        CASE WHEN home_formation < away_formation 
             THEN home_formation || ' vs ' || away_formation
             ELSE away_formation || ' vs ' || home_formation 
        END AS formation_pair,
        SUM(total_matches) AS total_matches,
        SUM(draws) AS total_draws,
        1.0 * SUM(draws) / SUM(total_matches) AS draw_rate
    FROM FormationMatchups
    GROUP BY CASE WHEN home_formation < away_formation 
                  THEN home_formation || ' vs ' || away_formation
                  ELSE away_formation || ' vs ' || home_formation 
             END
)

SELECT 
    formation_pair,
    total_matches,
    total_draws,
    draw_rate
FROM SymmetricMatchups
WHERE total_matches >= 5  -- Adjust threshold as needed
ORDER BY draw_rate DESC, total_matches DESC;

SELECT 
    COUNT(*) AS total_matches,
    SUM(CASE WHEN json_valid(home_team_formation) 
              AND json_valid(away_team_formation)
              AND json_extract(home_team_formation, '$.type') IS NOT NULL
              AND json_extract(away_team_formation, '$.type') IS NOT NULL
             THEN 1 ELSE 0 END) AS matches_with_formations,
    SUM(CASE WHEN home_score IS NOT NULL 
              AND away_score IS NOT NULL THEN 1 ELSE 0 END) AS matches_with_scores
FROM matches;