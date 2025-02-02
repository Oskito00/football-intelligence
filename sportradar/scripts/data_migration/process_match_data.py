import sqlite3
import json
from datetime import datetime
from pathlib import Path

def create_tables(cursor):
    """Creates necessary tables in SQLite database
    These will be used to store match data
    
    matches: contains generic match data
    team_stats: contains team stats for each match
    player_stats: contains player stats for each match
    """
    
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
        position TEXT,
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


def process_match_data(db_file='football_data.db'):
    """
    Process match data from JSON files and insert into SQLite database.
    Handles matches, team stats, and player stats in a single transaction.
    
    Args:
        db_file (str): Path to SQLite database file. Defaults to 'football_data.db'
    """
    # Initialize database connection
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Ensure all necessary tables exist
    create_tables(cursor)
    
    # Get all JSON files from the matches data directory
    matches_dir = Path('sportradar/data/matches_data')
    season_files = matches_dir.glob('*.json')
    
    # Process each season file
    for season_file in season_files:
        print(f"\nProcessing {season_file.name}")
        
        # Load the JSON data for this season
        with open(season_file, 'r') as f:
            data = json.load(f)
        
        # Process each match in the season
        for summary in data.get("summaries", []):
            # Extract basic match information
            sport_event = summary.get("sport_event", {})
            sport_event_status = summary.get("sport_event_status", {})
            match_id = sport_event.get("id")
            match_status = sport_event_status.get("match_status")
            
            # Skip if we've already processed this match in all tables
            if check_match_exists(cursor, match_id):
                print(f"Skipping existing match {match_id}")
                continue
            
            # Extract detailed match information
            competitors = sport_event.get("competitors", [])
            # Find home and away teams using list comprehension with next()
            home_team = next((team for team in competitors if team.get("qualifier") == "home"), {})
            away_team = next((team for team in competitors if team.get("qualifier") == "away"), {})

            venue = sport_event.get("venue", {})

            # Get competition data
            context = sport_event.get("sport_event_context", {})
            
            # Get scores for home and away teams for the completed match
            home_score = sport_event_status.get("home_score") if match_status != "not_started" else None
            away_score = sport_event_status.get("away_score") if match_status != "not_started" else None
            
            # Extract additional match details
            attendance = sport_event.get("sport_event_conditions", {}).get("attendance", {}).get("count")
            # Find main referee from list of officials
            referee = next((ref for ref in sport_event.get("sport_event_conditions", {}).get("referees", []) 
                          if ref.get("type") == "main_referee"), {})
            referee_id = referee.get("id")
            #TODO: Get weather from sport_event_conditions
            
            # Handle round information
            round_info = context.get("round", {})
            round_display = round_info.get("name") if round_info.get("name") else str(round_info.get("number", ""))

            # Insert basic match data
            cursor.execute('''INSERT OR REPLACE INTO matches (
                match_id, start_time, start_time_confirmed, venue_id, venue_name, venue_capacity,
                venue_city, venue_country, competition_id, competition_name, competition_type,
                competition_phase, season_id, season_name, round_display, home_team_id,
                home_team_name, away_team_id, away_team_name, home_score, away_score,
                match_status, attendance, referee_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (match_id, sport_event.get("start_time"), sport_event.get("start_time_confirmed"),
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
                 home_score, away_score, match_status,
                 attendance, referee_id
            ))

            # Commit the match data to the matches database
            conn.commit()
            
            # Only process detailed statistics for completed matches
            if match_status in ["ended", "closed", "ap", "aet"]:
                stats = summary.get("statistics", {})
                
                # Process team statistics
                for team in stats.get("totals", {}).get("competitors", []):
                    team_id = team.get("id")
                    team_stats = team.get("statistics", {})
                    
                    # Insert team statistics
                    cursor.execute('''INSERT OR REPLACE INTO team_stats (
                        match_id, team_id, start_time, team_name, qualifier,
                        ball_possession, cards_given, chances_created, clearances, corner_kicks,
                        crosses_successful, crosses_total, crosses_unsuccessful, defensive_blocks,
                        diving_saves, dribbles_completed, fouls, free_kicks, goal_kicks, injuries,
                        interceptions, long_passes_successful, long_passes_total, long_passes_unsuccessful,
                        loss_of_possession, offsides, passes_successful, passes_total, passes_unsuccessful,
                        red_cards, shots_blocked, shots_off_target, shots_on_target, shots_saved,
                        shots_total, substitutions, tackles_successful, tackles_total, tackles_unsuccessful,
                        throw_ins, was_fouled, yellow_cards, yellow_red_cards
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                             ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (match_id, team_id, sport_event.get("start_time"), team.get("name"),
                         team.get("qualifier"), *[team_stats.get(k) for k in [
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
                    
                    # Commit the team stats to the team_stats database
                    conn.commit()
                    
                    # Get player positions from lineup data
                    cursor.execute("""
                        SELECT 
                            json_extract(value, '$.id') as player_id,
                            json_extract(value, '$.type') as position
                        FROM team_lineups l,
                             json_each(l.home_players)
                        WHERE l.match_id = ?
                        UNION ALL
                        SELECT 
                            json_extract(value, '$.id') as player_id,
                            json_extract(value, '$.type') as position
                        FROM team_lineups l,
                             json_each(l.away_players)
                        WHERE l.match_id = ?
                    """, (match_id, match_id))
                    
                    # Create dictionary of player positions
                    player_positions = {row[0]: row[1] for row in cursor.fetchall()}

                    # Process individual player statistics
                    for player in team.get("players", []):
                        player_stats = player.get("statistics", {})
                        position = player_positions.get(player.get("id"), 'unknown')
                        
                        # Insert player statistics
                        cursor.execute('''INSERT OR REPLACE INTO player_stats (
                            match_id, start_time, player_id, player_name, team_id, starter,
                            position,
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
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                            (match_id, sport_event.get("start_time"), player.get("id"), player.get("name"),
                             team.get("id"), player.get("starter", False),
                             position,
                             *[player_stats.get(k) for k in [
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
                            ]])
                        )

                        # Commit the player stats to the player_stats database
                        conn.commit()
    
    # Get final statistics for reporting
    cursor.execute("SELECT COUNT(*) FROM matches WHERE match_status = 'ended'")
    match_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM team_lineups")
    lineup_count = cursor.fetchone()[0]

    # Report statistics
    print(f"\nDatabase stats:")
    print(f"Total ended matches: {match_count}")
    print(f"Total matches with lineups: {lineup_count}")
    print(f"Matches missing lineups: {match_count - lineup_count}")
   
    # Commit all changes and close connection
    conn.commit()
    conn.close()
    print(f"Successfully processed all match data and saved to {db_file}")

#********************************************************************************
#HELPER FUNCTIONS
#********************************************************************************

def check_match_exists(cursor, match_id):
    """Check if match data exists in all relevant tables.
    
    Args:
        cursor: SQLite cursor object
        match_id: ID of the match to check
        
    Returns:
        bool: True if match exists in all tables, False otherwise
    """

    # Check if match exists in all relevant tables
    cursor.execute('''
        SELECT 
            EXISTS(SELECT 1 FROM matches WHERE match_id = ?) AS in_matches,
            EXISTS(SELECT 1 FROM team_stats WHERE match_id = ?) AS in_team_stats,
            EXISTS(SELECT 1 FROM player_stats WHERE match_id = ?) AS in_player_stats
    ''', (match_id, match_id, match_id))
    
    return all(cursor.fetchone())

if __name__ == "__main__":
    process_match_data('football_data.db')