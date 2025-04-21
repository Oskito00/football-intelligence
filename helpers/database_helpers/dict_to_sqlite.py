import sqlite3

def dict_to_sqlite(db_path, table_name, data_dicts, batch_size=1000):
    """Process multiple dictionaries in batches"""
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