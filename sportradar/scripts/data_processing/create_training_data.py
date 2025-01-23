import sqlite3
import os
from datetime import datetime
import pandas as pd

# Local imports
from constants import (
    PREVIOUS_MATCHES_QUERY,
    ENDED_MATCHES_QUERY,
    STATS_CHECK_QUERY,
    DEBUG_ENDED_MATCHES_QUERY
)
from player_stats import initialize_player_database, process_match_stats
from team_processing import add_points_for_team, add_team_stats, calculate_elo_rating, calculate_match_importance, calculate_form, get_league_positions, get_match_formations, get_stats_coverage, get_team_points, getH2h_stats, initialize_database, get_previous_matches, refined_categorize_formation


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

def create_training_data(db_path, output_dir, debug_mode=False):
    """Create both basic and advanced training datasets from match database"""
    print(f"\n=== Starting training data creation at {datetime.now()} ===")
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

        initialize_database(conn)
        initialize_player_database(conn)
        
        # # Get all processed matches once
        # processed_match_ids, processed_team_times = get_processed_matches(conn)
        # print(f"Found {len(processed_match_ids)} previously processed matches")
        
        # Get completed matches
        print("\nFetching completed matches...")
        matches_query = DEBUG_ENDED_MATCHES_QUERY if debug_mode else ENDED_MATCHES_QUERY
        matches_df = pd.read_sql_query(matches_query, conn)
        print(f"Found {len(matches_df)} completed matches")
        
        basic_data = []
        advanced_data = []
        advanced_data_with_formation = []
        total_matches = len(matches_df)
        processed_count = 0
        skipped_count = 0
        
        for idx, match in matches_df.iterrows():
            try:
                match_id = match['fixture_id']
                
                # # Fast lookup using sets
                # if (match_id in processed_match_ids or 
                #     (match['home_team'], match['start_time']) in processed_team_times or 
                #     (match['away_team'], match['start_time']) in processed_team_times):
                #     skipped_count += 1
                #     continue
                
                # Process match stats
                add_team_stats(conn, match)
                
                # Calculate form using pre-match ELO ratings
                average_home_stats, average_away_stats = calculate_form(conn, match)
                competition_id = match['competition_id']
                home_formation, away_formation = get_match_formations(match_id)
                print(f"Home formation: {home_formation}, Away formation: {away_formation}")

                # Now update ELO ratings based on match outcome
                match_importance = calculate_match_importance(conn, match)
                home_elo_rating, away_elo_rating = calculate_elo_rating(conn, match, match_importance)
                
                add_points_for_team(conn, match)

                # H2H Stats
                h2h_stats = getH2h_stats(conn, match['home_team_id'], match['away_team_id'], match['start_time'])
                
                # Skip this match if no h2h stats available
                if h2h_stats is None:
                    print(f"Skipping match {match['fixture_id']}: No head-to-head history")
                    continue

                try:
                    result = process_match_stats(conn, match['fixture_id'], match['home_team_id'], 
                                               match['away_team_id'], match['start_time'], 
                                               match['home_team'], match['away_team'])
                    print(f"\nProcessed {result['processed_count']} players for match {match['fixture_id']}")
                    print(f"Home Team vs Away Team: {match['home_team']} vs {match['away_team']}")
                                    
                except ValueError as error:
                    print(f"Skipping player stats for match {match['fixture_id']}: {str(error)}")
                    continue  # Skip this match if player stats processing fails
                except Exception as error:
                    print(f"Error processing player stats for match {match['fixture_id']}: {str(error)}")
                    if debug_mode:
                        raise
                    continue

                # Create basic row data only if we have h2h stats
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
                    'away_h2h_avg_points': h2h_stats[match['away_team_id']]['avg_points'],
                }

                # # Add referee_id if it exists and is not null
                # if 'referee_id' in match and pd.notna(match['referee_id']):
                #     basic_row['referee_id'] = match['referee_id']
                # else:
                #     print(f"No referee data for match {match['fixture_id']}")

                if home_elo_rating is not None and away_elo_rating is not None:
                    basic_row['home_elo_rating'] = home_elo_rating
                    basic_row['away_elo_rating'] = away_elo_rating

                if (average_home_stats.get('has_advanced_stats') == 0 and average_away_stats.get('has_advanced_stats') == 0) and result['home_squad_strength'] is not None and result['away_squad_strength'] is not None:
                    basic_row['home_squad_strength'] = result['home_squad_strength']
                    basic_row['away_squad_strength'] = result['away_squad_strength']
                    basic_row['home_goals'] = match['home_goals']
                    basic_row['away_goals'] = match['away_goals']
                    basic_data.append(basic_row)

                if home_formation is not None and away_formation is not None and average_home_stats.get('has_advanced_stats') == 1 and average_away_stats.get('has_advanced_stats') == 1 and result['home_squad_strength'] is not None and result['away_squad_strength'] is not None:
                    home_formation_category = refined_categorize_formation(home_formation)
                    away_formation_category = refined_categorize_formation(away_formation)
                    advanced_row_with_formation = basic_row.copy()
                    advanced_row_with_formation.update({
                        'home_pass_effectiveness': round(average_home_stats['pass_effectiveness'], 2),
                        'home_shot_accuracy': round(average_home_stats['shot_accuracy'], 2),
                        'home_conversion_rate': round(average_home_stats['conversion_rate'], 2),
                        'home_defensive_success': round(average_home_stats['defensive_success'], 2),
                        'away_pass_effectiveness': round(average_away_stats['pass_effectiveness'], 2),
                        'away_shot_accuracy': round(average_away_stats['shot_accuracy'], 2),
                        'away_conversion_rate': round(average_away_stats['conversion_rate'], 2),
                        'away_defensive_success': round(average_away_stats['defensive_success'], 2),
                        'home_squad_strength': round(result['home_squad_strength'], 2),
                        'away_squad_strength': round(result['away_squad_strength'], 2),
                        'home_formation': home_formation_category,
                        'away_formation': away_formation_category,
                        'home_goals': match['home_goals'],
                        'away_goals': match['away_goals'],
                    })
                    advanced_data_with_formation.append(advanced_row_with_formation)
                
                # Process advanced stats if available
                if average_home_stats.get('has_advanced_stats') == 1 and average_away_stats.get('has_advanced_stats') == 1 and result['home_squad_strength'] is not None and result['away_squad_strength'] is not None:


                    advanced_row = basic_row.copy()
                    advanced_row.update({ #TODO: Check if rounding here increases time complexity
                        'home_pass_effectiveness': round(average_home_stats['pass_effectiveness'], 2),
                        'home_shot_accuracy': round(average_home_stats['shot_accuracy'], 2),
                        'home_conversion_rate': round(average_home_stats['conversion_rate'], 2),
                        'home_defensive_success': round(average_home_stats['defensive_success'], 2),
                        'away_pass_effectiveness': round(average_away_stats['pass_effectiveness'], 2),
                        'away_shot_accuracy': round(average_away_stats['shot_accuracy'], 2),
                        'away_conversion_rate': round(average_away_stats['conversion_rate'], 2),
                        'away_defensive_success': round(average_away_stats['defensive_success'], 2),
                        'home_squad_strength': round(result['home_squad_strength'], 2),
                        'away_squad_strength': round(result['away_squad_strength'], 2),
                        'home_goals': match['home_goals'],
                        'away_goals': match['away_goals'],
                    })
                    advanced_data.append(advanced_row)

                conn.commit()
                processed_count += 1
                if processed_count % 100 == 0:  # Print progress less frequently
                    print(f"Matches processed: {processed_count} (Total: {idx + 1} of {total_matches}, Skipped: {skipped_count})")

            except Exception as e:
                print(f"\nError processing match {match['fixture_id']}: {str(e)}")
                if debug_mode:
                    raise
                continue
        
        # Save datasets
        basic_df = pd.DataFrame(basic_data)
        advanced_df = pd.DataFrame(advanced_data)
        advanced_with_formation_df = pd.DataFrame(advanced_data_with_formation)
        
        print(f"\nDataFrame sizes before saving:")
        print(f"Basic data: {len(basic_df)} rows, {len(basic_df.columns)} columns")
        print(f"Advanced data: {len(advanced_df)} rows, {len(advanced_df.columns)} columns")
        print(f"Advanced with formation: {len(advanced_with_formation_df)} rows, {len(advanced_with_formation_df.columns)} columns")
        
        # Save to files
        basic_output = os.path.join(output_dir, f'training_data_basic.csv')
        advanced_output = os.path.join(output_dir, f'training_data_advanced.csv')
        advanced_output_with_formation = os.path.join(output_dir, f'training_data_advanced_with_formation.csv')
        
        new_basic_matches = len(basic_df)
        new_advanced_matches = len(advanced_df)
        new_advanced_with_formation_matches = len(advanced_with_formation_df)
        
        # Append to existing files if they exist
        if os.path.exists(basic_output) and new_basic_matches > 0:
            existing_basic_df = pd.read_csv(basic_output)
            basic_df = pd.concat([existing_basic_df, basic_df], ignore_index=True)
            print(f"\nAppended {new_basic_matches} new matches to existing basic dataset")
            
        if os.path.exists(advanced_output) and new_advanced_matches > 0:
            existing_advanced_df = pd.read_csv(advanced_output)
            advanced_df = pd.concat([existing_advanced_df, advanced_df], ignore_index=True)
            print(f"Appended {new_advanced_matches} new matches to existing advanced dataset")
            
        if os.path.exists(advanced_output_with_formation) and new_advanced_with_formation_matches > 0:
            existing_advanced_with_formation_df = pd.read_csv(advanced_output_with_formation)
            advanced_with_formation_df = pd.concat([existing_advanced_with_formation_df, advanced_with_formation_df], ignore_index=True)
            print(f"Appended {new_advanced_with_formation_matches} new matches to existing advanced dataset with formation")
            
        # Save the updated dataframes
        if len(basic_df) > 0:
            basic_df.to_csv(basic_output, index=False)
        if len(advanced_df) > 0:
            advanced_df.to_csv(advanced_output, index=False)
            
        if len(advanced_with_formation_df) > 0:
            advanced_with_formation_df.to_csv(advanced_output_with_formation, index=False)
        
        print(f"\nProcessing summary:")
        print(f"Total matches found: {total_matches}")
        print(f"New matches processed: {processed_count}")
        print(f"Matches skipped (already processed): {skipped_count}")
        
        if new_basic_matches == 0 and new_advanced_matches == 0:
            print("\nNo new matches to add to the datasets")
        else:
            print(f"\nTotal matches in basic dataset: {len(basic_df)}")
            print(f"Total matches in advanced dataset: {len(advanced_df)}")
            print(f"Total matches in advanced dataset with formation: {len(advanced_with_formation_df)}")
        
        return basic_df, advanced_df, advanced_with_formation_df
        
    except Exception as e:
        print(f"\nFatal error: {str(e)}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()
            print("\nDatabase connection closed")

if __name__ == "__main__":
    try:
        output_dir = 'sportradar/data/processed_data'
        debug_mode = False  # Set to False for full processing
        basic_df, advanced_df, advanced_with_formation_df = create_training_data('football_data.db', output_dir, debug_mode)
    except Exception as e:
        print(f"\nScript failed: {str(e)}") 