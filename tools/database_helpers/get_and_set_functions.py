def get_all_matches(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT match_id, home_team_id, home_team_name, away_team_id, away_team_name, home_score, away_score FROM matches WHERE home_score IS NOT NULL AND away_score IS NOT NULL AND elo_processed = 0")
    return cursor.fetchall()