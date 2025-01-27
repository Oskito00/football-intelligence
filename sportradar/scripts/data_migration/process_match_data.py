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
    """Function to process the match data from the JSON files and insert into SQLite database"""
    conn = None
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Create tables
        create_tables(cursor)
        
        # Get all JSON files from matches_data3
        matches_dir = Path('sportradar/data/matches_data')
        season_files = matches_dir.glob('*.json')
        
        for season_file in season_files:
            try:
                print(f"\nProcessing {season_file.name}")
                
                with open(season_file, 'r') as f:
                    data = json.load(f)
                
                for summary in data.get("summaries", []):
                    try:
                        match = summary.get("sport_event", {})
                        status = summary.get("sport_event_status", {})
                        match_id = match.get("id")
                        
                        # Check if match already exists in all relevant tables, if so skip so that we don't have duplicates
                        if check_match_exists(cursor, match_id):
                            print(f"Skipping existing match {match_id}")
                            continue
                        
                        # Extract some more match details
                        competitors = match.get("competitors", [])
                        home_team = next((team for team in competitors if team.get("qualifier") == "home"), {})
                        away_team = next((team for team in competitors if team.get("qualifier") == "away"), {})
                        venue = match.get("venue", {})
                        context = match.get("sport_event_context", {})
                        #TODO: Extract weather data
                        # For future matches, some fields will be None
                        home_score = status.get("home_score") if match.get("status") != "not_started" else None
                        away_score = status.get("away_score") if match.get("status") != "not_started" else None
                        attendance = match.get("sport_event_conditions", {}).get("attendance", {}).get("count")
                        referee = next((ref for ref in match.get("sport_event_conditions", {}).get("referees", []) 
                                      if ref.get("type") == "main_referee"), {})
                        referee_id = referee.get("id")
                        round_info = context.get("round", {})
                        round_display = round_info.get("name") if round_info.get("name") else str(round_info.get("number", ""))

                        insert_into_match_data(
                            cursor=cursor,
                            match_id=match_id,
                            match=match,
                            context=context,
                            home_team=home_team,
                            away_team=away_team,
                            venue=venue,
                            start_time=match.get("start_time"),
                            round_display=round_display,
                            home_score=home_score,
                            away_score=away_score,
                            match_status=match.get("status"),
                            attendance=attendance,
                            referee_id=referee_id
                        )
                        
                        # If the match has ended, process deeper statistics
                        if match.get("status") in ["ended", "closed"]:
                            stats = summary.get("statistics", {})
                            
                            # For each team in the match add their stats to the team_stats table
                            for team in stats.get("totals", {}).get("competitors", []):
                                team_id = team.get("id")
                                team_name = team.get("name")
                                qualifier = team.get("qualifier")
                                team_stats = team.get("statistics", {})
                                
                                insert_into_team_stats(
                                    cursor=cursor,
                                    match_id=match_id,
                                    team_id=team_id,
                                    start_time=match.get("start_time"),
                                    team_name=team_name,
                                    qualifier=qualifier,
                                    team_stats=team_stats
                                )
                                
                                # Get player positions from lineups
                                player_positions = get_player_positions(cursor, match_id)

                                # For each player in the team insert their stats into the player_stats table
                                for player in team.get("players", []):
                                    position = next((pos for pid, pos in player_positions if pid == player.get("id")), 'unknown')
                                    
                                    insert_into_player_stats(
                                        cursor=cursor,
                                        match_id=match_id,
                                        player=player,
                                        team_id=team_id,
                                        start_time=match.get("start_time"),
                                        position=position
                                    )
                            
                    except Exception as e:
                        print(f"Error processing match: {e}")
                        continue
                        
            except Exception as e:
                print(f"Error processing file {season_file.name}: {e}")
                continue
        
        # Get final stats
        cursor.execute("SELECT COUNT(*) FROM matches WHERE match_status = 'ended'")
        match_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM team_lineups")
        lineup_count = cursor.fetchone()[0]
        
        print(f"\nDatabase stats:")
        print(f"Total ended matches: {match_count}")
        print(f"Total matches with lineups: {lineup_count}")
        print(f"Matches missing lineups: {match_count - lineup_count}")
        
        conn.commit()
        print(f"Successfully processed all match data and saved to {db_file}")
        
    except Exception as e:
        print(f"Fatal error in process_match_data: {e}")
        if conn:
            conn.rollback()
        raise
        
    finally:
        if conn:
            conn.close()

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

def insert_into_match_data(cursor, match_id: str, match: dict, context: dict, 
                     home_team: dict, away_team: dict, venue: dict, 
                     start_time: str, round_display: str, 
                     home_score: int, away_score: int, 
                     match_status: str, attendance: int, referee_id: str) -> None:
    """Insert or update match data in the matches table.
    
    Args:
        cursor: SQLite cursor object
        match_id: Unique identifier for the match
        match: Dictionary containing match details
        context: Dictionary containing competition context
        home_team: Dictionary containing home team details
        away_team: Dictionary containing away team details
        venue: Dictionary containing venue details
        start_time: Match start time
        round_display: Display name for the round
        home_score: Home team score
        away_score: Away team score
        match_status: Current status of the match
        attendance: Match attendance
        referee_id: ID of the main referee
    """
    cursor.execute('''INSERT OR REPLACE INTO matches (
        match_id, start_time, start_time_confirmed, venue_id, venue_name, venue_capacity,
        venue_city, venue_country, competition_id, competition_name, competition_type, 
        competition_phase, season_id, season_name, round_display, home_team_id, 
        home_team_name, away_team_id, away_team_name, home_score, away_score, 
        match_status, attendance, referee_id
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

def insert_into_team_stats(cursor, match_id: str, team_id: str, start_time: str, 
                     team_name: str, qualifier: str, team_stats: dict) -> None:
    """Insert or update team statistics in the team_stats table.
    
    Args:
        cursor: SQLite cursor object
        match_id: Unique identifier for the match
        team_id: ID of the team
        start_time: Match start time
        team_name: Name of the team
        qualifier: Team qualifier (home/away)
        team_stats: Dictionary containing team statistics
    """
    stats_columns = [
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
    ]
    
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
    ) VALUES (?, ?, ?, ?, ?, ''' + ', '.join(['?' * len(stats_columns)]) + ')',
        (match_id, team_id, start_time, team_name, qualifier, 
         *[team_stats.get(k) for k in stats_columns]))

def get_player_positions(cursor, match_id: str) -> list:
    """Get all player positions for a given match from both teams.
    
    Args:
        cursor: SQLite cursor object
        match_id: ID of the match to get positions for
        
    Returns:
        list: List of tuples containing (player_id, position)
    """
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
    
    return cursor.fetchall()

def insert_into_player_stats(cursor, match_id: str, player: dict, team_id: str, 
                       start_time: str, position: str) -> None:
    """Insert or update player statistics in the player_stats table.
    
    Args:
        cursor: SQLite cursor object
        match_id: Unique identifier for the match
        player: Dictionary containing player details and statistics
        team_id: ID of the player's team
        start_time: Match start time
        position: Player's position on the field
    """
    stats_columns = [
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
    ]
    
    cursor.execute('''INSERT OR REPLACE INTO player_stats (
        match_id, start_time, player_id, player_name, team_id, starter,
        position, ''' + ', '.join(stats_columns) + '''
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ''' + ', '.join(['?' * len(stats_columns)]) + ')',
        (match_id, start_time, player.get("id"), player.get("name"), 
         team_id, player.get("starter", False), position,
         *[player.get("statistics", {}).get(k) for k in stats_columns]))

if __name__ == "__main__":
    process_match_data('football_data.db')