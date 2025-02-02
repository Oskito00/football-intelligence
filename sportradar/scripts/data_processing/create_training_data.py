import os
import sys

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
sys.path.append(project_root)

import sqlite3

from datetime import datetime
import pandas as pd
import traceback
# Local imports
from sportradar.scripts.constants.constants import (
    ENDED_MATCHES_QUERY
)
from player_stats import initialize_player_database, process_match_stats
from team_processing import add_points_for_team, add_team_stats, calculate_elo_rating, calculate_match_importance, calculate_form_stats, get_match_formations, getH2h_stats, initialize_database, refined_categorize_formation

def create_training_data(db_path, output_dir, debug_mode=False):
    """Create both basic and advanced training datasets from match database"""
    print(f"\n=== Starting training data creation at {datetime.now()} ===")
    
    # Add log file creation at the start
    log_file = os.path.join(output_dir, 'processing_log.txt')
    processed_matches = {}  # Track matches and their calculated strengths
    
    try:
        # Ensure database exists
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database not found at: {db_path}")
        print(f"Using database: {db_path}")
        print(f"Debug mode: {'ON' if debug_mode else 'OFF'}")
            
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        print("Successfully connected to database")

        #TODO: Check this works, adds new matches without having to re-initialize the database
        # If we need to re-initialize the database, uncomment the following two lines
        # initialize_database(conn)
        # initialize_player_database(conn)
        
        # Get all of the matches that have already been processed
        processed_match_ids, processed_team_times = get_processed_matches(conn)
        print(f"Found {len(processed_match_ids)} previously processed matches")
        
        # Get all matches that have already been completed to analyse the data/stats
        print("\nFetching completed matches...")
        matches_query = ENDED_MATCHES_QUERY
        matches_df = pd.read_sql_query(matches_query, conn)
        print(f"Found {len(matches_df)} completed matches")
        
        basic_data = []
        advanced_data = []
        advanced_data_with_formation = []
        total_matches = len(matches_df)
        processed_count = 0
        skipped_count = 0
        
        with open(log_file, 'w') as f:
            # For every match that has been completed, process the stats
            for idx, match in matches_df.iterrows():
                try:
                    # Extract the match_id
                    match_id = match['fixture_id']
                    
                    # If the match has already been processed, skip it to avoid duplicates
                    if match_id in processed_match_ids:
                        print(f"Skipping match {match_id} as it has already been processed")
                        skipped_count += 1
                        continue
                    
                    f.write(f"\n=== Processing match {match_id} ===\n")
                    f.write(f"Home: {match['home_team']} vs Away: {match['away_team']}\n")
                    
                    # Process match stats
                    print("Adding team stats...")
                    add_team_stats(conn, match)
                    
                    # Calculate the form of each team based on their previous 5 match stats.
                    print("Calculating form based on previous 5 match stats...")
                    average_home_stats, average_away_stats = calculate_form_stats(conn, match)
                    print(f"Home advanced stats: {average_home_stats.get('has_advanced_stats')}")
                    print(f"Away advanced stats: {average_away_stats.get('has_advanced_stats')}")
                    
                    competition_id = match['competition_id']
                    # Get the formations of each team
                    home_formation, away_formation = get_match_formations(match_id)
                    print(f"Formations - Home: {home_formation}, Away: {away_formation}")

                    # Now update ELO ratings based on match outcome
                    print("Calculating match importance and ELO...")
                    match_importance = calculate_match_importance(conn, match)
                    home_elo_rating, away_elo_rating = calculate_elo_rating(conn, match, match_importance)
                    print(f"ELO ratings - Home: {home_elo_rating}, Away: {away_elo_rating}")
                    
                    #Update the season points table based on the outcome of this match
                    add_points_for_team(conn, match)

                    # H2H Stats
                    print("Getting H2H stats...")
                    h2h_stats = getH2h_stats(conn, match['home_team_id'], match['away_team_id'], match['start_time'])
                    if not h2h_stats:
                        #TODO: Change to not skip if no h2h but add to advanced_no_h2h dataset
                        print(f"❌ No H2H stats available for match: {match['fixture_id']}")
                        continue

                    try:
                        print("Processing player stats...")
                        result = process_match_stats(conn, match['fixture_id'], match['home_team_id'], 
                                                   match['away_team_id'], match['start_time'], 
                                                   match['home_team'], match['away_team'])
                        print(f"✓ Processed {result['processed_count']} players")
                        print("Squad strengths:")
                        print(f"Home - GK: {result.get('home_team_gk_strength')}, DEF: {result.get('home_team_defence_strength')}, "
                              f"MID: {result.get('home_team_midfield_strength')}, ATT: {result.get('home_team_attack_strength')}")
                        print(f"Away - GK: {result.get('away_team_gk_strength')}, DEF: {result.get('away_team_defence_strength')}, "
                              f"MID: {result.get('away_team_midfield_strength')}, ATT: {result.get('away_team_attack_strength')}")
                                    
                    except ValueError as error:
                        print(f"❌ Player stats error: {str(error)}")
                        continue
                    except Exception as error:
                        print(f"❌ Unexpected error in player stats: {str(error)}")
                        if debug_mode:
                            raise
                        continue

                    print("\nChecking conditions for dataset inclusion:")
                    
                    # Create basic row for all matches becuase all matches have basic stats
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
                    }

                    if home_elo_rating is not None and away_elo_rating is not None:
                        basic_row['home_elo_rating'] = home_elo_rating
                        basic_row['away_elo_rating'] = away_elo_rating


                    if (average_home_stats.get('has_advanced_stats') == 0 and average_away_stats.get('has_advanced_stats') == 0) and result['home_team_overall_strength'] is not None and result['away_team_overall_strength'] is not None:
                        basic_row['home_goals'] = match['home_goals']
                        basic_row['away_goals'] = match['away_goals']
                        basic_data.append(basic_row)


                    if average_home_stats.get('has_advanced_stats') == 1 and average_away_stats.get('has_advanced_stats') == 1 and result['home_team_overall_strength'] is not None and result['away_team_overall_strength'] is not None and home_formation is not None and away_formation is not None:
                        advanced_row_with_formation = basic_row.copy()
                        advanced_row_with_formation.update({
                            'h2h_avg_draw_rate': h2h_stats[match['home_team_id']]['avg_draw_rate'],
                            'home_h2h_avg_goals': h2h_stats[match['home_team_id']]['avg_goals'],
                            'home_h2h_avg_clean_sheets': h2h_stats[match['home_team_id']]['avg_clean_sheets'],
                            'home_h2h_avg_points': h2h_stats[match['home_team_id']]['avg_points'],
                            'away_h2h_avg_goals': h2h_stats[match['away_team_id']]['avg_goals'],
                            'away_h2h_avg_clean_sheets': h2h_stats[match['away_team_id']]['avg_clean_sheets'],
                            'away_h2h_avg_points': h2h_stats[match['away_team_id']]['avg_points'],
                            'home_pass_effectiveness': round(average_home_stats['pass_effectiveness'], 2),
                            'home_shot_accuracy': round(average_home_stats['shot_accuracy'], 2),
                            'home_conversion_rate': round(average_home_stats['conversion_rate'], 2),
                            'home_defensive_success': round(average_home_stats['defensive_success'], 2),
                            'away_pass_effectiveness': round(average_away_stats['pass_effectiveness'], 2),
                            'away_shot_accuracy': round(average_away_stats['shot_accuracy'], 2),
                            'away_conversion_rate': round(average_away_stats['conversion_rate'], 2),
                            'away_defensive_success': round(average_away_stats['defensive_success'], 2),
                            'home_team_gk_strength': result['home_team_gk_strength'],
                            'home_team_defence_strength': result['home_team_defence_strength'],
                            'home_team_midfield_strength': result['home_team_midfield_strength'],
                            'home_team_attack_strength': result['home_team_attack_strength'],
                            'away_team_gk_strength': result['away_team_gk_strength'],
                            'away_team_defence_strength': result['away_team_defence_strength'],
                            'away_team_midfield_strength': result['away_team_midfield_strength'],
                            'away_team_attack_strength': result['away_team_attack_strength'],
                            'home_team_overall_strength': result['home_team_overall_strength'],
                            'away_team_overall_strength': result['away_team_overall_strength'],
                            'home_formation': refined_categorize_formation(home_formation),
                            'away_formation': refined_categorize_formation(away_formation),
                            'home_goals': match['home_goals'],
                            'away_goals': match['away_goals'],
                        })
                        advanced_data_with_formation.append(advanced_row_with_formation)
                    

                    # Process advanced stats if available
                    if average_home_stats.get('has_advanced_stats') == 1 and average_away_stats.get('has_advanced_stats') == 1 and result['home_team_overall_strength'] is not None and result['away_team_overall_strength'] is not None:
                        advanced_row = basic_row.copy()
                        advanced_row.update({
                            'h2h_avg_draw_rate': h2h_stats[match['home_team_id']]['avg_draw_rate'],
                            'home_h2h_avg_goals': h2h_stats[match['home_team_id']]['avg_goals'],
                            'home_h2h_avg_clean_sheets': h2h_stats[match['home_team_id']]['avg_clean_sheets'],
                            'home_h2h_avg_points': h2h_stats[match['home_team_id']]['avg_points'],
                            'away_h2h_avg_goals': h2h_stats[match['away_team_id']]['avg_goals'],
                            'away_h2h_avg_clean_sheets': h2h_stats[match['away_team_id']]['avg_clean_sheets'],
                            'away_h2h_avg_points': h2h_stats[match['away_team_id']]['avg_points'],
                            'home_pass_effectiveness': round(average_home_stats['pass_effectiveness'], 2),
                            'home_shot_accuracy': round(average_home_stats['shot_accuracy'], 2),
                            'home_conversion_rate': round(average_home_stats['conversion_rate'], 2),
                            'home_defensive_success': round(average_home_stats['defensive_success'], 2),
                            'away_pass_effectiveness': round(average_away_stats['pass_effectiveness'], 2),
                            'away_shot_accuracy': round(average_away_stats['shot_accuracy'], 2),
                            'away_conversion_rate': round(average_away_stats['conversion_rate'], 2),
                            'away_defensive_success': round(average_away_stats['defensive_success'], 2),
                            'home_team_gk_strength': result['home_team_gk_strength'],
                            'home_team_defence_strength': result['home_team_defence_strength'],
                            'home_team_midfield_strength': result['home_team_midfield_strength'],
                            'home_team_attack_strength': result['home_team_attack_strength'],
                            'away_team_gk_strength': result['away_team_gk_strength'],
                            'away_team_defence_strength': result['away_team_defence_strength'],
                            'away_team_midfield_strength': result['away_team_midfield_strength'],
                            'away_team_attack_strength': result['away_team_attack_strength'],
                            'home_team_overall_strength': result['home_team_overall_strength'],
                            'away_team_overall_strength': result['away_team_overall_strength'],
                            'home_goals': match['home_goals'],
                            'away_goals': match['away_goals'],
                        })
                        advanced_data.append(advanced_row)

                    # Log key players and missing players
                    f.write("\nKey Players Analysis:\n")
                    f.write("Home Team Key Players:\n")
                    for player in result['home_key_players']:
                        f.write(f"- {player['player_name']} ({player['position']}) - "
                               f"Score: {player.get('average_score', 0):.2f}, "
                               f"Importance: {player.get('importance', 'N/A')}\n")
                    
                    f.write("\nHome Team Missing Players:\n")
                    for player in result['home_key_players_missing']:
                        f.write(f"- {player['player_name']} ({player['position']}) - "
                               f"Score: {player.get('average_score', 0):.2f}, "
                               f"Importance: {player.get('importance_score', 'N/A')}\n")
                    
                    f.write("\nAway Team Key Players:\n")
                    for player in result['away_key_players']:
                        f.write(f"- {player['player_name']} ({player['position']}) - "
                               f"Score: {player.get('average_score', 0):.2f}, "
                               f"Importance: {player.get('importance', 'N/A')}\n")
                    
                    f.write("\nAway Team Missing Players:\n")
                    for player in result['away_key_players_missing']:
                        f.write(f"- {player['player_name']} ({player['position']}) - "
                               f"Score: {player.get('average_score', 0):.2f}, "
                               f"Importance: {player.get('importance_score', 'N/A')}\n")
                    
                    # Then your existing squad strengths logging
                    f.write(f"\nMatch strengths calculated:\n")
                    f.write(f"Home squad - GK: {result.get('home_team_gk_strength')}, DEF: {result.get('home_team_defence_strength')}, "
                           f"MID: {result.get('home_team_midfield_strength')}, ATT: {result.get('home_team_attack_strength')}\n")
                    
                    f.write(f"Away squad - GK: {result.get('away_team_gk_strength')}, DEF: {result.get('away_team_defence_strength')}, "
                           f"MID: {result.get('away_team_midfield_strength')}, ATT: {result.get('away_team_attack_strength')}\n")
                    
                    # Log which datasets this match is being added to
                    f.write("\nDataset additions:\n")
                    if (average_home_stats.get('has_advanced_stats') == 0 and 
                        average_away_stats.get('has_advanced_stats') == 0 and 
                        result['home_team_overall_strength'] is not None and 
                        result['away_team_overall_strength'] is not None):
                        f.write("✓ Adding to basic dataset\n")
                    
                    if (home_formation is not None and 
                        away_formation is not None and 
                        average_home_stats.get('has_advanced_stats') == 1 and 
                        average_away_stats.get('has_advanced_stats') == 1 and 
                        result['home_team_overall_strength'] is not None and 
                        result['away_team_overall_strength'] is not None):
                        f.write("✓ Adding to advanced with formation dataset\n")
                    
                    if (average_home_stats.get('has_advanced_stats') == 1 and 
                        average_away_stats.get('has_advanced_stats') == 1 and 
                        result['home_team_overall_strength'] is not None and 
                        result['away_team_overall_strength'] is not None):
                        f.write("✓ Adding to advanced dataset\n")
                    
                    f.write(f"\nCurrent dataset sizes:\n")
                    f.write(f"Basic: {len(basic_data)}\n")
                    f.write(f"Advanced: {len(advanced_data)}\n")
                    f.write(f"Advanced with formation: {len(advanced_data_with_formation)}\n")
                    f.write("=== Finished processing match ===\n\n")
                    
                    # If we successfully process the match and add it to any dataset, increment the counter
                    if (result['home_team_overall_strength'] is not None and 
                        result['away_team_overall_strength'] is not None):
                        processed_count += 1  # Increment counter here
                    
                except Exception as e:
                    f.write(f"\nError processing match {match['fixture_id']}: {str(e)}\n")
                    if debug_mode:
                        raise
                    continue
                    
            # Create DataFrames once
            basic_df = pd.DataFrame(basic_data)
            advanced_df = pd.DataFrame(advanced_data)
            advanced_with_formation_df = pd.DataFrame(advanced_data_with_formation)

            basic_output = os.path.join(output_dir, 'training_data_basic.csv')
            advanced_output = os.path.join(output_dir, 'training_data_advanced.csv')
            advanced_output_with_formation = os.path.join(output_dir, 'training_data_advanced_with_formation.csv')
            
            # Log final stats
            f.write("\n=== Final Statistics ===\n")
            f.write(f"Total matches processed: {processed_count}\n")
            f.write(f"Matches skipped: {skipped_count}\n")

            # Append new matches to csv files
            append_to_dataset(basic_df, basic_output)
            append_to_dataset(advanced_df, advanced_output)
            append_to_dataset(advanced_with_formation_df, advanced_output_with_formation)

            print(f"\nProcessing summary:")
            print(f"Total matches found: {total_matches}")
            print(f"Matches processed: {processed_count}")
            print(f"Matches skipped: {skipped_count}")
            
            return basic_df, advanced_df, advanced_with_formation_df
        
    except Exception as e:
        print(f"\nFatal error: {str(e)}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()
            print("\nDatabase connection closed")

#**********************************************************************************************************************
#HELPER FUNCTIONS
#**********************************************************************************************************************

def get_processed_matches(conn):
    """Get all processed matches in one query"""
    cursor = conn.cursor()
    
    # Get all unique combinations of match_id, team names and start times
    cursor.execute('''
        SELECT DISTINCT 
            match_id,
            team_name,
            start_time
        FROM team_running_stats
    ''')
    
    # Create sets for fast lookup
    processed_match_ids = set()
    processed_team_times = set()
    
    for row in cursor.fetchall():
        match_id, team_name, start_time = row
        if match_id:
            processed_match_ids.add(match_id)
        if team_name and start_time:
            processed_team_times.add((team_name, start_time))
    
    return processed_match_ids, processed_team_times

def append_to_dataset(new_df, output_path, id_column='fixture_id'):
    """
    Append new data to existing CSV, handling duplicates
    Args:
        new_df: DataFrame containing new records
        output_path: Path to output CSV file
        id_column: Column to use for duplicate checking
    """
    try:
        if new_df.empty:
            print(f"No new data to append to {output_path}")
            return
            
        if os.path.exists(output_path):
            try:
                # Load existing data
                existing_df = pd.read_csv(output_path)
                print(f"Loaded existing dataset from {output_path} with {len(existing_df)} records")
            except Exception as e:
                print(f"Error reading existing CSV {output_path}: {str(e)}")
                raise
                
            try:
                # Combine with new data
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                print(f"Combined with {len(new_df)} new records")
                
                # Remove duplicates
                original_len = len(combined_df)
                combined_df.drop_duplicates(subset=[id_column], keep='last', inplace=True)
                duplicates_removed = original_len - len(combined_df)
                print(f"Removed {duplicates_removed} duplicate records")
                
                # Save updated dataset
                combined_df.to_csv(output_path, index=False)
                print(f"Saved updated dataset with {len(combined_df)} total records")
                
            except Exception as e:
                print(f"Error processing and saving combined dataset: {str(e)}")
                raise
        else:
            try:
                # Create new file
                new_df.to_csv(output_path, index=False)
                print(f"Created new dataset at {output_path} with {len(new_df)} records")
            except Exception as e:
                print(f"Error creating new CSV {output_path}: {str(e)}")
                raise
                
    except Exception as e:
        print(f"Fatal error in append_to_dataset for {output_path}: {str(e)}")
        print(traceback.format_exc())
        raise

if __name__ == "__main__":
    try:
        output_dir = 'sportradar/data/processed_data'
        debug_mode = False  # Set to False for full processing
        basic_df, advanced_df, advanced_with_formation_df = create_training_data('football_data.db', output_dir, debug_mode)
    except Exception as e:
        print(f"\nScript failed: {str(e)}") 