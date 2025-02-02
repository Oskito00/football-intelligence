import sqlite3
import json
from pathlib import Path

#TODO: If putting the sql queries into the helper functions doesn't work uncomment the code at the bottom of this file and use it instead
def create_lineup_table(cursor):
    """Create the team_lineups table in existing database"""
    cursor.execute('''CREATE TABLE IF NOT EXISTS team_lineups (
        match_id TEXT PRIMARY KEY,
        match_status TEXT,
        start_time TEXT,
        home_team_id TEXT,
        home_team_name TEXT,
        away_team_id TEXT,
        away_team_name TEXT,
        home_formation TEXT,
        away_formation TEXT,
        home_players JSON,  -- Store full player list as JSON
        away_players JSON   -- Store full player list as JSON
    )''')

def process_lineup_data(db_file='football_data.db'):
    """Process lineup data from all season files and insert into existing SQLite database"""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Create lineup table
    create_lineup_table(cursor)
    
    # Get all JSON lineup files from the lineups_data directory
    # This data includes all lineups for all matches in a season
    lineups_dir = Path('sportradar/data/lineups_data')
    lineup_files = list(lineups_dir.glob('*_lineups.json'))
    
    print(f"\nFound {len(lineup_files)} lineup files/seasons")
    
    processed_count = 0
    skipped_count = 0
    
    # For every season/file, process all lineups
    for lineup_file in lineup_files:
        print(f"\nProcessing {lineup_file.name}")
        
        # Load JSON data
        with open(lineup_file, 'r') as f:
            data = json.load(f)
        
        # For every match in the season, process the lineup
        for match_data in data.get("lineups", []):
            # Get generic match details
            sport_event = match_data.get("sport_event", {})
            match_status = match_data.get("sport_event_status", {}).get("match_status", None)
            print(f"match_status: {match_status}")
            match_id = sport_event.get("id")
            print(f"match_id: {match_id}")
            
            # Check if match already exists in the team_lineups table
            cursor.execute('SELECT match_status FROM team_lineups WHERE match_id = ?', (match_id,))
            result = cursor.fetchone()
            
            if result:
                current_match_status = result[0]
                # If it exists, check if the match_status is the same
                if current_match_status == match_status:
                    print(f"Skipping existing match {match_id} because it has already ended")
                    skipped_count += 1
                    continue
                else:
                    # Update the match_status if it's different
                    cursor.execute('UPDATE team_lineups SET match_status = ? WHERE match_id = ?', (match_status, match_id))
                    print(f"Updated match {match_id} status from {current_match_status} to {match_status}.")
            else:
                print(f"Processing match {match_id} haven't seen it before ")
            
            # Get the start time of the match    
            start_time = sport_event.get("start_time")
            
            # Get lineup data
            lineup_data = match_data.get("lineups", {}).get("competitors", [])
            if not lineup_data:
                print("No lineup data found for match {match_id} or match has not started...")

            if lineup_data:
                # Find home and away teams and get their data
                home_team = next((team for team in lineup_data if team.get("qualifier") == "home"), {})
                away_team = next((team for team in lineup_data if team.get("qualifier") == "away"), {})
            else:
                print(f"No lineup data found for match {match_id}")
                home_team = {}
                away_team = {}
            
            
            # Insert lineup data
            insert_lineup_data(
                cursor=cursor,
                conn=conn,
                match_id=match_id,
                match_status=match_status,
                start_time=start_time,
                home_team=home_team,
                away_team=away_team
            )
            
            processed_count += 1
    
    print(f"\nProcessing complete:")
    print(f"Total lineups processed: {processed_count}")
    print(f"Lineups skipped (already existed): {skipped_count}")
    
    # Just get the lineup counts
    cursor.execute("SELECT COUNT(*) FROM team_lineups")
    total_lineups = cursor.fetchone()[0]
    
    print(f"\nDatabase stats:")
    print(f"Total matches with lineups in DB: {total_lineups}")
    
    conn.close()
    print(f"\nSuccessfully processed all lineup data and saved to {db_file}")

#********************************************************************************
#HELPER FUNCTIONS
#********************************************************************************

def process_players(team):
    players = []
    for player in team.get("players", []):
        players.append({
            'id': player.get('id'),
            'name': player.get('name'),
            'type': player.get('type'),  # goalkeeper, defender, midfielder, forward
            'position': player.get('position'),  # specific position if they played
            'shirt_number': player.get('jersey_number'),
            'starter': player.get('starter', False),
            'played': player.get('played', False),
        })
    return players  # No need to sort since we're including everyone

def insert_lineup_data(cursor, conn, match_id: str, match_status: str, start_time: str, 
                      home_team: dict, away_team: dict) -> None:
    """Insert lineup data into the database and commit the transaction.
    
    Args:
        cursor: SQLite cursor object
        conn: SQLite connection object
        match_id: ID of the match
        start_time: Match start time
        home_team: Dictionary containing home team data
        away_team: Dictionary containing away team data
    """
    cursor.execute('''
        INSERT OR REPLACE INTO team_lineups (
            match_id,
            match_status,
            start_time,
            home_team_id,
            home_team_name,
            away_team_id,
            away_team_name,
            home_formation,
            away_formation,
            home_players,
            away_players
        ) VALUES (?, ?, ?, ?,?, ?, ?, ?, ?, ?, ?)
    ''', (
        match_id,
        match_status,
        start_time,
        home_team.get("id"),
        home_team.get("name"),
        away_team.get("id"),
        away_team.get("name"),
        home_team.get("formation", {}).get("type"),
        away_team.get("formation", {}).get("type"),
        json.dumps(process_players(home_team)),
        json.dumps(process_players(away_team))
    ))
    
    conn.commit()

