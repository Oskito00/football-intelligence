import sqlite3
import json
from datetime import datetime
from pathlib import Path

def create_tables(cursor):
    """Create necessary tables in SQLite database"""
    
    # Create competitions table
    cursor.execute('''CREATE TABLE IF NOT EXISTS competitions (
        competition_id TEXT PRIMARY KEY,
        competition_name TEXT,
        first_seen_date TEXT,
        last_updated TEXT
    )''')
    
    # Create teams table
    cursor.execute('''CREATE TABLE IF NOT EXISTS teams (
        team_id TEXT PRIMARY KEY,
        team_name TEXT,
        home_venue_id TEXT,
        home_venue_name TEXT,
        home_venue_city TEXT,
        home_venue_country TEXT,
        main_competition_id TEXT,
        last_updated TEXT
    )''')
    
    # Create matches table
    cursor.execute('''CREATE TABLE IF NOT EXISTS matches (
        match_id TEXT PRIMARY KEY,
        start_time TEXT,
        start_time_confirmed BOOLEAN,
        venue_id TEXT,
        venue_name TEXT,
        venue_capacity INTEGER,
        venue_city TEXT,
        venue_country TEXT,
        competition_id TEXT,
        competition_name TEXT,
        competition_type TEXT,
        competition_phase TEXT,
        season_id TEXT,
        season_name TEXT,
        round_display TEXT,
        home_team_id TEXT,
        home_team_name TEXT,
        away_team_id TEXT,
        away_team_name TEXT,
        home_score INTEGER,
        away_score INTEGER,
        match_status TEXT,
        attendance INTEGER,
        referee_id TEXT
    )''')
    
    # Create team_stats table
    cursor.execute('''CREATE TABLE IF NOT EXISTS team_stats (
        match_id TEXT,
        team_id TEXT,
        start_time TEXT,
        team_name TEXT,
        qualifier TEXT,
        ball_possession REAL,
        cards_given INTEGER,
        chances_created INTEGER,
        clearances INTEGER,
        corner_kicks INTEGER,
        crosses_successful INTEGER,
        crosses_total INTEGER,
        crosses_unsuccessful INTEGER,
        defensive_blocks INTEGER,
        diving_saves INTEGER,
        dribbles_completed INTEGER,
        fouls INTEGER,
        free_kicks INTEGER,
        goal_kicks INTEGER,
        injuries INTEGER,
        interceptions INTEGER,
        long_passes_successful INTEGER,
        long_passes_total INTEGER,
        long_passes_unsuccessful INTEGER,
        loss_of_possession INTEGER,
        offsides INTEGER,
        passes_successful INTEGER,
        passes_total INTEGER,
        passes_unsuccessful INTEGER,
        red_cards INTEGER,
        shots_blocked INTEGER,
        shots_off_target INTEGER,
        shots_on_target INTEGER,
        shots_saved INTEGER,
        shots_total INTEGER,
        substitutions INTEGER,
        tackles_successful INTEGER,
        tackles_total INTEGER,
        tackles_unsuccessful INTEGER,
        throw_ins INTEGER,
        was_fouled INTEGER,
        yellow_cards INTEGER,
        yellow_red_cards INTEGER,
        PRIMARY KEY (match_id, team_id)
    )''')
    
    # Create player_stats table
    cursor.execute('''CREATE TABLE IF NOT EXISTS player_stats (
        match_id TEXT,
        start_time TEXT,
        player_id TEXT,
        player_name TEXT,
        team_id TEXT,
        starter BOOLEAN,
        assists INTEGER,
        chances_created INTEGER,
        clearances INTEGER,
        corner_kicks INTEGER,
        crosses_successful INTEGER,
        crosses_total INTEGER,
        defensive_blocks INTEGER,
        diving_saves INTEGER,
        dribbles_completed INTEGER,
        fouls_committed INTEGER,
        goals_by_head INTEGER,
        goals_by_penalty INTEGER,
        goals_conceded INTEGER,
        goals_scored INTEGER,
        interceptions INTEGER,
        long_passes_successful INTEGER,
        long_passes_total INTEGER,
        long_passes_unsuccessful INTEGER,
        loss_of_possession INTEGER,
        minutes_played INTEGER,
        offsides INTEGER,
        own_goals INTEGER,
        passes_successful INTEGER,
        passes_total INTEGER,
        passes_unsuccessful INTEGER,
        penalties_faced INTEGER,
        penalties_missed INTEGER,
        penalties_saved INTEGER,
        red_cards INTEGER,
        shots_blocked INTEGER,
        shots_faced_saved INTEGER,
        shots_faced_total INTEGER,
        shots_off_target INTEGER,
        shots_on_target INTEGER,
        substituted_in INTEGER,
        substituted_out INTEGER,
        tackles_successful INTEGER,
        tackles_total INTEGER,
        was_fouled INTEGER,
        yellow_cards INTEGER,
        yellow_red_cards INTEGER,
        PRIMARY KEY (match_id, player_id)
    )''')

