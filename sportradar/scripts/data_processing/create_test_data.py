import sqlite3
import os
from datetime import datetime, timedelta
from numpy import log
import pandas as pd
import traceback
import json
import pytz  # Ensure you have pytz installed

import requests

from player_stats import get_key_players_count, initialize_player_database, process_match_stats
from team_processing import (
    calculate_match_importance, 
    calculate_form_stats, 
    initialize_database, 
    getH2h_stats
)

from dotenv import load_dotenv
load_dotenv()

#********************************************************************************
#MAIN FUNCTIONS
#********************************************************************************

def create_test_data(db_path, output_dir):
    """Create test dataset from upcoming matches"""
    try:
        conn = sqlite3.connect(db_path)
        os.makedirs(output_dir, exist_ok=True)
        
        # Create necessary tables
        create_h2h_table(conn)
        
        print("Getting upcoming matches...")
        upcoming_matches_df = pd.read_sql_query(get_upcoming_matches_query(), conn)
        total_matches = len(upcoming_matches_df)
        print(upcoming_matches_df)
        
        # Initialize three datasets
        advanced_data = []  # For matches with all features including h2h
        basic_data = []    # For matches with basic stats and h2h
        no_h2h_data = []   # For matches without h2h stats
        
        # Debugging counters
        skipped_not_next_match = 0
        skipped_no_h2h = 0
        skipped_no_squad_strength = 0
        skipped_other_errors = 0
        
        for idx, match in upcoming_matches_df.iterrows():
            try:
                # Check if next match
                home_next = is_next_unplayed_match(conn, match['home_team_id'], match['start_time'])
                away_next = is_next_unplayed_match(conn, match['away_team_id'], match['start_time'])
                
                if not (home_next and away_next):
                    skipped_not_next_match += 1
                    continue

                # Check if match started more than 90 minutes ago
                if match_has_started(match['start_time']):
                    print("Skipping match because it started more than 90 minutes ago")
                    continue
                
                # Calculate form
                average_home_stats, average_away_stats = calculate_form_stats(conn, match)
                competition_id = match['competition_id']
                match_importance = calculate_match_importance(conn, match)
                home_elo_rating, away_elo_rating = get_current_elo_ratings(conn, match)                
                # Get H2H stats from database
                h2h_stats = getH2h_stats(conn, match['home_team_id'], match['away_team_id'], match['start_time'])
                
                # Get key players for both teams
                home_key_count, home_key_players = get_key_players_count(conn, match['home_team_id'], match['start_time'])
                away_key_count, away_key_players = get_key_players_count(conn, match['away_team_id'], match['start_time'])

                # Get future lineups (From API call if the match is within 45 minute and the match has advanced stats, to reduce API calls for basic matches)
                #TODO: Make sure this helper works
                home_lineup, away_lineup = get_future_lineups(match, average_home_stats, average_away_stats, conn)
                
                # Compare the lineups with the key players to find who's missing
                home_missing_players = [
                    player for player in home_key_players 
                    if not any(lp['player_id'] == player['player_id'] for lp in home_lineup)
                ]
                
                away_missing_players = [
                    player for player in away_key_players 
                    if not any(lp['player_id'] == player['player_id'] for lp in away_lineup)
                ]
                
                # Calculate squad strengths with missing players information
                home_team_overall_strength = calculate_squad_strength(home_key_players, home_missing_players)
                away_team_overall_strength = calculate_squad_strength(away_key_players, away_missing_players)

                # Cheks to see if the teams have advanced stats
                has_advanced_home = average_home_stats.get('has_advanced_stats') == 1
                has_advanced_away = average_away_stats.get('has_advanced_stats') == 1

                 # Check to see if the teams have h2h stats
                has_h2h = (h2h_stats and match['home_team_id'] in h2h_stats 
                           and match['away_team_id'] in h2h_stats)
                
                # Create basic row with just the basic stats
                basic_row = {
                    'fixture_id': match['fixture_id'],
                    'start_time': match['start_time'],
                    'home_team': match['home_team'],
                    'away_team': match['away_team'],
                    'competition_id': competition_id,
                    'match_importance': match_importance,
                    'average_home_goals_scored': average_home_stats['average_goals_scored'],
                    'average_home_goals_conceded': average_home_stats['average_goals_conceded'],
                    'average_home_win_rate': average_home_stats['average_win_rate'],
                    'average_home_draw_rate': average_home_stats['average_draw_rate'],
                    'average_home_clean_sheets': average_home_stats['average_clean_sheets'],
                    'home_fatigue': average_home_stats.get('fatigue'),
                    'home_momentum': average_home_stats.get('momentum'),
                    'average_away_goals_scored': average_away_stats['average_goals_scored'],
                    'average_away_goals_conceded': average_away_stats['average_goals_conceded'],
                    'average_away_win_rate': average_away_stats['average_win_rate'],
                    'average_away_draw_rate': average_away_stats['average_draw_rate'],
                    'average_away_clean_sheets': average_away_stats['average_clean_sheets'],
                    'away_fatigue': average_away_stats.get('fatigue'),
                    'away_momentum': average_away_stats.get('momentum')
                }
                
                #If we have elo rating for the team (which we should, add them)
                if home_elo_rating is not None and away_elo_rating is not None:
                    basic_row['home_elo_rating'] = home_elo_rating
                    basic_row['away_elo_rating'] = away_elo_rating

                # If the match doesn't have advanced stats, squad strength, or h2h stats, add it to the basic dataset
                if not has_advanced_home or not has_advanced_away or not home_team_overall_strength or not away_team_overall_strength or not has_h2h:
                    basic_data.append(basic_row)
                    print(f"Added to basic dataset (This matches advanced stats were: {has_advanced_home} and {has_advanced_away}, this match has h2h stats: {has_h2h}, this match has squad strength: {home_team_overall_strength} and {away_team_overall_strength})")
                
                if has_h2h:
                    # Add h2h stats to the row
                    h2h_row = basic_row.copy()
                    h2h_row.update({
                        'h2h_avg_draw_rate': h2h_stats[match['home_team_id']]['avg_draw_rate'],
                        'home_h2h_avg_goals': h2h_stats[match['home_team_id']]['avg_goals'],
                        'home_h2h_avg_clean_sheets': h2h_stats[match['home_team_id']]['avg_clean_sheets'],
                        'home_h2h_avg_points': h2h_stats[match['home_team_id']]['avg_points'],
                        'away_h2h_avg_goals': h2h_stats[match['away_team_id']]['avg_goals'],
                        'away_h2h_avg_clean_sheets': h2h_stats[match['away_team_id']]['avg_clean_sheets'],
                        'away_h2h_avg_points': h2h_stats[match['away_team_id']]['avg_points']
                    })
                    
                    # Add to appropriate dataset based on advanced stats
                    if has_advanced_home and has_advanced_away and home_team_overall_strength and away_team_overall_strength:
                        advanced_row = h2h_row.copy()
                        advanced_row.update({
                            'home_pass_effectiveness': round(average_home_stats['pass_effectiveness'], 2),
                            'home_shot_accuracy': round(average_home_stats['shot_accuracy'], 2),
                            'home_conversion_rate': round(average_home_stats['conversion_rate'], 2),
                            'home_defensive_success': round(average_home_stats['defensive_success'], 2),
                            'away_pass_effectiveness': round(average_away_stats['pass_effectiveness'], 2),
                            'away_shot_accuracy': round(average_away_stats['shot_accuracy'], 2),
                            'away_conversion_rate': round(average_away_stats['conversion_rate'], 2),
                            'away_defensive_success': round(average_away_stats['defensive_success'], 2),
                            'home_team_gk_strength': home_team_overall_strength['goalkeeper_strength'],
                            'home_team_defence_strength': home_team_overall_strength['defence_strength'],
                            'home_team_midfield_strength': home_team_overall_strength['midfield_strength'],
                            'home_team_attack_strength': home_team_overall_strength['attack_strength'],
                            'away_team_gk_strength': away_team_overall_strength['goalkeeper_strength'],
                            'away_team_defence_strength': away_team_overall_strength['defence_strength'],
                            'away_team_midfield_strength': away_team_overall_strength['midfield_strength'],
                            'away_team_attack_strength': away_team_overall_strength['attack_strength'],
                            'home_team_overall_strength': home_team_overall_strength['overall_strength'],
                            'away_team_overall_strength': away_team_overall_strength['overall_strength']
                        })
                        advanced_data.append(advanced_row)
                        # log("→ Added to advanced dataset (with H2H)")
                else:
                    # No h2h stats available - add to no_h2h dataset or basic dataset
                    if has_advanced_home and has_advanced_away and home_team_overall_strength and away_team_overall_strength:
                        no_h2h_row = basic_row.copy()
                        no_h2h_row.update({
                            'home_pass_effectiveness': round(average_home_stats['pass_effectiveness'], 2),
                            'home_shot_accuracy': round(average_home_stats['shot_accuracy'], 2),
                            'home_conversion_rate': round(average_home_stats['conversion_rate'], 2),
                            'home_defensive_success': round(average_home_stats['defensive_success'], 2),
                            'away_pass_effectiveness': round(average_away_stats['pass_effectiveness'], 2),
                            'away_shot_accuracy': round(average_away_stats['shot_accuracy'], 2),
                            'away_conversion_rate': round(average_away_stats['conversion_rate'], 2),
                            'away_defensive_success': round(average_away_stats['defensive_success'], 2),
                            'home_team_gk_strength': home_team_overall_strength['goalkeeper_strength'],
                            'home_team_defence_strength': home_team_overall_strength['defence_strength'],
                            'home_team_midfield_strength': home_team_overall_strength['midfield_strength'],
                            'home_team_attack_strength': home_team_overall_strength['attack_strength'],
                            'away_team_gk_strength': away_team_overall_strength['goalkeeper_strength'],
                            'away_team_defence_strength': away_team_overall_strength['defence_strength'],
                            'away_team_midfield_strength': away_team_overall_strength['midfield_strength'],
                            'away_team_attack_strength': away_team_overall_strength['attack_strength'],
                            'home_team_overall_strength': home_team_overall_strength['overall_strength'],
                            'away_team_overall_strength': away_team_overall_strength['overall_strength']
                        })
                        #TODO: I don't think it is appending to the no_h2h_data list
                        no_h2h_data.append(no_h2h_row)

            except Exception as e:
                print(f"Error processing match: {str(e)}")
                skipped_other_errors += 1
                continue

        # Print summary statistics
        summary = f"""
=== Processing Summary ===
Total matches found: {total_matches}
Skipped - not next match: {skipped_not_next_match}
Skipped - no H2H history: {skipped_no_h2h}
Skipped - missing squad strength: {skipped_no_squad_strength}
Skipped - other errors: {skipped_other_errors}
Successfully processed - basic: {len(basic_data)}
Successfully processed - advanced: {len(advanced_data)}
Successfully processed - no H2H: {len(no_h2h_data)}
"""
        # log(summary)
        
        # Save datasets
        basic_df = None
        advanced_df = None
        no_h2h_df = None

        if len(basic_data) > 0:
            basic_df = pd.DataFrame(basic_data)
            basic_output = os.path.join(output_dir, 'test_data_basic.csv')
            basic_df.to_csv(basic_output, index=False)
            print(f"Length of basic data: {len(basic_df)}")

        if len(advanced_data) > 0:
            advanced_df = pd.DataFrame(advanced_data)
            advanced_output = os.path.join(output_dir, 'test_data_advanced.csv')
            advanced_df.to_csv(advanced_output, index=False)
            print(f"Length of advanced data: {len(advanced_df)}")

        if len(no_h2h_data) > 0:
            no_h2h_df = pd.DataFrame(no_h2h_data)
            no_h2h_output = os.path.join(output_dir, 'test_data_no_h2h.csv')
            no_h2h_df.to_csv(no_h2h_output, index=False)
            print(f"Length of no H2H data: {len(no_h2h_df)}")

        # Just return the DataFrames directly
        return advanced_df, no_h2h_df, basic_df
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()


