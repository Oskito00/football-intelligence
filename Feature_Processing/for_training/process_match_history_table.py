import sqlite3
from datetime import datetime

def process_matches_to_history(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Process unprocessed matches in batches
    while True:
        # Get batch of unprocessed matches (100 at a time)
        cursor.execute("""
            SELECT match_id, start_time, home_team_id, away_team_id,
                   home_score, away_score 
            FROM matches 
            WHERE processed_match_history = 0 AND match_status != 'not_started' AND home_score IS NOT NULL AND away_score IS NOT NULL
            LIMIT 100
        """)
        batch = cursor.fetchall()
        
        if not batch:
            break  # No more matches to process
            
        # Prepare data for TeamMatchHistory
        history_data = []
        skipped_match_ids = []
        
        for match in batch:
            match_id, start_time, home_id, away_id, home_score, away_score = match
            print("Processing match: ", match_id)
            # Convert start_time to date (assuming ISO format)
            match_date = datetime.fromisoformat(start_time).date().isoformat()
            
            # Home team entry
            history_data.append((
                home_id,
                match_id,
                match_date,
                home_score,
                away_score,
                'win' if home_score > away_score else 'loss' if home_score < away_score else 'draw',
                3 if home_score > away_score else 0 if home_score < away_score else 1,
                1  # is_home=True
            ))
            
            # Away team entry
            history_data.append((
                away_id,
                match_id,
                match_date,
                away_score,
                home_score,
                'win' if away_score > home_score else 'loss' if away_score < home_score else 'draw',
                3 if away_score > home_score else 0 if away_score < home_score else 1,
                0  # is_home=False
            ))
        
        # Insert into TeamMatchHistory
        if history_data:
            cursor.executemany("""
                INSERT OR IGNORE INTO TeamMatchHistory 
                (team_id, match_id, date, goals_scored, goals_conceded, 
                result, points, is_home)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, history_data)
        
        # Mark all matches in batch as processed (including skipped ones)
        all_processed_ids = [m[0] for m in batch]
        if all_processed_ids:
            placeholders = ','.join(['?'] * len(all_processed_ids))
            cursor.execute(f"""
                UPDATE matches
                SET processed_match_history = 1
                WHERE match_id IN ({placeholders})
            """, all_processed_ids)
        
        conn.commit()
        processed_count = len(batch) - len(skipped_match_ids)
        print(f"Processed {processed_count} matches, skipped {len(skipped_match_ids)} matches with NULL scores")

    conn.close()

# Usage
process_matches_to_history('v2db.sqlite')