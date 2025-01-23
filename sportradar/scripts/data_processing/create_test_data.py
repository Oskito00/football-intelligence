import sqlite3
import os
from datetime import datetime
import pandas as pd
import traceback

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
    AND datetime('now', '+5 days')
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
    """
    Calculate squad strength based on weighted importance of available players
    
    Args:
        all_key_players: List of all key players with their scores
        missing_players: List of missing key players
    
    Returns:
        float: Squad strength score between 0 and 1
    """
    if not all_key_players:
        return None
        
    # Create a set of missing player IDs for quick lookup
    missing_ids = {p['player_id'] for p in missing_players}
    
    # Calculate maximum possible strength (weighted by position in ranking)
    max_strength = 0
    actual_strength = 0
    
    for i, player in enumerate(all_key_players):
        # Weight by position (higher ranked players count more)
        position_weight = 1 / (i + 1)  # 1st = 1.0, 2nd = 0.5, 3rd = 0.33, etc.
        player_weight = position_weight * player['average_score']
        
        max_strength += player_weight
        
        # If player is available (not in missing_ids), add to actual strength
        if player['player_id'] not in missing_ids:
            actual_strength += player_weight
    
    # Return ratio of actual to maximum strength
    return actual_strength / max_strength if max_strength > 0 else 0.0

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
                
                h2h_stats = getH2h_stats(conn, match['home_team_id'], match['away_team_id'], match['start_time'])
                if h2h_stats is None:
                    log("→ Skipping: No head-to-head history")
                    skipped_no_h2h += 1
                    continue
                log("→ H2H stats retrieved")
                log(f"  H2H stats: {h2h_stats}")
                
                home_squad_strength = get_squad_strength_from_last_match(conn, match['home_team_id'], match['start_time'])
                away_squad_strength = get_squad_strength_from_last_match(conn, match['away_team_id'], match['start_time'])
                
                log(f"→ Squad strengths - Home: {home_squad_strength}, Away: {away_squad_strength}")
                
                if home_squad_strength is None or away_squad_strength is None:
                    log("→ Skipping: Missing squad strength data")
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
                
                if not has_advanced_home and not has_advanced_away:
                    basic_row['home_squad_strength'] = home_squad_strength
                    basic_row['away_squad_strength'] = away_squad_strength
                    basic_data.append(basic_row)
                    log("→ Added to basic dataset")
                
                if has_advanced_home and has_advanced_away:
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
                        'home_squad_strength': round(home_squad_strength, 2),
                        'away_squad_strength': round(away_squad_strength, 2),
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

if __name__ == "__main__":
    try:
        output_dir = 'sportradar/data/processed_data'
        basic_df, advanced_df = create_test_data('football_data.db', output_dir)
    except Exception as e:
        print(f"\nScript failed: {str(e)}")

    # db_path = "football_data.db"
    # check_upcoming_matches(db_path) 