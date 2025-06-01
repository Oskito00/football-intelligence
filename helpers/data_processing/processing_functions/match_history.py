from datetime import time


def process_matches_to_history(conn,matches, batch_size=1000):
    """Saves matches into an easier to query table.
    Mostly used for form analysis, easier to query "last N matches for team" X


    
    """
    cursor = conn.cursor()
    
    team_data_batch = []
    processed_count = 0
    
    for match in matches:
        if processed_count % 1000 == 0:
            print(f"MATCH HISTORY: Processing match {processed_count}/{len(matches)}")
            
        match_id, start_time, competition_season_name, competition_id, competition_name, competition_country, home_team_id, home_team_name, away_team_id, away_team_name, \
        home_score, away_score, home_main_comp_id, home_main_comp_country, \
        away_main_comp_id, away_main_comp_country = match

        is_same_nation = (home_main_comp_country == away_main_comp_country)
        is_same_league = home_main_comp_id == away_main_comp_id

        is_domestic_league_match = is_same_nation and is_same_league
        is_domestic_cup_match = is_same_nation and not is_same_league
        # NOTE: For different datasets the competitions might be named differently. Please change to your naming convention
        continental_comps = ['Champions League', 'Europa League', 'Conference League']
        is_continental_cup_match = competition_name in continental_comps

        # Home team entry
        team_data_batch.append((
            home_team_id,
            match_id,
            start_time,
            competition_season_name,
            competition_id,
            competition_name,
            competition_country,
            home_score,
            away_score,
            'win' if home_score > away_score else 'loss' if home_score < away_score else 'draw',
            1,  # is_home=True,
            is_domestic_league_match,
            is_domestic_cup_match,
            is_continental_cup_match
        ))
            
        # Away team entry
        team_data_batch.append((
            away_team_id,
            match_id,
            start_time,
            competition_season_name,
            competition_id,
            competition_name,
            competition_country,
            away_score,
            home_score,
            'win' if away_score > home_score else 'loss' if away_score < home_score else 'draw',
            0,  # is_home=False
            is_domestic_league_match,
            is_domestic_cup_match,
            is_continental_cup_match
        ))
        
        processed_count += 1
        
        # Insert in batches
        if len(team_data_batch) >= batch_size:
            cursor.executemany("""
                INSERT OR IGNORE INTO TeamMatchHistory 
                (team_id, match_id, start_time, competition_season_name, competition_id, competition_name, competition_country, goals_scored, goals_conceded, 
                result, is_home, is_intraleague_match, is_domestic_cup_match, is_continental_cup_match)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, team_data_batch)
            conn.commit()
            team_data_batch = []  # Clear the batch
    
    # Insert any remaining records
    if team_data_batch:
        cursor.executemany("""
            INSERT OR IGNORE INTO TeamMatchHistory 
            (team_id, match_id, start_time, competition_season_name, competition_id, competition_name, competition_country, goals_scored, goals_conceded, 
            result, is_home, is_intraleague_match, is_domestic_cup_match, is_continental_cup_match)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? )
        """, team_data_batch)
        conn.commit()
    
    print(f"Processed {processed_count} matches ({processed_count*2} team history records)")
    conn.close()
    print("WAITING 5 SECONDS BEFORE STARTING NEXT PROCESSING FUNCTION")
    time.sleep(5)