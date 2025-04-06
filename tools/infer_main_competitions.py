import sqlite3
from collections import defaultdict
from Tools.Database_helpers.get_and_set_functions import get_main_league_and_nation_data
from Tools.Database_helpers.create_tables import create_team_main_competition_table

def infer_main_competitions(conn):
    """Infer the main competition and country for each team"""
    main_league_and_nation_data = get_main_league_and_nation_data(conn)
    
    # Create dictionaries to track competition counts for each team
    team_competitions = defaultdict(lambda: defaultdict(int))
    team_competition_names = defaultdict(lambda: defaultdict(int))
    team_countries = defaultdict(lambda: defaultdict(int))
    team_names = {}
    
    # Process match data
    for row in main_league_and_nation_data:
        home_team_id, home_team_name, away_team_id, away_team_name, competition_id, competition_name, competition_country = row
        
        # Skip if competition_id or competition_country is NULL
        if not competition_id or not competition_country:
            continue
            
        # Track home team
        team_names[home_team_id] = home_team_name
        team_competitions[home_team_id][competition_id] += 1
        team_competition_names[home_team_id][competition_name] += 1
        team_countries[home_team_id][competition_country] += 1
        
        # Track away team
        team_names[away_team_id] = away_team_name
        team_competitions[away_team_id][competition_id] += 1
        team_competition_names[away_team_id][competition_name] += 1
        team_countries[away_team_id][competition_country] += 1
    
    # Create or ensure the table exists
    create_team_main_competition_table(conn)
    cursor = conn.cursor()
    
    # Find and store the main competition for each team
    for team_id, competitions in team_competitions.items():
        if not competitions:  # Skip if no competitions
            continue
            
        # Find the most common competition
        main_competition_id = max(competitions.items(), key=lambda x: x[1])[0]
        match_count = competitions[main_competition_id]
        
        # Find the most common country
        main_country = max(team_countries[team_id].items(), key=lambda x: x[1])[0]
        main_competition_name = max(team_competition_names[team_id].items(), key=lambda x: x[1])[0]
        # Insert or update the record
        cursor.execute('''
        INSERT OR REPLACE INTO team_main_competition 
        (team_id, team_name, main_competition_id, main_competition_name, main_competition_country, match_count)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (team_id, team_names.get(team_id, "Unknown"), main_competition_id, main_competition_name, main_country, match_count))
    
    conn.commit()
    print(f"Updated main competition data for {len(team_competitions)} teams")

if __name__ == "__main__":
    conn = sqlite3.connect('v2db.sqlite')
    infer_main_competitions(conn)
    conn.close()