#********************************************************************************
#HELPER FUNCTIONS
#********************************************************************************

def create_h2h_table(conn):
    """Create h2h_matches table if it doesn't exist"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS h2h_matches (
            match_id TEXT PRIMARY KEY,
            home_team_id TEXT,
            away_team_id TEXT,
            home_score INTEGER,
            away_score INTEGER,
            start_time TEXT,
            match_status TEXT,
            UNIQUE(match_id)
        )
    """)
    conn.commit()

def get_upcoming_matches_query():
    """Get matches within next 10 days that haven't been played yet"""
    return """
    SELECT DISTINCT 
        m.match_id as fixture_id,
        m.start_time,
        m.competition_name,
        m.competition_id,
        m.competition_type,
        m.competition_phase,
        m.round_display,
        m.season_id,
        m.home_team_id,
        m.away_team_id,
        m.home_team_name as home_team,
        m.away_team_name as away_team,
        m.home_score as home_goals,
        m.away_score as away_goals,
        m.referee_id,
        m.match_status
    FROM matches m
    WHERE (m.match_status IS NULL OR m.match_status = '' OR m.match_status != 'ended')
    AND m.start_time >= datetime('now')
    AND m.start_time <= datetime('now', '+3 days')
    ORDER BY m.start_time
    """

def is_next_unplayed_match(conn, team_id, match_start_time):
    """Check if this is the next unplayed match for the team"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT match_status
        FROM matches
        WHERE (home_team_id = ? OR away_team_id = ?)
        AND datetime(start_time) < datetime(?)
        AND datetime(start_time) >= datetime(?, '-90 days')
        AND match_status = 'not_started'
        ORDER BY start_time DESC
    """, (team_id, team_id, match_start_time, match_start_time))
    
    return len(cursor.fetchall()) == 0

