import json
import sqlite3

# Load JSON data
with open('data/api_football/raw/basic_match_data.json') as f:
    matches = json.load(f)

# Connect to SQLite DB
conn = sqlite3.connect('api_football.db')
cursor = conn.cursor()

# Create table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS matches (
        match_id INTEGER PRIMARY KEY,
        start_time DATETIME,
        clean_date DATE,
        competition_id INTEGER,
        competition_name TEXT,
        competition_country TEXT,
        competition_season_name TEXT,
        competition_season_id TEXT,
        season_start_date DATE,
        season_end_date DATE,
        round_info TEXT,
        home_team_id INTEGER,
        home_team_name TEXT,
        home_team_domestic_league_id INTEGER,
        away_team_domestic_league_id INTEGER,
        home_team_domestic_country TEXT,
        away_team_domestic_country TEXT,
        away_team_id INTEGER,
        away_team_name TEXT,
        match_status TEXT,
        home_score INTEGER,
        away_score INTEGER,
        result TEXT,
        is_processed INTEGER,
        home_team_formation VARCHAR(10),
        away_team_formation VARCHAR(10),
        home_team_lineup JSONB,
        away_team_lineup JSONB,
        attempted_formation_scrape INTEGER DEFAULT 0
    )
''')

# Insert data
insert_query = '''
INSERT INTO matches (
    match_id, start_time, clean_date, competition_id,
    competition_name, competition_country, competition_season_name,
    competition_season_id, season_start_date, season_end_date,
    round_info, home_team_id, home_team_name,
    home_team_domestic_league_id, away_team_domestic_league_id,
    home_team_domestic_country, away_team_domestic_country,
    away_team_id, away_team_name, match_status,
    home_score, away_score, result, is_processed
) VALUES (?,?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
'''

for match in matches:
    cursor.execute(insert_query, (
        match['match_id'],
        match['start_time'],
        match['clean_date'],
        match['competition_id'],
        match['competition_name'],
        match['competition_country'],
        match['competition_season_name'],
        match['competition_season_id'],
        match['season_start_date'],
        match['season_end_date'],
        match['round_info'],
        match['home_team_id'],
        match['home_team_name'],
        match['home_team_domestic_league_id'],
        match['away_team_domestic_league_id'],
        match['home_team_domestic_country'],
        match['away_team_domestic_country'],
        match['away_team_id'],
        match['away_team_name'],
        match['match_status'],
        match['home_score'],
        match['away_score'],
        match['result'],
        match['is_processed']
    ))

# Commit and close
conn.commit()
conn.close()
