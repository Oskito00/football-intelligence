import sqlite3
from typing import List, Dict

def get_from_matches(conn, columns, where_clause=None, order_by=None, limit=None):
    """A dynamic function that gets data from the matches table.
    
    Args:
        conn (sqlite3.Connection): The database connection.
        columns (list): The columns to select.
        where_clause (str): The WHERE clause to filter the data.
        order_by (str): The ORDER BY clause to sort the data.
        limit (int): The LIMIT clause to limit the number of rows returned.
    """
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


def bulk_insert_formations(formations: List[Dict], db_path: str = 'api_football.db'):
    """
    Bulk insert formations into SQL table.
    
    Args:
        formations: List of dicts with keys:
                   - match_id (str)
                   - home_team_formation (str)
                   - away_team_formation (str)
        db_path: Path to SQLite database
    """
    # Create table if not exists
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS formations (
        match_id TEXT PRIMARY KEY,
        home_team_formation TEXT,
        away_team_formation TEXT
    )
    """
    
    # Insert/ignore existing
    insert_sql = """
    INSERT OR IGNORE INTO formations 
    (match_id, home_team_formation, away_team_formation)
    VALUES (?, ?, ?)
    """
    
    # Prepare data
    data = [
        (f['match_id'], f['home_team_formation'], f['away_team_formation'])
        for f in formations
    ]
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(create_table_sql)
        cursor.executemany(insert_sql, data)
        conn.commit()
    
    print(f"Inserted/updated {len(data)} formations")
