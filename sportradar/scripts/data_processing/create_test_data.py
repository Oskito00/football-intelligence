import sqlite3
import os
from datetime import datetime
from numpy import log
import pandas as pd
import traceback

import requests

# Local imports
from constants import (
    PREVIOUS_MATCHES_QUERY,
    STATS_CHECK_QUERY
)
from player_stats import get_key_players_count, initialize_player_database, process_match_stats
from team_processing import (
    calculate_match_importance, 
    calculate_form, 
    initialize_database, 
    getH2h_stats
)

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
    WHERE m.match_status != 'ended'
    AND datetime(m.start_time) BETWEEN datetime('now') 
    AND datetime('now', '+3 days')
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
                if player.get('starter', False):  # Only include starting players
                    players_list.append({
                        'player_id': player['id'],
                        'name': player['name'],
                        'position': player['type'],
                        'jersey_number': player['jersey_number']
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

def get_squad_strength_from_last_match(conn, team_id, reference_time):
    """
    Get team's squad strength from their last completed match
    Returns strength between 0 and 1
    """
    # Get all key players from recent games
    key_player_count, all_key_players = get_key_players_count(conn, team_id, reference_time)
    
    if not all_key_players:
        return 0.5  # Default value if no key players
    
    # Get the last completed match
    cursor = conn.cursor()
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
        return 0.5
    
    # Get players who didn't play in last match
    cursor.execute("""
        SELECT player_id
        FROM player_running_stats 
        WHERE match_id = ? 
        AND team_id = ?
    """, (last_match[0], team_id))
    
    played_ids = {row[0] for row in cursor.fetchall()}
    
    # Identify missing players (key players who didn't play)
    missing_players = [
        player for player in all_key_players 
        if player['player_id'] not in played_ids
    ]
    
    # Calculate strength using the existing function
    strength = calculate_squad_strength(all_key_players, missing_players)
    
    # Return strength directly (already between 0 and 1)
    return strength if strength is not None else 0.5

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
            
        # Get player IDs and positions from the last match
        cursor.execute("""
            SELECT player_id,player_name, position
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
        
        print(f"Found {len(lineup)} players in last lineup for team {team_id}")
        
        return lineup
        
    except Exception as e:
        print(f"Error getting last lineup for team {team_id}: {str(e)}")
        print(traceback.format_exc())
        return []

def create_test_data(db_path, output_dir):
    """Create test dataset from upcoming matches"""
    # Create log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(output_dir, f'test_data_creation_log_{timestamp}.txt')
    
    def log(message):
        """Helper function to write to both console and log file"""
        print(message)
        with open(log_file, 'a') as f:
            f.write(message + '\n')
    
    log(f"\n=== Starting test data creation at {datetime.now()} ===")
    try:
        conn = sqlite3.connect(db_path)
        os.makedirs(output_dir, exist_ok=True)
        
        upcoming_matches_df = pd.read_sql_query(get_upcoming_matches_query(), conn)
        total_matches = len(upcoming_matches_df)
        log(f"Found {total_matches} upcoming matches")
        
        basic_data = []
        advanced_data = []
        
        # Debugging counters
        skipped_not_next = 0
        skipped_no_h2h = 0
        skipped_no_squad_strength = 0
        skipped_other_errors = 0
        
        for idx, match in upcoming_matches_df.iterrows():
            try:
                log(f"\nProcessing match {idx + 1}/{total_matches}")
                log(f"Match: {match['home_team']} vs {match['away_team']}")
                log(f"Time: {match['start_time']}")
                log(f"ID: {match['fixture_id']}")
                
                # Check if next match
                home_next = is_next_unplayed_match(conn, match['home_team_id'], match['start_time'])
                away_next = is_next_unplayed_match(conn, match['away_team_id'], match['start_time'])
                
                if not (home_next and away_next):
                    log(f"→ Skipping: Not the next match")
                    if not home_next:
                        log("  - Not next for home team")
                    if not away_next:
                        log("  - Not next for away team")
                    skipped_not_next += 1
                    continue
                
                log("→ Is next match for both teams")
                
                # Calculate form
                average_home_stats, average_away_stats = calculate_form(conn, match)
                log("→ Form calculated")
                log(f"  Home stats: {average_home_stats}")
                log(f"  Away stats: {average_away_stats}")
                
                competition_id = match['competition_id']
                match_importance = calculate_match_importance(conn, match)
                log(f"→ Match importance: {match_importance}")
                
                home_elo_rating, away_elo_rating = get_current_elo_ratings(conn, match)
                log(f"→ ELO ratings - Home: {home_elo_rating}, Away: {away_elo_rating}")
                
                # Get H2H stats from database first
                h2h_stats = getH2h_stats(conn, match['home_team_id'], match['away_team_id'], match['start_time'])
                
                # If no H2H stats found in database, try the API
                if not h2h_stats:
                    print("❌ Skipped because no H2H stats found in database")
                    print(f"No H2H stats found in database for {match['home_team']} vs {match['away_team']}, trying API...")
                    # h2h_stats = get_h2h_from_api(match['home_team_id'], match['away_team_id'])
                    #TODO: Choose whether to use API or not
                
                if not h2h_stats:
                    log(f"→ Skipping match: No H2H history available from database or API")
                    skipped_no_h2h += 1
                    continue

                # Get key players for both teams
                home_key_count, home_key_players = get_key_players_count(conn, match['home_team_id'], match['start_time'])
                away_key_count, away_key_players = get_key_players_count(conn, match['away_team_id'], match['start_time'])
                
                log(f"\nKey players analysis:")
                log(f"Home team key players: {home_key_count}")
                for player in home_key_players:
                    log(f"- {player['player_name']} ({player['position']}) - Importance: {player['importance']}, Form: {player['form']}")
                
                log(f"\nAway team key players: {away_key_count}")
                for player in away_key_players:
                    log(f"- {player['player_name']} ({player['position']}) - Importance: {player['importance']}, Form: {player['form']}")
                
                # Get expected lineups for the match
                #TODO: Should schedule this to run 45 minutes before the match starts, so that we get the most accurate lineup, before that we should use the last lineup...
                # home_lineup, away_lineup = get_match_lineups(match['fixture_id'])
                home_lineup = get_last_lineup(conn, match['home_team_id'], match['start_time'])
                print("Hello")
                print(f"Home lineup: {home_lineup}")
                away_lineup = get_last_lineup(conn, match['away_team_id'], match['start_time'])
                print(f"Away lineup: {away_lineup}")

                log("\nLineup analysis:")
                log("Home team lineup:")
                for player in home_lineup:
                    log(f"- #{player['player_name']} ({player['position']})")
                
                log("\nAway team lineup:")
                for player in away_lineup:
                    log(f"- #{player['player_name']} ({player['position']})")
                
                # Compare with key players to find who's missing
                home_missing_players = [
                    player for player in home_key_players 
                    if not any(lp['player_id'] == player['player_id'] for lp in home_lineup)
                ]
                
                away_missing_players = [
                    player for player in away_key_players 
                    if not any(lp['player_id'] == player['player_id'] for lp in away_lineup)
                ]
                
                log("\nMissing key players:")
                log("Home team:")
                for player in home_missing_players:
                    log(f"- {player['player_name']} ({player['position']}) - Importance: {player['importance']}")
                
                log("Away team:")
                for player in away_missing_players:
                    log(f"- {player['player_name']} ({player['position']}) - Importance: {player['importance']}")
                
                # Calculate squad strengths with missing players information
                home_team_overall_strength = calculate_squad_strength(home_key_players, home_missing_players)
                away_team_overall_strength = calculate_squad_strength(away_key_players, away_missing_players)
                
                # Extract squad strengths from the calculated values
                home_team_gk_strength = home_team_overall_strength['goalkeeper_strength']
                home_team_defence_strength = home_team_overall_strength['defence_strength']
                home_team_midfield_strength = home_team_overall_strength['midfield_strength']
                home_team_attack_strength = home_team_overall_strength['attack_strength']

                away_team_gk_strength = away_team_overall_strength['goalkeeper_strength']
                away_team_defence_strength = away_team_overall_strength['defence_strength']
                away_team_midfield_strength = away_team_overall_strength['midfield_strength']
                away_team_attack_strength = away_team_overall_strength['attack_strength']

                # Then use these variables in your strength components check
                home_strength_components = [
                    home_team_gk_strength,
                    home_team_defence_strength,
                    home_team_midfield_strength,
                    home_team_attack_strength,
                    home_team_overall_strength['overall_strength']
                ]
    
                away_strength_components = [
                    away_team_gk_strength,
                    away_team_defence_strength,
                    away_team_midfield_strength,
                    away_team_attack_strength,
                    away_team_overall_strength['overall_strength']
                ]
    
                if any(pd.isna(x) for x in home_strength_components) or any(pd.isna(x) for x in away_strength_components):
                    log(f"→ Skipping: Missing squad strength data for {match['home_team']} vs {match['away_team']}")
                    skipped_no_squad_strength += 1
                    continue

                # Create basic row
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
                    'away_momentum': average_away_stats.get('momentum'),
                    'h2h_avg_draw_rate': h2h_stats[match['home_team_id']]['avg_draw_rate'],
                    'home_h2h_avg_goals': h2h_stats[match['home_team_id']]['avg_goals'],
                    'home_h2h_avg_clean_sheets': h2h_stats[match['home_team_id']]['avg_clean_sheets'],
                    'home_h2h_avg_points': h2h_stats[match['home_team_id']]['avg_points'],
                    'away_h2h_avg_goals': h2h_stats[match['away_team_id']]['avg_goals'],
                    'away_h2h_avg_clean_sheets': h2h_stats[match['away_team_id']]['avg_clean_sheets'],
                    'away_h2h_avg_points': h2h_stats[match['away_team_id']]['avg_points']
                }
                
                if home_elo_rating is not None and away_elo_rating is not None:
                    basic_row['home_elo_rating'] = home_elo_rating
                    basic_row['away_elo_rating'] = away_elo_rating

                # Add to appropriate dataset
                has_advanced_home = average_home_stats.get('has_advanced_stats') == 1
                has_advanced_away = average_away_stats.get('has_advanced_stats') == 1
                
                log(f"→ Advanced stats available - Home: {has_advanced_home}, Away: {has_advanced_away}")
                
                if not has_advanced_home and not has_advanced_away and home_team_overall_strength is not None and away_team_overall_strength is not None:
                    basic_row['home_team_gk_strength'] = home_team_gk_strength
                    basic_row['home_team_defence_strength'] = home_team_defence_strength
                    basic_row['home_team_midfield_strength'] = home_team_midfield_strength
                    basic_row['home_team_attack_strength'] = home_team_attack_strength
                    basic_row['away_team_gk_strength'] = away_team_gk_strength
                    basic_row['away_team_defence_strength'] = away_team_defence_strength
                    basic_row['away_team_midfield_strength'] = away_team_midfield_strength
                    basic_row['away_team_attack_strength'] = away_team_attack_strength
                    basic_row['home_team_overall_strength'] = home_team_overall_strength['overall_strength']
                    basic_row['away_team_overall_strength'] = away_team_overall_strength['overall_strength']
                    basic_data.append(basic_row)
                    log("→ Added to basic dataset")
                
                if has_advanced_home and has_advanced_away and home_team_overall_strength is not None and away_team_overall_strength is not None:
                    advanced_row = basic_row.copy()
                    advanced_row.update({
                        'home_pass_effectiveness': round(average_home_stats['pass_effectiveness'], 2),
                        'home_shot_accuracy': round(average_home_stats['shot_accuracy'], 2),
                        'home_conversion_rate': round(average_home_stats['conversion_rate'], 2),
                        'home_defensive_success': round(average_home_stats['defensive_success'], 2),
                        'away_pass_effectiveness': round(average_away_stats['pass_effectiveness'], 2),
                        'away_shot_accuracy': round(average_away_stats['shot_accuracy'], 2),
                        'away_conversion_rate': round(average_away_stats['conversion_rate'], 2),
                        'away_defensive_success': round(average_away_stats['defensive_success'], 2),
                        'home_team_gk_strength': home_team_gk_strength,
                        'home_team_defence_strength': home_team_defence_strength,
                        'home_team_midfield_strength': home_team_midfield_strength,
                        'home_team_attack_strength': home_team_attack_strength,
                        'away_team_gk_strength': away_team_gk_strength,
                        'away_team_defence_strength': away_team_defence_strength,
                        'away_team_midfield_strength': away_team_midfield_strength,
                        'away_team_attack_strength': away_team_attack_strength,
                        'home_team_overall_strength': home_team_overall_strength['overall_strength'],
                        'away_team_overall_strength': away_team_overall_strength['overall_strength']
                    })
                    advanced_data.append(advanced_row)
                    log("→ Added to advanced dataset")

            except Exception as e:
                log(f"→ Error processing match: {str(e)}")
                log(f"  Full error: {traceback.format_exc()}")
                skipped_other_errors += 1
                continue

        # Print summary statistics
        summary = f"""
=== Processing Summary ===
Total matches found: {total_matches}
Skipped - not next match: {skipped_not_next}
Skipped - no H2H history: {skipped_no_h2h}
Skipped - missing squad strength: {skipped_no_squad_strength}
Skipped - other errors: {skipped_other_errors}
Successfully processed - basic: {len(basic_data)}
Successfully processed - advanced: {len(advanced_data)}
"""
        log(summary)
        
        # Save datasets
        basic_df = pd.DataFrame(basic_data)
        advanced_df = pd.DataFrame(advanced_data)
        
        basic_output = os.path.join(output_dir, 'test_data_basic.csv')
        advanced_output = os.path.join(output_dir, 'test_data_advanced.csv')
        
        basic_df.to_csv(basic_output, index=False)
        advanced_df.to_csv(advanced_output, index=False)
        
        log(f"\nSaved basic dataset with {len(basic_df)} matches to {basic_output}")
        log(f"Saved advanced dataset with {len(advanced_df)} matches to {advanced_output}")
        
        return basic_df, advanced_df
        
    except Exception as e:
        log(f"\nError: {str(e)}")
        log(f"Full error: {traceback.format_exc()}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

def check_upcoming_matches(db_path):
    """
    Check upcoming matches and identify which ones are next for both teams.
    
    Args:
        db_path: Path to the SQLite database
        
    Returns:
        List of tuples: (fixture_id, start_time, home_team, away_team, is_next_match)
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get upcoming matches
        cursor.execute(get_upcoming_matches_query())
        upcoming_matches = cursor.fetchall()
        
        print(f"\nFound {len(upcoming_matches)} upcoming matches")
        print("\nAnalyzing matches:")
        print("-" * 80)
        
        results = []
        for match in upcoming_matches:
            fixture_id = match[0]
            start_time = match[1]
            home_team = match[10]  # home_team_name
            away_team = match[11]  # away_team_name
            home_team_id = match[8]
            away_team_id = match[9]
            
            # Check if it's next match for both teams
            home_next = is_next_unplayed_match(conn, home_team_id, start_time)
            away_next = is_next_unplayed_match(conn, away_team_id, start_time)
            is_next_match = home_next and away_next
            
            results.append((fixture_id, start_time, home_team, away_team, is_next_match))
            
            # Print result with formatting
            status = "✓ NEXT MATCH" if is_next_match else "✗ Not next match"
            print(f"Match: {home_team} vs {away_team}")
            print(f"Time:  {start_time}")
            print(f"ID:    {fixture_id}")
            print(f"Status: {status}")
            if not is_next_match:
                print(f"Reason: {'Not next for home team' if not home_next else 'Not next for away team'}")
            print("-" * 80)
        
        # Print summary
        next_matches = [r for r in results if r[4]]
        print(f"\nSummary: {len(next_matches)} out of {len(results)} matches are next for both teams")
        
        return results
        
    except Exception as e:
        print(f"Error checking upcoming matches: {e}")
        return []
    
    finally:
        if 'conn' in locals():
            conn.close()

def get_h2h_from_api(home_team_id, away_team_id):
    """
    Get head-to-head statistics from Sportradar API
    Args:
        home_team_id: URN of home team (e.g., 'sr:competitor:17')
        away_team_id: URN of away team (e.g., 'sr:competitor:42')
    """
    try:
        api_key = os.getenv('SPORTRADAR_API_KEY')
        if not api_key:
            print("Error: SPORTRADAR_API_KEY environment variable not set")
            return None

        api_url = f"https://api.sportradar.com/soccer-extended/trial/v4/en/competitors/{home_team_id.replace(':', '%3A')}/versus/{away_team_id.replace(':', '%3A')}/summaries.json?api_key={api_key}"
        print(f"Fetching H2H data from API...")
        
        response = requests.get(api_url)
        if response.status_code != 200:
            print(f"API request failed with status code: {response.status_code}")
            print(f"Response text: {response.text}")
            return None
            
        data = response.json()
        last_meetings = data.get('last_meetings', [])
        print(f"\nFound {len(last_meetings)} last meetings")
        
        h2h_stats = {
            home_team_id: {'goals': 0, 'clean_sheets': 0, 'points': 0, 'matches': 0},
            away_team_id: {'goals': 0, 'clean_sheets': 0, 'points': 0, 'matches': 0}
        }
        
        draw_count = 0
        total_matches = 0
        
        for meeting in last_meetings:
            sport_event = meeting.get('sport_event', {})
            status = meeting.get('sport_event_status', {})
            
            if status.get('status') != 'closed':
                print(f"Skipping - match status is {status.get('status')}")
                continue
                
            total_matches += 1
            
            # Get teams and scores
            teams = {}  # Will store both teams and their roles
            for competitor in sport_event.get('competitors', []):
                team_id = competitor.get('id')
                teams[team_id] = {
                    'score': status.get('home_score' if competitor.get('qualifier') == 'home' else 'away_score', 0),
                    'is_home': competitor.get('qualifier') == 'home'
                }
            
            # Process stats for both teams if they're our target teams
            for team_id, team_data in teams.items():
                if team_id not in [home_team_id, away_team_id]:
                    continue
                    
                opponent_id = away_team_id if team_id == home_team_id else home_team_id
                opponent_data = teams.get([t for t in teams.keys() if t != team_id][0])
                
                team_score = team_data['score']
                opponent_score = opponent_data['score']
                
                print(f"Processing {team_id}: scored {team_score}, conceded {opponent_score}")
                
                # Update stats
                h2h_stats[team_id]['goals'] += team_score
                if opponent_score == 0:
                    h2h_stats[team_id]['clean_sheets'] += 1
                if team_score > opponent_score:
                    h2h_stats[team_id]['points'] += 3
                elif team_score == opponent_score:
                    h2h_stats[team_id]['points'] += 1
                    if team_id == home_team_id:  # Only count draws once
                        draw_count += 1
                h2h_stats[team_id]['matches'] += 1
        
        if total_matches == 0:
            print("No completed H2H matches found")
            return None
            
        # Calculate averages and ensure all required fields exist
        draw_rate = round(draw_count / total_matches, 2) if total_matches > 0 else 0
        
        for team_id in [home_team_id, away_team_id]:
            matches = h2h_stats[team_id]['matches']
            if matches > 0:
                h2h_stats[team_id].update({
                    'avg_goals': round(h2h_stats[team_id]['goals'] / matches, 2),
                    'avg_clean_sheets': round(h2h_stats[team_id]['clean_sheets'] / matches, 2),
                    'avg_points': round(h2h_stats[team_id]['points'] / matches, 2),
                    'avg_draw_rate': draw_rate  # Add this to both teams
                })
        
        print(f"\nProcessed {total_matches} completed H2H matches")
        print(f"Final stats: {h2h_stats}")
        
        return h2h_stats
        
    except Exception as e:
        print(f"Error fetching H2H data from API: {str(e)}")
        print(traceback.format_exc())
        return None

if __name__ == "__main__":
    # # Test H2H data
    # h2h_stats = get_h2h_from_api("sr:competitor:42", "sr:competitor:17")
    # if h2h_stats:
    #     print("\nHead-to-head statistics:")
    #     print(f"Total matches: {h2h_stats['sr:competitor:42']['matches']}")
    #     print(f"Home team avg goals: {h2h_stats['sr:competitor:42']['avg_goals']}")
    #     print(f"Away team avg goals: {h2h_stats['sr:competitor:17']['avg_goals']}")
    #     print(f"Draw rate: {h2h_stats['avg_draw_rate']}")

    # # Test the function
    # home_players, away_players = get_match_lineups('sr:sport_event:53160771')
    # # home_players, away_players = get_match_lineups('sr:sport_event:53160785')
    
    # print("\nHome team lineup:")
    # for player in home_players:
    #     print(f"- #{player['jersey_number']} {player['name']} ({player['position']})")
    
    # print("\nAway team lineup:")
    # for player in away_players:
    #     print(f"- #{player['jersey_number']} {player['name']} ({player['position']})")

    try:
        output_dir = 'sportradar/data/processed_data'
        basic_df, advanced_df = create_test_data('football_data.db', output_dir)
    except Exception as e:
        print(f"\nScript failed: {str(e)}")

    # db_path = "football_data.db"
    # check_upcoming_matches(db_path) 