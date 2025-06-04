from helpers.database_helpers.get_and_set_functions import get_from_matches

def process_match_info_history(conn, batch_size=10000):
    """
    Creates and populates a competition_history table using batch inserts.
    
    Args:
        db_path: Path to the SQLite database
        batch_size: Number of records to insert in each batch
    """
    competition_history_data = []
    processed_match_ids = []

    matches = get_from_matches(conn, select_str='SELECT DISTINCT', columns=['match_id', 'start_time', 'competition_season_name', 'competition_id', 'competition_name', 'competition_country', 'home_team_name', 'away_team_name'], where_clause='home_score IS NOT NULL AND away_score IS NOT NULL AND is_processed = false', order_by='start_time')

    processed_count = 0
    for match in matches:
        if processed_count % 10000 == 0:
            print(f"MATCH INFO: Processing match {processed_count}/{len(matches)}")

        match_id, start_time, competition_season_name, competition_id, competition_name, competition_country, home_team_name, away_team_name = match 
        if competition_id is not None:
            competition_history_data.append((match_id, start_time, competition_season_name, competition_id, competition_name, competition_country, home_team_name, away_team_name))
            processed_match_ids.append(match_id)
        
        processed_count += 1
    # Batch insert into competition_history table
    total_inserted = 0
    cursor = conn.cursor()
    
    for i in range(0, len(competition_history_data), batch_size):
        batch = competition_history_data[i:i+batch_size]
        try:
            cursor.executemany('''
            INSERT INTO match_info_history (match_id, start_time, competition_season_name, competition_id, competition_name, competition_country, home_team_name, away_team_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING
            ''', batch)
            
            # Count how many were actually inserted (ignoring duplicates)
            total_inserted += cursor.rowcount
            print(f"Inserted {total_inserted} rows into match_info_history")
        except Exception as e:
            print(f"Error inserting batch {i//batch_size + 1}: {str(e)}")
    
    # Commit and close
    conn.commit()
    print(f"Inserted {total_inserted} rows into match_info_history")