def get_match_lineups(match_id):
    """
    Get lineups for an upcoming match from the Sportradar API
    Args:
        match_id: The match/fixture ID
    Returns:
        tuple: (home_players, away_players) where each is a list of player dictionaries
    """
    try:
        # Get API key from environment variable
        api_key = os.getenv('SPORTRADAR_API_KEY')
        if not api_key:
            print("Error: SPORTRADAR_API_KEY environment variable not set")
            return [], []

        # Make API request with key
        api_url = f"https://api.sportradar.com/soccer/trial/v4/en/sport_events/{match_id}/lineups.json?api_key={api_key}"
        print(f"Making API request to: {api_url}")
        
        response = requests.get(api_url)
        if response.status_code != 200:
            print(f"API request failed with status code: {response.status_code}")
            print(f"Response text: {response.text}")
            return [], []
            
        data = response.json()
        
        home_players = []
        away_players = []
        
        for competitor in data.get('lineups', {}).get('competitors', []):
            players_list = []
            for player in competitor.get('players', []):
                players_list.append({
                    'player_id': player['id'],
                    'player_name': player['name'],
                    'position': player['type'],
                    'jersey_number': player.get('jersey_number'),
                    'starter': player.get('starter', False)  # Keep track of who's starting
                })
            
            # Determine if this is home or away team based on qualifier
            if competitor.get('qualifier') == 'home':
                home_players = players_list
            else:
                away_players = players_list
        
        print(f"Found {len(home_players)} home starters and {len(away_players)} away starters")
        
        return home_players, away_players
        
    except Exception as e:
        print(f"Error getting match lineups: {str(e)}")
        return [], []