def update_related_tables(cursor, match_data):
    """Update teams and competitions tables based on match data"""
    
    # Update competitions
    cursor.execute('''INSERT OR IGNORE INTO competitions 
        (competition_id, competition_name, first_seen_date, last_updated)
        VALUES (?, ?, datetime('now'), datetime('now'))''',
        (match_data['competition_id'], match_data['competition_name']))

    # Update teams (both home and away)
    for team_type in ['home', 'away']:
        team_id = match_data[f'{team_type}_team_id']
        team_name = match_data[f'{team_type}_team_name']
        
        if team_type == 'home':
            venue_id = match_data['venue_id']
            venue_name = match_data['venue_name']
            venue_city = match_data['venue_city']
            venue_country = match_data['venue_country']
        else:
            venue_id = None
            venue_name = None
            venue_city = None
            venue_country = None

        cursor.execute('''INSERT OR IGNORE INTO teams 
            (team_id, team_name, home_venue_id, home_venue_name, 
             home_venue_city, home_venue_country, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))''',
            (team_id, team_name, venue_id, venue_name, 
             venue_city, venue_country))

# We could keep this function if you want to maintain the main_competition_id field
def infer_main_competitions(cursor):
    """Update teams' main_competition_id based on frequency of appearances"""
    cursor.execute('''
        WITH CompetitionCounts AS (
            SELECT 
                team_id,
                competition_id,
                COUNT(*) as match_count,
                ROW_NUMBER() OVER (PARTITION BY team_id ORDER BY COUNT(*) DESC) as rn
            FROM (
                SELECT home_team_id as team_id, competition_id
                FROM matches
                UNION ALL
                SELECT away_team_id as team_id, competition_id
                FROM matches
            )
            GROUP BY team_id, competition_id
        )
        UPDATE teams
        SET main_competition_id = (
            SELECT competition_id 
            FROM CompetitionCounts 
            WHERE CompetitionCounts.team_id = teams.team_id 
            AND rn = 1
        )
    ''')

