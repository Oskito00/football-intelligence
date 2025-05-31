

import sqlite3
from helpers.data_processing.processing_functions.elo import calculate_elos
from helpers.database_helpers.get_and_set_functions import get_from_matches

def process_data(conn):
    matches = get_from_matches(conn, select_str='SELECT DISTINCT', columns=['match_id', 'start_time', 'competition_season_name', 'competition_id', 'competition_name', 'competition_country', 'home_team_id', 'home_team_name', 'away_team_id', 'away_team_name', 
               'home_score', 'away_score', 'home_team_domestic_league_id', 'home_team_domestic_country', 'away_team_domestic_league_id', 'away_team_domestic_country'], where_clause='home_score IS NOT NULL AND away_score IS NOT NULL AND is_processed = 0', order_by='datetime(start_time)')
    calculate_elos(conn, matches)


if __name__ == "__main__":
    conn = sqlite3.connect('api_football.db')
    process_data(conn)