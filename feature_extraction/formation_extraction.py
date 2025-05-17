import json
from typing import List, Dict
import sqlite3

from helpers.database_helpers.get_and_set_functions import get_all_formations

def formation_extraction(matches):
    formations = []
    for match in matches:
        try:
            match_id, home_formation_str, away_formation_str = match

            print(match_id)
            
            # Safely get formation type
            formations.append({
                'match_id': match_id,
                'home_team_formation': home_formation_str,
                'away_team_formation': away_formation_str
            })
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Skipping match {match_id}: {str(e)}")
            continue
    
    bulk_insert_formations(formations)
            
    return formations


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


if __name__ == "__main__":
    conn = sqlite3.connect('api_football.db')
    formations = get_all_formations(conn)
    print("Length of formations: ", len(formations))
    formation_extraction(formations)