def get_current_elo_ratings(conn, match):
    """Get current Elo ratings for both teams"""
    cursor = conn.cursor()
    
    def get_or_create_elo(team_id, team_name):
        cursor.execute("""
            INSERT OR IGNORE INTO elo_rating (team_id, team_name, elo_rating)
            VALUES (?, ?, 1500)
        """, (team_id, team_name))
        cursor.execute("SELECT elo_rating FROM elo_rating WHERE team_id = ?", (team_id,))
        return cursor.fetchone()[0]
    
    # Get current Elo ratings
    home_elo = get_or_create_elo(match['home_team_id'], match['home_team'])
    away_elo = get_or_create_elo(match['away_team_id'], match['away_team'])
    
    return home_elo, away_elo

def calculate_squad_strength(all_key_players, missing_players):
    """Calculate position-specific squad strengths with debug output"""
    print("\n=== Squad Strength Calculation Debug ===")
    
    # Debug: Print all key players and their positions
    print("\nAll Key Players:")
    for player in all_key_players:
        print(f"Name: {player.get('player_name', 'Unknown'):<20} "
              f"Position: {player.get('position', 'unknown'):<10} "
              f"Score: {player.get('average_score', 0):.2f}")
    
    # Debug: Print missing players
    print("\nMissing Players:")
    for player in missing_players:
        print(f"Name: {player.get('player_name', 'Unknown'):<20} "
              f"Position: {player.get('position', 'unknown'):<10} "
              f"Score: {player.get('average_score', 0):.2f}")
    
    if not all_key_players:
        print("\nNo key players found!")
        return {
            'goalkeeper_strength': None,
            'defence_strength': None,
            'midfield_strength': None,
            'attack_strength': None,
            'overall_strength': None
        }
    
    # Create a set of missing player IDs for quick lookup
    missing_ids = {p['player_id'] for p in missing_players}
    
    # Initialize position-specific strengths
    positions = {
        'goalkeeper': {'max': 0, 'actual': 0, 'weight': 1.0},
        'defender': {'max': 0, 'actual': 0, 'weight': 0.25},
        'midfielder': {'max': 0, 'actual': 0, 'weight': 0.33},
        'forward': {'max': 0, 'actual': 0, 'weight': 0.5},
        'unknown': {'max': 0, 'actual': 0, 'weight': 0.3}
    }
    
    # Calculate strengths by position
    print("\nPosition Calculations:")
    for i, player in enumerate(all_key_players):
        position = player.get('position', 'unknown').lower()
        ranking_weight = 1 / (i + 1)
        player_weight = ranking_weight * player['average_score']
        
        # Add to position totals
        if position in positions:
            position_weight = positions[position]['weight']
            weighted_score = position_weight * player_weight
            positions[position]['max'] += weighted_score
            if player['player_id'] not in missing_ids:
                positions[position]['actual'] += weighted_score
                print(f"Position: {position:<10} Player: {player['player_name']:<20} "
                      f"Weight: {weighted_score:.2f}")
    
    # Calculate strength ratios including unknown
    strengths = {
        'goalkeeper_strength': (
            positions['goalkeeper']['actual'] / positions['goalkeeper']['max'] 
            if positions['goalkeeper']['max'] > 0 else 1.0
        ),
        'defence_strength': (
            positions['defender']['actual'] / positions['defender']['max']
            if positions['defender']['max'] > 0 else 1.0
        ),
        'midfield_strength': (
            positions['midfielder']['actual'] / positions['midfielder']['max']
            if positions['midfielder']['max'] > 0 else 1.0
        ),
        'attack_strength': (
            positions['forward']['actual'] / positions['forward']['max']
            if positions['forward']['max'] > 0 else 1.0
        ),
        'unknown_strength': (  # Add unknown strength calculation
            positions['unknown']['actual'] / positions['unknown']['max']
            if positions['unknown']['max'] > 0 else 1.0
        )
    }
    
    # Calculate overall strength including unknown positions
    total_weight = 0
    weighted_strength = 0
    position_weights = {
        'goalkeeper_strength': 1.0,
        'defence_strength': 0.8,
        'midfield_strength': 0.6,
        'attack_strength': 0.7,
        'unknown_strength': 0.5  # Add weight for unknown positions
    }
    
    for pos, weight in position_weights.items():
        if strengths[pos] is not None:
            weighted_strength += strengths[pos] * weight
            total_weight += weight
            print(f"Adding {pos}: {strengths[pos]:.3f} * {weight} = {strengths[pos] * weight:.3f}")
    
    strengths['overall_strength'] = (
        weighted_strength / total_weight if total_weight > 0 else None
    )
    
    # Debug: Print final strengths
    print("\nFinal Strength Values:")
    for pos, strength in strengths.items():
        print(f"{pos:<20}: {strength:.3f}")
    
    print(f"Overall Strength: {strengths['overall_strength']:.3f}")
    print("=====================================\n")
    
    return strengths

