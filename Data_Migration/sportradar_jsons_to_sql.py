import os
import sqlite3
import json

#TODO: Need to make this more efficient, batch processing etc. as data grows this will become a bottleneck.
# But the matches data is all correct.

def create_matches_table(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS matches

                 (match_id TEXT, 
                 start_time TEXT, 
                 competition_id TEXT, 
                 competition_name TEXT,
                 competition_country TEXT,
                 competition_season_name TEXT,
                 competition_season_id TEXT,
                 season_start_date TEXT,
                 season_end_date TEXT,
                 round_info TEXT,
                 home_team_id TEXT,
                 home_team_name TEXT,
                 home_team_domestic_league_id TEXT,
                 home_team_domestic_country TEXT,
                 away_team_domestic_league_id TEXT,
                 away_team_domestic_country TEXT,
                 away_team_id TEXT,
                 away_team_name TEXT,
                 match_status TEXT,
                 home_score INTEGER,
                 away_score INTEGER,
                 result TEXT,
                 is_processed INTEGER DEFAULT 0,

                 venue_id TEXT,
                 venue_name TEXT,
                 venue_capacity INTEGER,
                 status TEXT,
                 period_scores JSON, 
                 winner_id TEXT,
                 home_team_stats JSON,
                 home_team_player_stats JSON,
                 away_team_stats JSON,
                 away_team_player_stats JSON,
                 home_team_lineup_info JSON,
                 home_team_manager_info JSON,
                 home_team_formation TEXT,
                 away_team_lineup_info JSON,
                 away_team_manager_info JSON,
                 away_team_formation TEXT
                 
                 )''')

#********************************************************************************************************************
#MAIN FUNCTION
#********************************************************************************************************************

def process_matches_jsons_to_sql(conn, matches_directory, db_path):
    create_matches_table(conn)

    for filename in os.listdir(matches_directory):
        if filename.endswith('.json'):
            with open(os.path.join(matches_directory, filename), 'r') as file:
                data = json.load(file)
                print("Processing matches data file: ", filename)

                matches_list = []
                
                # Loop through each summary (match) in the summaries (match) list
                for summary in data['summaries']:
                    # If the match exists and has ended and all data is present, skip it, because we don't need to re-process it...
                    match_id = summary.get('sport_event', {}).get('id')
                    match_status = summary.get('sport_event_status', {}).get('match_status')
                    has_stats = summary.get('statistics') is not None                    
                    if (match_status != 'not_started' or match_status != 'postponed') and has_stats:
                        home_team_stats = summary.get('statistics').get('totals').get('competitors')[0].get('statistics')
                        home_team_player_stats = summary.get('statistics').get('totals').get('competitors')[0].get('players')
                        away_team_stats = summary.get('statistics').get('totals').get('competitors')[1].get('statistics')
                        away_team_player_stats = summary.get('statistics').get('totals').get('competitors')[1].get('players')
                    else:
                        home_team_stats = None
                        home_team_player_stats = None
                        away_team_stats = None
                        away_team_player_stats = None
                        
                    home_score = summary.get('sport_event_status', {}).get('home_score')
                    away_score = summary.get('sport_event_status', {}).get('away_score')
                    match = {
                        'match_id': match_id,
                        'start_time': summary.get('sport_event', {}).get('start_time'),
                        'competition_id': summary.get('sport_event', {}).get('sport_event_context', {}).get('competition', {}).get('id'),
                        'competition_name': summary.get('sport_event', {}).get('sport_event_context', {}).get('competition', {}).get('name'),
                        'competition_country': summary.get('sport_event', {}).get('sport_event_context', {}).get('category', {}).get('name'),
                        'competition_season_id': summary.get('sport_event', {}).get('sport_event_context', {}).get('season', {}).get('id'),
                        'competition_season_name': summary.get('sport_event', {}).get('sport_event_context', {}).get('season', {}).get('name'),
                        'season_start_date': summary.get('sport_event', {}).get('sport_event_context', {}).get('season', {}).get('start_date'),
                        'season_end_date': summary.get('sport_event', {}).get('sport_event_context', {}).get('season', {}).get('end_date'),
                        'round_info': summary.get('sport_event', {}).get('sport_event_context', {}).get('round', {}),
                        'home_team_id': next(c.get('id') for c in summary.get('sport_event', {}).get('competitors', []) if c.get('qualifier') == 'home'),
                        'home_team_name': next(c.get('name') for c in summary.get('sport_event', {}).get('competitors', []) if c.get('qualifier') == 'home'),
                        'home_team_domestic_league_id': None,
                        'home_team_domestic_country': None,
                        'away_team_domestic_league_id': None,
                        'away_team_domestic_country': None,
                        'away_team_id': next(c.get('id') for c in summary.get('sport_event', {}).get('competitors', []) if c.get('qualifier') == 'away'),
                        'away_team_name': next(c.get('name') for c in summary.get('sport_event', {}).get('competitors', []) if c.get('qualifier') == 'away'),
                        'match_status': summary.get('sport_event_status', {}).get('match_status'),
                        'home_score': summary.get('sport_event_status', {}).get('home_score'),
                        'away_score': summary.get('sport_event_status', {}).get('away_score'),


                        # Extra sport radar data
                        'venue_id': summary.get('sport_event', {}).get('venue', {}).get('id'),
                        'venue_name': summary.get('sport_event', {}).get('venue', {}).get('name'),
                        'venue_capacity': summary.get('sport_event', {}).get('venue', {}).get('capacity'),
                        'status': summary.get('sport_event_status', {}).get('status'),
                        'period_scores': summary.get('sport_event_status', {}).get('period_scores'),
                        'winner_id': summary.get('sport_event_status', {}).get('winner_id'),
                        'home_team_stats': home_team_stats,
                        'home_team_player_stats': home_team_player_stats,
                        'away_team_stats': away_team_stats,
                        'away_team_player_stats': away_team_player_stats,
                    }
                    matches_list.append(match)
                
                processed_match_ids = get_processed_matches(conn, matches_list)
                unprocessed_matches = [m for m in matches_list if m['match_id'] not in processed_match_ids]

                batch_upsert_matches(conn, unprocessed_matches)
                    
    conn.commit()

def process_lineups_jsons_to_sql(conn, lineups_directory, db_path):

    for filename in os.listdir(lineups_directory):
        if filename.endswith('.json'):
            with open(os.path.join(lineups_directory, filename), 'r') as file:
                data = json.load(file)
                print("Processing lineups data file: ", filename)

            matches_list = []

            for summary in data.get('lineups', []):
                match_id = summary.get('sport_event', {}).get('id')

                lineups = summary.get('lineups', {})
                competitors = lineups.get('competitors', [])
                
                # Safe defaults in case data is missing
                home_team_lineup_info = None
                away_team_lineup_info = None
                home_team_manager_info = None
                away_team_manager_info = None
                home_team_formation = None
                away_team_formation = None

                # Process data only if we have competitors
                if len(competitors) > 0:
                    home_team_lineup_info = competitors[0].get('players')
                    home_team_manager_info = competitors[0].get('manager')
                    home_team_formation = competitors[0].get('formation')

                if len(competitors) > 1:
                    away_team_lineup_info = competitors[1].get('players')
                    away_team_manager_info = competitors[1].get('manager')
                    away_team_formation = competitors[1].get('formation')

                match_status = summary.get('sport_event_status', {}).get('match_status')

                if match_status == 'ended':
                    is_processed = 1
                else:
                    is_processed = 0
                
                match = {
                    'match_id': match_id,
                    'start_time': summary.get('sport_event', {}).get('start_time'),
                    'competition_id': summary.get('sport_event', {}).get('sport_event_context', {}).get('competition', {}).get('id'),
                    'competition_name': summary.get('sport_event', {}).get('sport_event_context', {}).get('competition', {}).get('name'),
                    'competition_country': summary.get('sport_event', {}).get('sport_event_context', {}).get('category', {}).get('name'),
                    'competition_season_id': summary.get('sport_event', {}).get('sport_event_context', {}).get('season', {}).get('id'),
                    'competition_season_name': summary.get('sport_event', {}).get('sport_event_context', {}).get('season', {}).get('name'),
                    'season_start_date': summary.get('sport_event', {}).get('sport_event_context', {}).get('season', {}).get('start_date'),
                    'season_end_date': summary.get('sport_event', {}).get('sport_event_context', {}).get('season', {}).get('end_date'),
                    'round_info': summary.get('sport_event', {}).get('sport_event_context', {}).get('round', {}),
                    'home_team_id': next(c.get('id') for c in summary.get('sport_event', {}).get('competitors', []) if c.get('qualifier') == 'home'),
                    'home_team_name': next(c.get('name') for c in summary.get('sport_event', {}).get('competitors', []) if c.get('qualifier') == 'home'),
                    'home_team_domestic_league_id': None,
                    'home_team_domestic_country': None,
                    'away_team_domestic_league_id': None,
                    'away_team_domestic_country': None,
                    'away_team_id': next(c.get('id') for c in summary.get('sport_event', {}).get('competitors', []) if c.get('qualifier') == 'away'),
                    'away_team_name': next(c.get('name') for c in summary.get('sport_event', {}).get('competitors', []) if c.get('qualifier') == 'away'),
                    'match_status': summary.get('sport_event_status', {}).get('match_status'),
                    'is_processed': is_processed,

                    'venue_id': summary.get('sport_event', {}).get('venue', {}).get('id'),
                    'venue_name': summary.get('sport_event', {}).get('venue', {}).get('name'),
                    'venue_capacity': summary.get('sport_event', {}).get('venue', {}).get('capacity'),
                    'status': summary.get('sport_event_status', {}).get('status'),
                    'period_scores': summary.get('sport_event_status', {}).get('period_scores'),
                    'winner_id': summary.get('sport_event_status', {}).get('winner_id'),
                    'home_team_lineup_info': home_team_lineup_info,
                    'home_team_manager_info': home_team_manager_info,
                    'home_team_formation': home_team_formation,
                    'away_team_lineup_info': away_team_lineup_info,
                    'away_team_manager_info': away_team_manager_info,
                    'away_team_formation': away_team_formation
                }
                matches_list.append(match)
            
            processed_match_ids = get_processed_matches(conn, matches_list)
            unprocessed_matches = [m for m in matches_list if m['match_id'] not in processed_match_ids]

            batch_upsert_matches(conn, unprocessed_matches)
            


    conn.commit()
    conn.close()

#********************************************************************************************************************
#Helper functions
#********************************************************************************************************************

def get_processed_matches(conn, incoming_matches):
    """Return list of match IDs that already exist and are marked as processed"""
    print("Len of incoming matches: ", len(incoming_matches))
    if not incoming_matches:
        return []

    incoming_match_ids = [str(match['match_id']) for match in incoming_matches]
    placeholders = ','.join(['?'] * len(incoming_match_ids))

    query = f"""
        SELECT match_id 
        FROM matches 
        WHERE match_id IN ({placeholders})
          AND is_processed = 1
    """

    try:
        cursor = conn.cursor()
        cursor.execute(query, incoming_match_ids)
        return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error checking processed matches: {str(e)}")
        return []

def batch_upsert_matches(conn, matches):
    if not matches:
        return

    # Prepare data
    insert_data = []
    update_data = []
    all_match_ids = [m['match_id'] for m in matches]

    # Check existing matches in bulk
    existing_match_ids = get_existing_match_ids(conn, all_match_ids)

    # Separate inserts and updates
    for match in matches:
        if match['match_id'] in existing_match_ids:
            update_data.append(match)
        else:
            insert_data.append(match)

    # Batch insert
    if insert_data:
        batch_insert_matches(conn, insert_data)
    
    # Batch update
    if update_data:
        batch_update_matches(conn, update_data)

def get_existing_match_ids(conn, match_ids):
    if not match_ids:
        return set()
    
    placeholders = ','.join(['?'] * len(match_ids))
    query = f"SELECT match_id FROM matches WHERE match_id IN ({placeholders})"
    
    try:
        cursor = conn.cursor()
        cursor.execute(query, match_ids)
        return {row[0] for row in cursor.fetchall()}
    except Exception as e:
        print(f"Error in get_existing_match_ids: {str(e)}")
        return set()

def batch_insert_matches(conn, matches):
    if not matches:
        return

    try:
        columns = list(matches[0].keys())
        insert_query = f"""
            INSERT INTO matches ({','.join(columns)})
            VALUES ({','.join(['?'] * len(columns))})
        """
        
        values = [
            tuple(json.dumps(v) if isinstance(v, (dict, list)) else v 
                 for v in match.values())
            for match in matches
        ]
        
        cursor = conn.cursor()
        cursor.executemany(insert_query, values)
        conn.commit()
        
    except Exception as e:
        print(f"Batch insert failed: {str(e)}")
        conn.rollback()
        raise

def batch_update_matches(conn, matches):
    if not matches:
        return

    # Get columns to update (exclude match_id)
    columns = [col for col in matches[0].keys() if col != 'match_id']
    
    # Prepare update query
    set_clause = ','.join([f"{col} = ?" for col in columns])
    update_query = f"""
        UPDATE matches
        SET {set_clause}
        WHERE match_id = ?
    """
    
    # Prepare data tuples
    values = []
    for match in matches:
        row = [json.dumps(match[col]) if isinstance(match[col], (dict, list)) else match[col] 
               for col in columns]
        row.append(match['match_id'])
        values.append(tuple(row))
    
    # Execute batch update
    try:
        cursor = conn.cursor()
        cursor.executemany(update_query, values)
        conn.commit()
    except Exception as e:
        print(f"Batch update failed: {str(e)}")
        conn.rollback()

def initialize_db(db_path):
    conn = sqlite3.connect(db_path)
    # Drop existing table
    conn.execute('DROP TABLE IF EXISTS matches')
    conn.commit()
    conn.close()

# Example usage:
if __name__ == '__main__':
    conn = sqlite3.connect('v2db.sqlite')
    # initialize_db('v2db.sqlite')
    process_matches_jsons_to_sql(conn, 'Data/sportradar/raw/matches_data', 'v2db.sqlite')
    process_lineups_jsons_to_sql(conn,'Data/sportradar/raw/lineups_data', 'v2db.sqlite')