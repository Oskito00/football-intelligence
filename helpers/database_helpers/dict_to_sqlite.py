import sqlite3

def dict_to_sqlite(db_path, table_name, data_dict):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table if not exists
    
    columns = ', '.join(f'"{k}" TEXT' for k in data_dict.keys())
    cursor.execute(f'CREATE TABLE IF NOT EXISTS {table_name} ({columns})')
    
    # Insert data
    placeholders = ', '.join(['?'] * len(data_dict))
    columns = ', '.join(f'"{k}"' for k in data_dict.keys())
    sql = f'INSERT INTO {table_name} ({columns}) VALUES ({placeholders})'
    
    cursor.execute(sql, tuple(data_dict.values()))
    conn.commit()
    conn.close()