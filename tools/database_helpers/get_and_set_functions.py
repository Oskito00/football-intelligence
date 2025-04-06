
#NOTE: This function fetches from both matches and team_main_competition tables.
# If you do not have team_main_competition table, run the Tools/infer_main_competition.py script to create it.
# This will create a new table with the main competition and country for each team you have in your dataset.
def get_all_matches(conn):
    """Gets all matches whilst adding main competition and country to each match"""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT m.match_id, m.start_time, m.competition_id, m.competition_name, m.home_team_id, m.home_team_name, m.away_team_id, m.away_team_name, 
               m.home_score, m.away_score,
               home_comp.main_competition_id AS home_main_comp_id,
               home_comp.main_competition_country AS home_main_comp_country,
               away_comp.main_competition_id AS away_main_comp_id,
               away_comp.main_competition_country AS away_main_comp_country
        FROM matches m
        LEFT JOIN team_main_competition home_comp ON m.home_team_id = home_comp.team_id
        LEFT JOIN team_main_competition away_comp ON m.away_team_id = away_comp.team_id
        WHERE m.home_score IS NOT NULL AND m.away_score IS NOT NULL
    ''')
    return cursor.fetchall()


def get_main_league_and_nation_data(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT home_team_id, home_team_name, away_team_id, away_team_name, competition_id, competition_name, competition_country FROM matches")
    return cursor.fetchall()
