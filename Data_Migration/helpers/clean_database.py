import sqlite3
from pathlib import Path

def drop_all_tables(cursor):
    """Drop all existing tables from the database"""
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name NOT LIKE 'sqlite_%'
    """)
    tables = cursor.fetchall()
    
    for table in tables:
        print(f"Dropping table: {table[0]}")
        cursor.execute(f"DROP TABLE IF EXISTS {table[0]}")

def clean_database(db_file):
    """Clean the database by dropping all tables and recreating them"""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    print("\nDropping existing tables...")
    drop_all_tables(cursor)
    
    conn.commit()
    conn.close()
    print(f"\nDatabase {db_file} has been cleaned.")

if __name__ == "__main__":
    clean_database('football_data.db')