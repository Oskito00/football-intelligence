from datetime import datetime, timedelta

def calculate_match_history_features(match_history, current_match_start_time):
    """
    Calculate various features based on match history.
    
    Parameters:
    match_history (list): List of match dictionaries containing historical matches
    current_match_start_time (str): Datetime string in format "2018-04-28T13:30:00+00:00"
    
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