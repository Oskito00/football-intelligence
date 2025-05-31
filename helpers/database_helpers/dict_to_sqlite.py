import sqlite3

def dict_to_sqlite(db_path, table_name, data_dicts, batch_size=1000):
    """A helper function to insert a list of dictionaries into a specific table
    
    Args:
        db_path (str): The path to the database
        table_name (str): The name of the table to insert the data into
        data_dicts (list): A list of dictionaries to insert into the table
        batch_size (int): The number of dictionaries to insert in each batch
    """
    if not data_dicts:
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table using first dict's keys
    first = data_dicts[0]

    columns = ', '.join(f'"{k}" TEXT' for k in first.keys())
    cursor.execute(f'CREATE TABLE IF NOT EXISTS {table_name} ({columns})')
    
    # Prepare insert statement
    placeholders = ', '.join(['?'] * len(first))
    columns_str = ', '.join(f'"{k}"' for k in first.keys())
    sql = f'INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})'
    
    # Process in batches
    for i in range(0, len(data_dicts), batch_size):
        batch = data_dicts[i:i+batch_size]
        try:
            cursor.executemany(sql, [tuple(d.values()) for d in batch])
            conn.commit()
        except sqlite3.IntegrityError as e:
            print(f"Skipping duplicate in batch {i//batch_size}: {str(e)}")
            conn.rollback()
    
    conn.close()

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