import sqlite3
import json
from pathlib import Path

def create_lineup_table(cursor):
    """Create the team_lineups table in existing database"""
    cursor.execute('''CREATE TABLE IF NOT EXISTS team_lineups (
        match_id TEXT PRIMARY KEY,
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
    
    # Get all JSON files from lineups_data directory
    lineups_dir = Path('sportradar/data/lineups_data')
    lineup_files = list(lineups_dir.glob('*_lineups.json'))
    
    print(f"\nFound {len(lineup_files)} lineup files")
    
    processed_count = 0
    skipped_count = 0
    
    for lineup_file in lineup_files:
        print(f"\nProcessing {lineup_file.name}")
        
        # Load JSON data
        with open(lineup_file, 'r') as f:
            data = json.load(f)
        
        # Process each lineup
        for match_data in data.get("lineups", []):
            # Get match details
            sport_event = match_data.get("sport_event", {})
            match_id = sport_event.get("id")
            
            # Check if match already exists
            cursor.execute('SELECT 1 FROM team_lineups WHERE match_id = ?', (match_id,))
            if cursor.fetchone():
                print(f"Skipping existing match {match_id}")
                skipped_count += 1
                continue
                
            start_time = sport_event.get("start_time")
            
            # Get lineup data
            lineup_data = match_data.get("lineups", {}).get("competitors", [])
            if not lineup_data:
                continue
                
            # Find home and away teams
            home_team = next((team for team in lineup_data if team.get("qualifier") == "home"), {})
            away_team = next((team for team in lineup_data if team.get("qualifier") == "away"), {})
            
            if not home_team or not away_team:
                continue
            
            # Process players with formation positions
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
            
            # Insert lineup data
            cursor.execute('''
                INSERT OR REPLACE INTO team_lineups (
                    match_id,
                    start_time,
                    home_team_id,
                    home_team_name,
                    away_team_id,
                    away_team_name,
                    home_formation,
                    away_formation,
                    home_players,
                    away_players
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                match_id,
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
            
            processed_count += 1
            conn.commit()
    
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

if __name__ == "__main__":
    process_lineup_data()