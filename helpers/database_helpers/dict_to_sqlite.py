import sqlite3

import sqlite3

def dict_to_sqlite(conn, table_name, data_dicts, batch_size=1000):
    """Insert a list of dictionaries into a SQLite table with match_id as INTEGER."""
    if not data_dicts:
        return
    
    cursor = conn.cursor()
    
    # Create table with proper types
    first = data_dicts[0]
    columns = []

    for k in first.keys():
        col_type = "INTEGER" if k == "match_id" else "TEXT"
        columns.append(f'"{k}" {col_type}')
    
    columns_sql = ", ".join(columns)
    cursor.execute(f'CREATE TABLE IF NOT EXISTS {table_name} ({columns_sql})')
    
    # Prepare insert statement
    placeholders = ', '.join(['?'] * len(first))  # Use '?' for SQLite
    columns_str = ', '.join(f'"{k}"' for k in first.keys())
    sql = f'INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})'
    
    # Ensure match_id is int before insertion
    for d in data_dicts:
        if "match_id" in d and d["match_id"] is not None:
            d["match_id"] = int(d["match_id"])

    # Batch insert
    for i in range(0, len(data_dicts), batch_size):
        batch = data_dicts[i:i+batch_size]
        try:
            cursor.executemany(sql, [tuple(d.values()) for d in batch])
            conn.commit()
        except sqlite3.IntegrityError as e:
            print(f"Skipping duplicate in batch {i//batch_size}: {str(e)}")
            conn.rollback()

def combine_stats(match_id, home_stats, away_stats):
    """A helper function to combine two dictionaries, prefix the data by either home_ or away_ and add match_id as the first key"""
    # Ensure match_id is first
    combined = {'match_id': match_id}
    
    # Add home stats
    combined.update(
        {f'home_{k}': v for k, v in home_stats.items()}
    )
    
    # Add away stats
    combined.update(
        {f'away_{k}': v for k, v in away_stats.items()}
    )
    
    return combined