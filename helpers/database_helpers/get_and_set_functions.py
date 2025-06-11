import sqlite3
from typing import List, Dict

import pandas as pd

def get_from_matches(conn, select_str, columns, where_clause=None, from_clause=None, order_by=None, limit=None, where_clause_args=None):
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
    from_clause_str = f'FROM {from_clause}' if from_clause else 'FROM matches'
    order_by_str = f'ORDER BY {order_by}' if order_by else ''
    limit_str = f'LIMIT {limit}' if limit else ''

    cursor.execute(f'{select_str} {columns_str} {from_clause_str} {where_clause_str} {order_by_str} {limit_str}')
    return cursor.fetchall()

def get_from_standings(conn, select_str, columns, where_clause=None, order_by=None, limit=None, where_clause_args=None):
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

    cursor.execute(f'{select_str} {columns_str} FROM league_standings {where_clause_str} {order_by_str} {limit_str}', where_clause_args) if where_clause_args else cursor.execute(f'{select_str} {columns_str} FROM league_standings {where_clause_str} {order_by_str} {limit_str}')
    return cursor.fetchall()

def load_from_postgres(
    engine,
    table: str,
    select: str = "*",
    where: str = None,
    drop_columns: list[str] = None,
    limit: int = None
) -> pd.DataFrame:
    """
    Load data from any PostgreSQL table using SQLAlchemy with flexible SELECT/WHERE/LIMIT clauses.
    Mostly used for loading data for training.
    #TODO: Use this function instead of the ones above

    Args:
        table (str): Table name to query.
        select (str): Comma-separated column list or "*" (default).
        where (str): Optional WHERE clause (without 'WHERE').
        drop_columns (list): List of column names to drop.
        limit (int): Optional LIMIT clause.

    Returns:
        pd.DataFrame: Resulting dataframe.
    """
    print(f"Loading data from {table}")
    query = f"SELECT {select} FROM {table}"
    if where:
        query += f" WHERE {where}"
    if limit:
        query += f" LIMIT {limit}"
    
    df = pd.read_sql_query(query, engine)

    if drop_columns:
        df.drop(columns=drop_columns, inplace=True, errors='ignore')

    return df

def update_processed_status(conn, match_ids, with_formation_flags, mode='training'):
    """Update processing status for processed matches"""
    cursor = conn.cursor()
    try:
        # Prepare data for bulk update
        update_data = [
            (match_id, True, with_formation, mode) 
            for match_id, with_formation in zip(match_ids, with_formation_flags)
        ]
        
        cursor.executemany('''
            INSERT INTO processed_info (match_id, is_processed, with_formation, processing_mode)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (match_id) DO UPDATE SET
                is_processed = EXCLUDED.is_processed,
                with_formation = EXCLUDED.with_formation,
                processing_mode = EXCLUDED.processing_mode,
                processed_at = CURRENT_TIMESTAMP
        ''', update_data)
        
        conn.commit()
        print(f"Updated processing status for {len(match_ids)} matches")
        
    except Exception as e:
        print(f"Error updating processed status: {str(e)}")
        conn.rollback()
        raise
    finally:
        cursor.close()

def bulk_insert_formations(formations: List[Dict], conn):
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
    INSERT INTO formations 
        (match_id, home_team_formation, away_team_formation)
        VALUES (%s, %s, %s)
        ON CONFLICT (match_id) 
        DO UPDATE SET 
        home_team_formation = EXCLUDED.home_team_formation, 
        away_team_formation = EXCLUDED.away_team_formation;
    """
    
    # Prepare data
    data = [
        (f['match_id'], f['home_team_formation'], f['away_team_formation'])
        for f in formations
    ]
    
    cursor = conn.cursor()
    cursor.execute(create_table_sql)
    cursor.executemany(insert_sql, data)
    conn.commit()
    
    print(f"Inserted/updated {len(data)} formations")
