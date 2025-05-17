import sqlite3
from helpers.database_helpers.get_and_set_functions import get_all_matches

def process_competition_history(db_path, batch_size=10000):
    """
    Creates and populates a competition_history table using batch inserts.
    
    Args:
        db_path: Path to the SQLite database
        batch_size: Number of records to insert in each batch
    """
    conn = sqlite3.connect(db_path)
    
    # Create the competition_history table if it doesn't exist
    conn.execute('''
    CREATE TABLE IF NOT EXISTS match_info_history (
        match_id INTEGER,
        start_time DATETIME,
        competition_season_name TEXT,
        competition_id INTEGER,
        competition_name TEXT,
        competition_country TEXT,
        home_team_name TEXT,
        away_team_name TEXT,
        PRIMARY KEY (match_id, competition_id)
    )
    ''')
    
    # Get all unprocessed matches using the existing function
    matches = get_all_matches(conn)
    first_5000 = matches[:5000]
    rest = matches[5000:]
    print(f"Found {len(matches)} unprocessed matches")
    
    # Extract match_id and competition_id from each match
    competition_history_data = []
    processed_match_ids = []
    
    for match in rest:
        match_id = match[0]         # match_id is at index 0
        start_time = match[1]
        competition_season_name = match[2]
        competition_id = match[3]   # competition_id is at index 3
        competition_name = match[4]
        competition_country = match[5]
        home_team_name = match[7]
        away_team_name = match[9]
        
        if competition_id is not None:
            competition_history_data.append((match_id, start_time, competition_season_name, competition_id, competition_name, competition_country, home_team_name, away_team_name))
            processed_match_ids.append(match_id)
    
    # Batch insert into competition_history table
    total_inserted = 0
    cursor = conn.cursor()
    
    for i in range(0, len(competition_history_data), batch_size):
        batch = competition_history_data[i:i+batch_size]
        try:
            cursor.executemany('''
            INSERT OR IGNORE INTO match_info_history (match_id, start_time, competition_season_name, competition_id, competition_name, competition_country, home_team_name, away_team_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', batch)
            
            # Count how many were actually inserted (ignoring duplicates)
            total_inserted += cursor.rowcount
        except Exception as e:
            print(f"Error inserting batch {i//batch_size + 1}: {str(e)}")
    
    # Commit and close
    conn.commit()
    print(f"Inserted {total_inserted} rows into match_info_history")
    conn.close()

if __name__ == "__main__":
    process_competition_history('api_football.db')