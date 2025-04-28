
# TODO: This function should only fetch matches that have is_processed = 0
# So that when new matches are added to the database, the old matches are not processed again...
# Will add this when I combine elo and form functions into one script.
def get_all_matches(conn):
    """Gets all matches ordered by start time."""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT m.match_id, m.start_time, m.competition_id, m.competition_name, m.competition_country, m.home_team_id, m.home_team_name, m.away_team_id, m.away_team_name, 
               m.home_score, m.away_score,
               home_comp.main_competition_id AS home_main_comp_id,
               home_comp.main_competition_country AS home_main_comp_country,
               away_comp.main_competition_id AS away_main_comp_id,
               away_comp.main_competition_country AS away_main_comp_country
        FROM matches m
        LEFT JOIN team_main_competition home_comp ON m.home_team_id = home_comp.team_id
        LEFT JOIN team_main_competition away_comp ON m.away_team_id = away_comp.team_id
        WHERE m.home_score IS NOT NULL AND m.away_score IS NOT NULL
        ORDER BY datetime(m.start_time)
    ''')
    return cursor.fetchall()


def get_main_league_and_nation_data(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT match_id, home_team_id, home_team_name, away_team_id, away_team_name, competition_season_id, season_start_date, season_end_date, competition_id, competition_name, competition_country FROM matches WHERE home_team_domestic_league_id IS NULL AND away_team_domestic_league_id IS NULL AND away_team_domestic_country IS NULL AND home_team_domestic_country IS NULL")
    return cursor.fetchall()
