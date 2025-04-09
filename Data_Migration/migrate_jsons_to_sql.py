import os
import sqlite3
import json

def create_matches_table(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS matches
                 (match_id TEXT, 
                 start_time TEXT, 
                 competition_id TEXT, 
                 competition_name TEXT,
                 competition_season_id TEXT,
                 competition_season_name TEXT,
                 season_start_date TEXT,
                 season_end_date TEXT,
                 round_info TEXT,
                 home_team_id TEXT,
                 home_team_name TEXT,
                 away_team_id TEXT,
                 away_team_name TEXT,
                 venue_id TEXT,
                 venue_name TEXT,
                 venue_capacity INTEGER,
                 status TEXT,
                 match_status TEXT,
                 home_score INTEGER,
                 away_score INTEGER,
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
                 away_team_formation TEXT,
                 h2h_processed INTEGER DEFAULT 0,
                 elo_processed INTEGER DEFAULT 0,
                 processed_match_history INTEGER DEFAULT 0
                 )''')

#********************************************************************************************************************
#MAIN FUNCTION
#********************************************************************************************************************

def process_matches_jsons_to_sql(matches_directory, db_path):
    conn = sqlite3.connect(db_path)
    create_matches_table(conn)

    for filename in os.listdir(matches_directory):
        if filename.endswith('.json'):
            with open(os.path.join(matches_directory, filename), 'r') as file:
                data = json.load(file)
                print("Processing matches data file: ", filename)
                
                # Loop through each summary (match) in the summaries (match) list
                for summary in data['summaries']:
                    # If the match exists and has ended, skip it, because we don't need to re-process it...
                    if check_if_match_exists_and_has_ended(conn, match_id) :
                        print(f"Match {match_id} already exists and has ended, skipping")
                        continue
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
                    match = {
                        'match_id': match_id,
                        'start_time': summary.get('sport_event', {}).get('start_time'),
                        'competition_id': summary.get('sport_event', {}).get('sport_event_context', {}).get('competition', {}).get('id'),
                        'competition_name': summary.get('sport_event', {}).get('sport_event_context', {}).get('competition', {}).get('name'),
                        'competition_season_id': summary.get('sport_event', {}).get('sport_event_context', {}).get('season', {}).get('id'),
                        'competition_season_name': summary.get('sport_event', {}).get('sport_event_context', {}).get('season', {}).get('name'),
                        'season_start_date': summary.get('sport_event', {}).get('sport_event_context', {}).get('season', {}).get('start_date'),
                        'season_end_date': summary.get('sport_event', {}).get('sport_event_context', {}).get('season', {}).get('end_date'),
                        'round_info': summary.get('sport_event', {}).get('sport_event_context', {}).get('round', {}),
                        'home_team_id': next(c.get('id') for c in summary.get('sport_event', {}).get('competitors', []) if c.get('qualifier') == 'home'),
                        'home_team_name': next(c.get('name') for c in summary.get('sport_event', {}).get('competitors', []) if c.get('qualifier') == 'home'),
                        'away_team_id': next(c.get('id') for c in summary.get('sport_event', {}).get('competitors', []) if c.get('qualifier') == 'away'),
                        'away_team_name': next(c.get('name') for c in summary.get('sport_event', {}).get('competitors', []) if c.get('qualifier') == 'away'),
                        'venue_id': summary.get('sport_event', {}).get('venue', {}).get('id'),
                        'venue_name': summary.get('sport_event', {}).get('venue', {}).get('name'),
                        'venue_capacity': summary.get('sport_event', {}).get('venue', {}).get('capacity'),
                        'status': summary.get('sport_event_status', {}).get('status'),
                        'match_status': summary.get('sport_event_status', {}).get('match_status'),
                        'home_score': summary.get('sport_event_status', {}).get('home_score'),
                        'away_score': summary.get('sport_event_status', {}).get('away_score'),
                        'period_scores': summary.get('sport_event_status', {}).get('period_scores'),
                        'winner_id': summary.get('sport_event_status', {}).get('winner_id'),
                        'home_team_stats': home_team_stats,
                        'home_team_player_stats': home_team_player_stats,
                        'away_team_stats': away_team_stats,
                        'away_team_player_stats': away_team_player_stats
                    }
                    insert_or_update_match_record(conn, match)

    conn.commit()
    conn.close()

def process_lineups_jsons_to_sql(conn, lineups_directory, db_path):
    for filename in os.listdir(lineups_directory):
        if filename.endswith('.json'):
            with open(os.path.join(lineups_directory, filename), 'r') as file:
                data = json.load(file)
                print("Processing lineups data file: ", filename)


            # Loop through each summary (match) in the summaries (match) list
            for summary in data.get('lineups', []):
                match_id = summary.get('sport_event', {}).get('id')
                # If the match exists and has ended, skip it, because we don't need to re-process it...
                if check_if_match_exists_and_has_ended(conn, match_id) :
                    print(f"Match {match_id} already exists and has ended, skipping")
                    continue

                lineups = summary.get('lineups', {})
                competitors = lineups.get('competitors', [{}] * 2)
                
                home_team_lineup_info = competitors[0].get('players')
                away_team_lineup_info = competitors[1].get('players')
                
                home_team_manager_info = competitors[0].get('manager')
                away_team_manager_info = competitors[1].get('manager')
                
                home_team_formation = competitors[0].get('formation')
                away_team_formation = competitors[1].get('formation')
                
                match = {
                    'match_id': match_id,
                    'start_time': summary.get('sport_event', {}).get('start_time'),
                    'competition_id': summary.get('sport_event', {}).get('sport_event_context', {}).get('competition', {}).get('id'),
                    'competition_name': summary.get('sport_event', {}).get('sport_event_context', {}).get('competition', {}).get('name'),
                    'competition_season_id': summary.get('sport_event', {}).get('sport_event_context', {}).get('season', {}).get('id'),
                    'competition_season_name': summary.get('sport_event', {}).get('sport_event_context', {}).get('season', {}).get('name'),
                    'season_start_date': summary.get('sport_event', {}).get('sport_event_context', {}).get('season', {}).get('start_date'),
                    'season_end_date': summary.get('sport_event', {}).get('sport_event_context', {}).get('season', {}).get('end_date'),
                    'round_info': summary.get('sport_event', {}).get('sport_event_context', {}).get('round', {}),
                    'home_team_id': next(c.get('id') for c in summary.get('sport_event', {}).get('competitors', []) if c.get('qualifier') == 'home'),
                    'home_team_name': next(c.get('name') for c in summary.get('sport_event', {}).get('competitors', []) if c.get('qualifier') == 'home'),
                    'away_team_id': next(c.get('id') for c in summary.get('sport_event', {}).get('competitors', []) if c.get('qualifier') == 'away'),
                    'away_team_name': next(c.get('name') for c in summary.get('sport_event', {}).get('competitors', []) if c.get('qualifier') == 'away'),
                    'venue_id': summary.get('sport_event', {}).get('venue', {}).get('id'),
                    'venue_name': summary.get('sport_event', {}).get('venue', {}).get('name'),
                    'venue_capacity': summary.get('sport_event', {}).get('venue', {}).get('capacity'),
                    'status': summary.get('sport_event_status', {}).get('status'),
                    'match_status': summary.get('sport_event_status', {}).get('match_status'),
                    'home_score': summary.get('sport_event_status', {}).get('home_score'),
                    'away_score': summary.get('sport_event_status', {}).get('away_score'),
                    'period_scores': summary.get('sport_event_status', {}).get('period_scores'),
                    'winner_id': summary.get('sport_event_status', {}).get('winner_id'),
                    'home_team_lineup_info': home_team_lineup_info,
                    'home_team_manager_info': home_team_manager_info,
                    'home_team_formation': home_team_formation,
                    'away_team_lineup_info': away_team_lineup_info,
                    'away_team_manager_info': away_team_manager_info,
                    'away_team_formation': away_team_formation
                }

                insert_or_update_match_record(conn, match)
                    
    conn.commit()
    conn.close()



#********************************************************************************************************************
#Helper functions
#********************************************************************************************************************
    
def insert_or_update_match_record(conn, match):
    try:
        # Check if match already exists
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM matches WHERE match_id = ?', (match.get('match_id'),))
        existing_match = cursor.fetchone()

        if existing_match is None:
            # Match doesn't exist - insert new record with all available data
            columns = []
            values = []
            placeholders = []
            
            # Build dynamic INSERT query based on available data
            for key, value in match.items():
                if value is not None:
                    columns.append(key)
                    values.append(value if not isinstance(value, (dict, list)) else json.dumps(value))
                    placeholders.append('?')
            
            query = f'''INSERT INTO matches ({','.join(columns)}) 
                       VALUES ({','.join(placeholders)})'''
            conn.execute(query, values)
            
        else:
            # Match exists - update with any new data
            updates = []
            values = []
            
            # Only update fields that have new data
            for key, value in match.items():
                if value is not None:
                    updates.append(f"{key} = ?")
                    values.append(value if not isinstance(value, (dict, list)) else json.dumps(value))
            
            values.append(match.get('match_id'))  # Add match_id for WHERE clause
            
            query = f'''UPDATE matches 
                       SET {','.join(updates)}
                       WHERE match_id = ?'''
            conn.execute(query, values)

    except Exception as e:
        print(f"Error inserting/updating match: {e}")
        print(f"Problematic match data: {match}")
        raise


def initialize_db(db_path):
    conn = sqlite3.connect(db_path)
    # Drop existing table
    conn.execute('DROP TABLE IF EXISTS matches')
    conn.commit()
    conn.close()

def check_if_match_exists_and_has_ended(conn, match_id):
    cursor = conn.cursor()
    cursor.execute('SELECT match_status FROM matches WHERE match_id = ?', (match_id,))
    existing_match = cursor.fetchone()
    return existing_match is not None and existing_match[0] == 'ended'

# Example usage:
if __name__ == '__main__':
    conn = sqlite3.connect('v2db.sqlite')
    # initialize_db('v2db.sqlite')
    process_matches_jsons_to_sql('sportradar/data/matches_data', 'v2db.sqlite')
    process_lineups_jsons_to_sql(conn,'sportradar/data/lineups_data', 'v2db.sqlite')