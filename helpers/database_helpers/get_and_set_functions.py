import sqlite3
from typing import List, Dict

def get_from_matches(conn, select_str, columns, where_clause=None, order_by=None, limit=None):
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
    select_str = f'{select_str} ' if select_str else ''
    where_clause_str = f'WHERE {where_clause}' if where_clause else ''
    order_by_str = f'ORDER BY {order_by}' if order_by else ''
    limit_str = f'LIMIT {limit}' if limit else ''

    cursor.execute(f'{select_str} {columns_str} FROM matches {where_clause_str} {order_by_str} {limit_str}')
    return cursor.fetchall()

def get_from_standings(conn, select_str, columns, where_clause=None, order_by=None, limit=None):
    """A dynamic function that gets data from the standings table.
    
    Args:
        conn (sqlite3.Connection): The database connection.
        columns (list): The columns to select.
        where_clause (str): The WHERE clause to filter the data.
        order_by (str): The ORDER BY clause to sort the data.
        limit (int): The LIMIT clause to limit the number of rows returned.
    """
    cursor = conn.cursor()

    columns_str = ', '.join(columns)
    select_str = f'{select_str} ' if select_str else ''
    where_clause_str = f'WHERE {where_clause}' if where_clause else ''
    order_by_str = f'ORDER BY {order_by}' if order_by else ''
    limit_str = f'LIMIT {limit}' if limit else ''

    cursor.execute(f'{select_str} {columns_str} FROM league_standings {where_clause_str} {order_by_str} {limit_str}')
    return cursor.fetchall()

def bulk_insert_formations(formations: List[Dict], db_path: str = 'api_football.db'):
    """
    Bulk insert formations dictionaries into SQL table.
    
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