def process_match_data(db_file):
    """Process match data from all season files and insert into SQLite database"""
    
    # Connect to SQLite database
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Create tables
    create_tables(cursor)
    
    # Get all JSON files from matches_data directory
    matches_dir = Path('sportradar/data/matches_data')
    season_files = matches_dir.glob('*.json')
    
    for season_file in season_files:
        print(f"\nProcessing {season_file.name}")
        
        # Load JSON data
        with open(season_file, 'r') as f:
            data = json.load(f)
        
        # Process each match summary
        for summary in data.get("summaries", []):
            match = summary.get("sport_event", {})
            status = summary.get("sport_event_status", {})
            
            # Extract match details
            match_id = match.get("id")
            start_time = match.get("start_time")
            match_status = status.get("match_status")
            
            # Check if match already exists in all relevant tables
            cursor.execute('''
                SELECT 
                    EXISTS(SELECT 1 FROM matches WHERE match_id = ?) AS in_matches,
                    EXISTS(SELECT 1 FROM team_stats WHERE match_id = ?) AS in_team_stats,
                    EXISTS(SELECT 1 FROM player_stats WHERE match_id = ?) AS in_player_stats
            ''', (match_id, match_id, match_id))
            
            exists_result = cursor.fetchone()
            if all(exists_result):  # If match exists in all tables
                print(f"Skipping existing match {match_id}")
                continue
            
            # Extract team info
            competitors = match.get("competitors", [])
            home_team = next((team for team in competitors if team.get("qualifier") == "home"), {})
            away_team = next((team for team in competitors if team.get("qualifier") == "away"), {})
            venue = match.get("venue", {})
            context = match.get("sport_event_context", {})
            
            # For future matches, some fields will be None
            home_score = status.get("home_score") if match_status != "not_started" else None
            away_score = status.get("away_score") if match_status != "not_started" else None
            attendance = match.get("sport_event_conditions", {}).get("attendance", {}).get("count")
            
            # Prepare match data for related tables update
            match_data = {
                'competition_id': context.get("competition", {}).get("id"),
                'competition_name': context.get("competition", {}).get("name"),
                'home_team_id': home_team.get("id"),
                'home_team_name': home_team.get("name"),
                'away_team_id': away_team.get("id"),
                'away_team_name': away_team.get("name"),
                'venue_id': venue.get("id"),
                'venue_name': venue.get("name"),
                'venue_city': venue.get("city_name"),
                'venue_country': venue.get("country_name")
            }
            
            # Update related tables
            update_related_tables(cursor, match_data)
            
            # Extract referee info
            referee = next((ref for ref in match.get("sport_event_conditions", {}).get("referees", []) 
                          if ref.get("type") == "main_referee"), {})
            referee_id = referee.get("id")

            # Insert match data
            round_info = context.get("round", {})
            round_display = round_info.get("name") if round_info.get("name") else str(round_info.get("number", ""))

            cursor.execute('''INSERT OR REPLACE INTO matches (
                match_id, start_time, start_time_confirmed, venue_id, venue_name, venue_capacity,
                venue_city, venue_country, competition_id, competition_name, competition_type, competition_phase, season_id, season_name,
                round_display, home_team_id, home_team_name, away_team_id, away_team_name,
                home_score, away_score, match_status, attendance, referee_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
                match_id, start_time, match.get("start_time_confirmed"),
                venue.get("id"), venue.get("name"), venue.get("capacity"),
                venue.get("city_name"), venue.get("country_name"),
                context.get("competition", {}).get("id"),
                context.get("competition", {}).get("name"),
                context.get("stage", {}).get("type"),
                context.get("stage", {}).get("phase"),
                context.get("season", {}).get("id"),
                context.get("season", {}).get("name"),
                round_display,
                home_team.get("id"), home_team.get("name"),
                away_team.get("id"), away_team.get("name"),
                home_score, away_score, match_status, attendance, referee_id
            ))
            
            # Only process statistics for completed matches
            if match_status in ["ended", "closed"]:
                stats = summary.get("statistics", {})
                
                # Insert team stats from totals
                for team in stats.get("totals", {}).get("competitors", []):
                    team_id = team.get("id")
                    team_name = team.get("name")
                    start_time = match.get("start_time")
                    qualifier = team.get("qualifier")
                    team_stats = team.get("statistics", {})
                    
                    cursor.execute('''INSERT OR REPLACE INTO team_stats (
                        match_id, team_id,start_time, team_name, qualifier,
                        ball_possession, cards_given, chances_created, clearances, corner_kicks,
                        crosses_successful, crosses_total, crosses_unsuccessful, defensive_blocks,
                        diving_saves, dribbles_completed, fouls, free_kicks, goal_kicks, injuries,
                        interceptions, long_passes_successful, long_passes_total, long_passes_unsuccessful,
                        loss_of_possession, offsides, passes_successful, passes_total, passes_unsuccessful,
                        red_cards, shots_blocked, shots_off_target, shots_on_target, shots_saved,
                        shots_total, substitutions, tackles_successful, tackles_total, tackles_unsuccessful,
                        throw_ins, was_fouled, yellow_cards, yellow_red_cards
                    ) VALUES (?, ?,?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                             ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (match_id, team_id, start_time, team_name, qualifier, *[team_stats.get(k) for k in [
                            "ball_possession", "cards_given", "chances_created", "clearances",
                            "corner_kicks", "crosses_successful", "crosses_total", "crosses_unsuccessful",
                            "defensive_blocks", "diving_saves", "dribbles_completed", "fouls",
                            "free_kicks", "goal_kicks", "injuries", "interceptions",
                            "long_passes_successful", "long_passes_total", "long_passes_unsuccessful",
                            "loss_of_possession", "offsides", "passes_successful", "passes_total",
                            "passes_unsuccessful", "red_cards", "shots_blocked", "shots_off_target",
                            "shots_on_target", "shots_saved", "shots_total", "substitutions",
                            "tackles_successful", "tackles_total", "tackles_unsuccessful",
                            "throw_ins", "was_fouled", "yellow_cards", "yellow_red_cards"
                        ]]))
                    
                    # Insert player stats
                    for player in team.get("players", []):
                        player_id = player.get("id")
                        player_name = player.get("name")
                        starter = player.get("starter", False)
                        start_time = match.get("start_time")
                        player_stats = player.get("statistics", {})
                        
                        cursor.execute('''INSERT OR REPLACE INTO player_stats (
                            match_id, start_time, player_id, player_name, team_id, starter,
                            assists, chances_created, clearances, corner_kicks, crosses_successful,
                            crosses_total, defensive_blocks, diving_saves, dribbles_completed,
                            fouls_committed, goals_by_head, goals_by_penalty, goals_conceded,
                            goals_scored, interceptions, long_passes_successful, long_passes_total,
                            long_passes_unsuccessful, loss_of_possession, minutes_played, offsides,
                            own_goals, passes_successful, passes_total, passes_unsuccessful,
                            penalties_faced, penalties_missed, penalties_saved, red_cards,
                            shots_blocked, shots_faced_saved, shots_faced_total, shots_off_target,
                            shots_on_target, substituted_in, substituted_out, tackles_successful,
                            tackles_total, was_fouled, yellow_cards, yellow_red_cards
                        ) VALUES (?, ?,?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                            (match_id, start_time, player_id, player_name, team_id, starter, *[player_stats.get(k) for k in [
                                "assists", "chances_created", "clearances", "corner_kicks",
                                "crosses_successful", "crosses_total", "defensive_blocks",
                                "diving_saves", "dribbles_completed", "fouls_committed",
                                "goals_by_head", "goals_by_penalty", "goals_conceded",
                                "goals_scored", "interceptions", "long_passes_successful",
                                "long_passes_total", "long_passes_unsuccessful",
                                "loss_of_possession", "minutes_played", "offsides", "own_goals",
                                "passes_successful", "passes_total", "passes_unsuccessful",
                                "penalties_faced", "penalties_missed", "penalties_saved",
                                "red_cards", "shots_blocked", "shots_faced_saved",
                                "shots_faced_total", "shots_off_target", "shots_on_target",
                                "substituted_in", "substituted_out", "tackles_successful",
                                "tackles_total", "was_fouled", "yellow_cards", "yellow_red_cards"
                            ]]))
    
    # Update main competitions after processing all matches
    infer_main_competitions(cursor)
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    print(f"Successfully processed all match data and saved to {db_file}")

if __name__ == "__main__":
    process_match_data('football_data.db')