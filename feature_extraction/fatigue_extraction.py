# This file is for extracting time since last match and matches in last 30 days for each team in a match

from datetime import datetime, timedelta
import sqlite3
from helpers.database_helpers.dictionaries import dict_to_sqlite
from helpers.database_helpers.get_and_set_functions import get_from_matches
from helpers.form.form import get_last_n_matches_for_team


def extract_fatigue_features(conn, matches):
    """Extracts the time since last match and matches in last X days for X in [1,3,5,10,15,30]
    
    Args:
        conn (sqlite3.Connection): The database connection.
        matches (list): The list of matches to extract fatigue features from.
    """
    rest = matches[5000:] #first 5000 matches are used to establish k_draw_parameter and eta_home advantage in elo_extraction

    batch= []
    BATCH_SIZE = 3000

    for match in rest:
        match_id, start_time, home_team_id, away_team_id = match
        home_team_matches = get_last_n_matches_for_team(conn, home_team_id, start_time, 15)
        away_team_matches = get_last_n_matches_for_team(conn, away_team_id, start_time, 15)
        
        home_team_fatigue = calculate_match_history_features(home_team_matches, start_time)
        away_team_fatigue = calculate_match_history_features(away_team_matches, start_time)

        home_team_fatigue = {f'home_team_{key}': value for key, value in home_team_fatigue.items()}
        away_team_fatigue = {f'away_team_{key}': value for key, value in away_team_fatigue.items()}

        combined_fatigue = {**home_team_fatigue, **away_team_fatigue}
        combined_fatigue['match_id'] = match_id #so that we can join on match_id in load_data
        
        if combined_fatigue['home_team_time_since_last_match'] is None or combined_fatigue['away_team_time_since_last_match'] is None:
            print("Either home or away time since last match is None")
        else:
            batch.append((combined_fatigue))

        if len(batch) == BATCH_SIZE:
            print("Batch size reached, writing to database")
            dict_to_sqlite('api_football.db', 'fatigue_history', batch, batch_size=BATCH_SIZE)
            batch = []
    
    if batch:
        print("Writing remaining batch to database")
        dict_to_sqlite('api_football.db', 'fatigue_history', batch, batch_size=BATCH_SIZE)

    print("Fatigue features extracted successfully")

#LOGIC HELPER
def calculate_match_history_features(match_history, current_match_start_time):
    """
    Function that performs the logical calculations on the match history data.
    
    Parameters:
    match_history (list): List of match dictionaries containing historical matches
    current_match_start_time (str): Datetime string in format "2018-04-28T13:30:00+00:00" Used as a reference point for the calculations
    
    Returns:
    dict: Dictionary containing all calculated features
    """
    # Parse the current match start time
    current_match_datetime = datetime.strptime(current_match_start_time, "%Y-%m-%dT%H:%M:%S%z")
    
    # Initialize result dictionary
    result = {}
    
    # Sort match history by start_time (most recent first)
    sorted_history = sorted(match_history, 
                           key=lambda x: datetime.strptime(x['start_time'], "%Y-%m-%dT%H:%M:%S%z"), 
                           reverse=True)
    
    # Time since last match (in days)
    if sorted_history:
        last_match_time = datetime.strptime(sorted_history[0]['start_time'], "%Y-%m-%dT%H:%M:%S%z")
        result['days_since_last_match'] = (current_match_datetime - last_match_time).total_seconds() / (24 * 3600)
    else:
        result['days_since_last_match'] = None
    
    # Define the time windows to analyze
    time_windows = [1, 3, 5, 10, 15, 30]
    
    # Calculate features for each time window
    for days in time_windows:
        cutoff_date = current_match_datetime - timedelta(days=days)
        
        # Filter matches within the time window
        matches_in_window = [
            match for match in match_history 
            if datetime.strptime(match['start_time'], "%Y-%m-%dT%H:%M:%S%z") >= cutoff_date
        ]
        
        # Total matches in window
        result[f'matches_last_{days}_days'] = len(matches_in_window)
        
        # Home matches in window
        result[f'home_matches_last_{days}_days'] = sum(1 for match in matches_in_window if match['is_home'] == 1)
        
        # Away matches in window
        result[f'away_matches_last_{days}_days'] = sum(1 for match in matches_in_window if match['is_home'] == 0)
        
        # Intraleague matches in window
        result[f'intraleague_matches_last_{days}_days'] = sum(1 for match in matches_in_window if match['is_intraleague_match'] == 1)
        
        # Domestic cup matches in window
        result[f'domestic_cup_matches_last_{days}_days'] = sum(1 for match in matches_in_window if match['is_domestic_cup_match'] == 1)
        
        # Continental cup matches in window
        result[f'continental_cup_matches_last_{days}_days'] = sum(1 for match in matches_in_window if match['is_continental_cup_match'] == 1)
        
    return result

if __name__ == "__main__":
    conn = sqlite3.connect('api_football.db')
    matches = get_from_matches(conn, select_str='SELECT', columns=['match_id', 'start_time', 'home_team_id', 'away_team_id'], where_clause='home_score IS NOT NULL AND away_score IS NOT NULL AND is_processed = 0')
    extract_fatigue_features(conn,matches)
    pass