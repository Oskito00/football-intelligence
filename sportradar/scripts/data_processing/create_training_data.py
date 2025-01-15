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
from team_processing import add_points_for_team, add_team_stats, calculate_match_importance, calculate_form, get_league_positions, get_stats_coverage, get_team_points, getH2h_stats, initialize_database, get_previous_matches


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
        
        # Connect to database and initialize
        conn = sqlite3.connect(db_path)
        print("Successfully connected to database")
        print("Initializing database...")
        initialize_database(conn)
        initialize_player_database(conn)
        print("Database initialization complete")

        # Get completed matches
        print("\nFetching completed matches...")
        matches_query = DEBUG_ENDED_MATCHES_QUERY if debug_mode else ENDED_MATCHES_QUERY
        matches_df = pd.read_sql_query(matches_query, conn)
        print(f"Found {len(matches_df)} completed matches")
        
        # Debug: Check team_stats table
        if debug_mode:
            print("\nChecking team_stats table...")
            stats_check = pd.read_sql_query(STATS_CHECK_QUERY, conn)
            print("Team stats summary:")
            print(stats_check)
        
        basic_data = []
        advanced_data = []
        total_matches = len(matches_df)
        
        for idx, match in matches_df.iterrows():
            try:
                # Process match stats
                add_team_stats(conn, match)
                average_home_stats, average_away_stats = calculate_form(conn, match)
                competition_id = match['competition_id']
                
                # Calculate match importance and update points
                match_importance = calculate_match_importance(conn, match)
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
                    'average_home_clean_sheets': average_home_stats['average_clean_sheets'],
                    'home_fatigue': average_home_stats.get('fatigue'),
                    'home_momentum': average_home_stats.get('momentum'),
                    'average_away_goals_scored': average_away_stats['average_goals_scored'],
                    'average_away_goals_conceded': average_away_stats['average_goals_conceded'],
                    'average_away_win_rate': average_away_stats['average_win_rate'],
                    'average_away_clean_sheets': average_away_stats['average_clean_sheets'],
                    'away_fatigue': average_away_stats.get('fatigue'),
                    'away_momentum': average_away_stats.get('momentum'),
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

                if (average_home_stats.get('has_advanced_stats') == 0 and average_away_stats.get('has_advanced_stats') == 0) and result['home_squad_strength'] is None and result['away_squad_strength'] is None:
                    basic_row['home_squad_strength'] = result['home_squad_strength']
                    basic_row['away_squad_strength'] = result['away_squad_strength']
                    basic_row['home_goals'] = match['home_goals']
                    basic_row['away_goals'] = match['away_goals']
                    basic_data.append(basic_row)

                
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
                print(f"Matches processed: {idx + 1} of {total_matches}")

            except Exception as e:
                print(f"\nError processing match {match['fixture_id']}: {str(e)}")
                if debug_mode:
                    raise
                continue
        
        # Save datasets
        basic_df = pd.DataFrame(basic_data)
        advanced_df = pd.DataFrame(advanced_data)
        
        # Save to files
        suffix = '_debug' if debug_mode else ''
        basic_output = os.path.join(output_dir, f'training_data_basic{suffix}.csv')
        advanced_output = os.path.join(output_dir, f'training_data_advanced{suffix}.csv')
        
        basic_df.to_csv(basic_output, index=False)
        advanced_df.to_csv(advanced_output, index=False)
        
        print(f"\nSaved basic dataset with {len(basic_df)} matches to {basic_output}")
        print(f"Saved advanced dataset with {len(advanced_df)} matches to {advanced_output}")
        
        return basic_df, advanced_df
        
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
        basic_df, advanced_df = create_training_data('football_data.db', output_dir, debug_mode)
    except Exception as e:
        print(f"\nScript failed: {str(e)}") 