def get_last_lineup(conn, team_id, reference_time):
    """
    Get the lineup details from the team's last completed match
    Args:
        conn: Database connection
        team_id: Team ID to get lineup for
        reference_time: Reference time to look back from
    Returns:
        list: List of dictionaries containing player details
    """
    try:
        cursor = conn.cursor()
        
        # Get the last completed match
        cursor.execute("""
            SELECT match_id
            FROM matches 
            WHERE (home_team_id = ? OR away_team_id = ?)
            AND match_status = 'ended'
            AND datetime(start_time) < datetime(?)
            ORDER BY start_time DESC 
            LIMIT 1
        """, (team_id, team_id, reference_time))
        
        last_match = cursor.fetchone()
        if not last_match:
            print(f"No previous matches found for team {team_id}")
            return []
            
        # First try to get from player_running_stats
        cursor.execute("""
            SELECT player_id, player_name, position
            FROM player_running_stats 
            WHERE match_id = ? 
            AND team_id = ?
        """, (last_match[0], team_id))
        
        lineup = [
            {
                'player_id': row[0],
                'player_name': row[1],
                'position': row[2]
            }
            for row in cursor.fetchall()
        ]
        
        # If no running stats, try the lineups table
        if not lineup:
            print(f"No running stats found for team {team_id}, checking team_lineups table...")
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN home_team_id = ? THEN home_players
                        ELSE away_players 
                    END as players
                FROM team_lineups 
                WHERE match_id = ? 
                AND (home_team_id = ? OR away_team_id = ?)
            """, (team_id, last_match[0], team_id, team_id))
            
            result = cursor.fetchone()
            if result and result[0]:  # Check if we got a result and it's not None
                players_json = json.loads(result[0])
                lineup = [
                    {
                        'player_id': player['id'],
                        'player_name': player['name'],
                        'position': player['type']
                    }
                    for player in players_json
                ]
            
        print(f"Found {len(lineup)} players in last lineup for team {team_id}")
        
        return lineup
        
    except Exception as e:
        print(f"Error getting last lineup for team {team_id}: {str(e)}")
        print(traceback.format_exc())
        return []

def match_has_started(start_time: str) -> bool:
    """
    Determine if a match should be skipped based on its start time.
    
    Args:
        start_time (str): The start time of the match in ISO 8601 format.
        
    Returns:
        bool: True if the match should be skipped, False otherwise.
    """
    match_start_time = datetime.fromisoformat(start_time)

    # Get the current time in UTC
    current_time = datetime.now(pytz.UTC)

    # Calculate the cutoff time (90 minutes before the current time)
    cutoff_time = current_time - timedelta(minutes=90)

    # Debugging output to see the values
    print(f"Match Start Time: {match_start_time}, Current Time: {current_time}, Cutoff Time: {cutoff_time}")

    return match_start_time < cutoff_time

def get_future_lineups(match, average_home_stats, average_away_stats, conn):
    """
    Get future lineups for a match if conditions are met.

    Args:
        match (dict): The match data containing fixture_id and start_time.
        average_home_stats (dict): Average stats for the home team.
        average_away_stats (dict): Average stats for the away team.
        conn: Database connection for fetching last lineups.

    Returns:
        tuple: Home lineup and away lineup.
    """
    # Only get future lineups for matches with advanced stats
    if average_home_stats.get('has_advanced_stats') and average_away_stats.get('has_advanced_stats'):
        # Check if match is less than 45 mins away and lineups haven't been saved yet
        match_time = pd.to_datetime(match['start_time'])
        time_until_match = match_time - pd.Timestamp.now(tz='UTC')
        lineups_path = f"sportradar/data/future_lineups/{match['fixture_id']}.json"
        
        if time_until_match.total_seconds() < 2700 and not os.path.exists(lineups_path):  # 2700 seconds = 45 minutes
            home_lineup, away_lineup = get_match_lineups(match['fixture_id'])
            
            # Save lineups to file
            with open(lineups_path, 'w') as f:
                json.dump({
                    'home_lineup': home_lineup,
                    'away_lineup': away_lineup
                }, f)
        else:
            if os.path.exists(lineups_path):
                with open(lineups_path, 'r') as f:
                    lineups = json.load(f)
                    home_lineup = lineups['home_lineup']
                    away_lineup = lineups['away_lineup']
            else:
                home_lineup = get_last_lineup(conn, match['home_team_id'], match['start_time'])
                away_lineup = get_last_lineup(conn, match['away_team_id'], match['start_time'])
    else:
        home_lineup = []
        away_lineup = []

    return home_lineup, away_lineup

if __name__ == "__main__":
    try:
        output_dir = 'sportradar/data/processed_data'
        advanced_df, no_h2h_df, basic_df = create_test_data('football_data.db', output_dir)
        
        # No need to print again since we already log in the create_test_data function
        # Just add a final summary
        print("\nProcessing complete!")
        
    except Exception as e:
        print(f"\nScript failed: {str(e)}")
