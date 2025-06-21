-- Create the teams mapping table
CREATE TABLE IF NOT EXISTS teams_mapping (
    team_id INTEGER PRIMARY KEY,
    team_name VARCHAR(255) NOT NULL,
    domestic_country VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_team_name ON teams_mapping(team_name);
CREATE INDEX IF NOT EXISTS idx_team_name_lower ON teams_mapping(LOWER(team_name));

-- Insert unique team_id entries, deduplicated
INSERT INTO teams_mapping (team_id, team_name, domestic_country)
SELECT DISTINCT ON (team_id)
    team_id,
    team_name,
    country
FROM (
    SELECT home_team_id AS team_id, home_team_name AS team_name, competition_country AS country
    FROM matches
    WHERE home_team_id IS NOT NULL

    UNION ALL

    SELECT away_team_id AS team_id, away_team_name AS team_name, competition_country AS country
    FROM matches
    WHERE away_team_id IS NOT NULL
) AS all_teams
WHERE team_id IS NOT NULL
ORDER BY team_id, team_name  -- arbitrarily picks one name if there are duplicates
ON CONFLICT (team_id) DO UPDATE
SET 
    team_name = EXCLUDED.team_name,
    domestic_country = EXCLUDED.domestic_country;