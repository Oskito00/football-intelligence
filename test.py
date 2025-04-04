import sqlite3

def get_upcoming_matches_query():
    """Get all future matches without duplicates, including team lineups."""
    return """
    SELECT DISTINCT 
        m.match_id as fixture_id,
        m.start_time,
        m.competition_name,
        m.competition_id,
        m.competition_type,
        m.competition_phase,
        m.round_display,
        m.season_id,
        m.home_team_id,
        m.away_team_id,
        m.home_team_name as home_team,
        m.away_team_name as away_team,
        m.home_score as home_goals,
        m.away_score as away_goals,
        m.referee_id,
        m.match_status,
        NULL as home_formation,
        NULL as away_formation,
        NULL as home_players,
        NULL as away_players
    FROM matches m
    WHERE (m.match_status IS NULL OR m.match_status = '' OR m.match_status != 'ended')
    AND m.start_time >= datetime('now')

    UNION

    SELECT DISTINCT 
        tl.match_id as fixture_id,
        tl.start_time,
        NULL as competition_name,
        NULL as competition_id,
        NULL as competition_type,
        NULL as competition_phase,
        NULL as round_display,
        NULL as season_id,
        tl.home_team_id,
        tl.away_team_id,
        tl.home_team_name as home_team,
        tl.away_team_name as away_team,
        NULL as home_goals,
        NULL as away_goals,
        NULL as referee_id,
        NULL as match_status,
        tl.home_formation,
        tl.away_formation,
        tl.home_players,
        tl.away_players
    FROM team_lineups tl
    WHERE tl.start_time >= datetime('now')
    AND NOT EXISTS (SELECT 1 FROM matches m WHERE m.match_id = tl.match_id)
    
    ORDER BY start_time
    """

# Connect to your SQLite database
conn = sqlite3.connect('football_data.db')  # Replace with your database file
cursor = conn.cursor()

# Execute the query
query = get_upcoming_matches_query()
cursor.execute(query)

# Fetch the results
upcoming_matches = cursor.fetchall()

# Print the results
for match in upcoming_matches:
    print(match)

# Close the connection
conn.close()