if __name__ == "__main__":
    # delete every entry in the team_lineups table
    conn = sqlite3.connect('football_data.db')
    cursor = conn.cursor()
    cursor.execute('DROP TABLE IF EXISTS team_lineups')
    conn.commit()
    process_lineup_data()


# USE THIS CODE IF THE ABOVE CODE DOESN'T WORK
# def process_lineup_data(db_file='football_data.db'):
#     """Process lineup data from all season files and insert into existing SQLite database"""
#     conn = sqlite3.connect(db_file)
#     cursor = conn.cursor()
    
#     # Create lineup table
#     cursor.execute('''CREATE TABLE IF NOT EXISTS team_lineups (
#         match_id TEXT PRIMARY KEY,
#         start_time TEXT,
#         home_team_id TEXT,
#         home_team_name TEXT,
#         away_team_id TEXT,
#         away_team_name TEXT,
#         home_formation TEXT,
#         away_formation TEXT,
#         home_players JSON,  -- Store full player list as JSON
#         away_players JSON   -- Store full player list as JSON
#     )''')
    
#     # Get all JSON lineup files
#     lineups_dir = Path('sportradar/data/lineups_data')
#     lineup_files = list(lineups_dir.glob('*_lineups.json'))
    
#     print(f"\nFound {len(lineup_files)} lineup files/seasons")
    
#     processed_count = 0
#     skipped_count = 0
    
#     for lineup_file in lineup_files:
#         print(f"\nProcessing {lineup_file.name}")
        
#         with open(lineup_file, 'r') as f:
#             data = json.load(f)
        
#         for match_data in data.get("lineups", []):
#             # Get match details
#             sport_event = match_data.get("sport_event", {})
#             match_id = sport_event.get("id")
            
#             # Check for existing match
#             cursor.execute('SELECT 1 FROM team_lineups WHERE match_id = ?', (match_id,))
#             if cursor.fetchone():
#                 print(f"Skipping existing match {match_id}")
#                 skipped_count += 1
#                 continue

#             start_time = sport_event.get("start_time")
            
#             # Get lineup data
#             lineup_data = match_data.get("lineups", {}).get("competitors", [])
#             if not lineup_data:
#                 continue
                
#             # Find home and away teams
#             home_team = next((team for team in lineup_data if team.get("qualifier") == "home"), {})
#             away_team = next((team for team in lineup_data if team.get("qualifier") == "away"), {})
            
#             if not home_team or not away_team:
#                 continue
            
#             # Process players for both teams
#             home_players = []
#             for player in home_team.get("players", []):
#                 home_players.append({
#                     'id': player.get('id'),
#                     'name': player.get('name'),
#                     'type': player.get('type'),
#                     'position': player.get('position'),
#                     'shirt_number': player.get('jersey_number'),
#                     'starter': player.get('starter', False),
#                     'played': player.get('played', False),
#                 })
            
#             away_players = []
#             for player in away_team.get("players", []):
#                 away_players.append({
#                     'id': player.get('id'),
#                     'name': player.get('name'),
#                     'type': player.get('type'),
#                     'position': player.get('position'),
#                     'shirt_number': player.get('jersey_number'),
#                     'starter': player.get('starter', False),
#                     'played': player.get('played', False),
#                 })
            
#             # Insert lineup data directly
#             cursor.execute('''
#                 INSERT OR REPLACE INTO team_lineups (
#                     match_id,
#                     start_time,
#                     home_team_id,
#                     home_team_name,
#                     away_team_id,
#                     away_team_name,
#                     home_formation,
#                     away_formation,
#                     home_players,
#                     away_players
#                 ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#             ''', (
#                 match_id,
#                 start_time,
#                 home_team.get("id"),
#                 home_team.get("name"),
#                 away_team.get("id"),
#                 away_team.get("name"),
#                 home_team.get("formation", {}).get("type"),
#                 away_team.get("formation", {}).get("type"),
#                 json.dumps(home_players),
#                 json.dumps(away_players)
#             ))
            
#             conn.commit()
#             processed_count += 1
    
#     print(f"\nProcessing complete:")
#     print(f"Total lineups processed: {processed_count}")
#     print(f"Lineups skipped (already existed): {skipped_count}")
    
#     cursor.execute("SELECT COUNT(*) FROM team_lineups")
#     total_lineups = cursor.fetchone()[0]
    
#     print(f"\nDatabase stats:")
#     print(f"Total matches with lineups in DB: {total_lineups}")
    
#     conn.close()
#     print(f"\nSuccessfully processed all lineup data and saved to {db_file}")

# if __name__ == "__main__":
#     process_lineup_data()