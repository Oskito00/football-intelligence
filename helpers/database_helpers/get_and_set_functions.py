def get_from_matches(conn, columns, where_clause=None, order_by=None, limit=None):
    cursor = conn.cursor()

    columns_str = ', '.join(columns)
    where_clause_str = f'WHERE {where_clause}' if where_clause else ''
    order_by_str = f'ORDER BY {order_by}' if order_by else ''
    limit_str = f'LIMIT {limit}' if limit else ''

    cursor.execute(f'SELECT {columns_str} FROM matches {where_clause_str} {order_by_str} {limit_str}')
    return cursor.fetchall()

def get_all_matches(conn):
    """Gets all matches ordered by start time."""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT match_id, start_time, competition_season_name, competition_id, competition_name, competition_country, home_team_id, home_team_name, away_team_id, away_team_name, 
               home_score, away_score, home_team_domestic_league_id, home_team_domestic_country, away_team_domestic_league_id, away_team_domestic_country
        FROM matches
        WHERE home_score IS NOT NULL AND away_score IS NOT NULL AND is_processed = 0
        ORDER BY datetime(start_time)
    ''')
    return cursor.fetchall()


def get_all_formations(conn):
    cursor = conn.cursor()
    cursor.execute('''
        SELECT match_id, home_team_formation, away_team_formation FROM matches WHERE home_team_formation IS NOT NULL AND away_team_formation IS NOT NULL AND home_score IS NOT NULL AND away_score IS NOT NULL AND is_processed = 0
    ''')
    return cursor.fetchall()

def get_all_stage_of_season(conn):
    cursor = conn.cursor()
    cursor.execute('''
        SELECT match_id, start_time, season_start_date, season_end_date FROM matches WHERE home_score IS NOT NULL AND away_score IS NOT NULL AND is_processed = 0
    ''')
    return cursor.fetchall()

def get_all_matches_for_fatigue(conn):
    cursor = conn.cursor()
    cursor.execute('''
        SELECT match_id, start_time, home_team_id, away_team_id FROM matches WHERE home_score IS NOT NULL AND away_score IS NOT NULL AND is_processed = 0
    ''')
    return cursor.fetchall()

def get_main_league_and_nation_data(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT match_id, home_team_id, home_team_name, away_team_id, away_team_name, competition_season_id, season_start_date, season_end_date, competition_id, competition_name, competition_country FROM matches WHERE home_team_domestic_league_id IS NULL AND away_team_domestic_league_id IS NULL AND away_team_domestic_country IS NULL AND home_team_domestic_country IS NULL")
    return cursor.fetchall()
