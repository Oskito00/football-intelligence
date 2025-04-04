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
                 home_team_lineup JSON,
                 away_team_lineup JSON
                 )''')
    
#********************************************************************************************************************
#MAIN FUNCTION
#********************************************************************************************************************

def process_matches_jsons_to_sql(matches_jsons, db_path):
    conn = sqlite3.connect(db_path)
    create_matches_table(conn)

    matches_directory = 'sportradar/data/matches_data'
    for match in matches_jsons:
        insert_match(conn, match)
    conn.commit()
    conn.close()




#********************************************************************************************************************
#Helper functions
#********************************************************************************************************************
    
def insert_match(conn, match):
    try:
        # Convert complex objects to JSON strings
        period_scores_json = json.dumps(match.get('period_scores', {}))
        home_team_stats_json = json.dumps(match.get('home_team_stats', {}))
        away_team_stats_json = json.dumps(match.get('away_team_stats', {}))
        home_team_player_stats_json = json.dumps(match.get('home_team_player_stats', {}))
        away_team_player_stats_json = json.dumps(match.get('away_team_player_stats', {}))

        conn.execute('''INSERT INTO matches 
                    (match_id, start_time, competition_id, competition_name, 
                    competition_season_id, competition_season_name, season_start_date, 
                    season_end_date, round_info, home_team_id, home_team_name, 
                    away_team_id, away_team_name, venue_id, venue_name, 
                    venue_capacity, status, match_status, home_score, away_score, 
                    period_scores, winner_id, home_team_stats, home_team_player_stats, 
                    away_team_stats, away_team_player_stats)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                            ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (match.get('match_id'),
                     match.get('start_time'),
                     match.get('competition_id'),
                     match.get('competition_name'),
                     match.get('competition_season_id'),
                     match.get('competition_season_name'),
                     match.get('season_start_date'),
                     match.get('season_end_date'),
                     match.get('round_info'),
                     match.get('home_team_id'),
                     match.get('home_team_name'),
                     match.get('away_team_id'),
                     match.get('away_team_name'),
                     match.get('venue_id'),
                     match.get('venue_name'),
                     match.get('venue_capacity'),
                     match.get('status'),
                     match.get('match_status'),
                     match.get('home_score'),
                     match.get('away_score'),
                     period_scores_json,
                     match.get('winner_id'),
                     home_team_stats_json,
                     home_team_player_stats_json,
                     away_team_stats_json,
                     away_team_player_stats_json))
    except Exception as e:
        print(f"Error inserting match: {e}")
        raise