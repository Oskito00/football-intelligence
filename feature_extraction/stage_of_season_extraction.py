import sqlite3
from helpers.database_helpers.dictionary_helpers import dict_to_sqlite
from helpers.database_helpers.get_and_set_functions import get_all_stage_of_season
from datetime import datetime
import time

def extract_stage_of_season(matches):
    function_start_time = time.time()
    first_5000 = matches[:5000]
    rest = matches[5000:]

    batch=[]
    BATCH_SIZE = 3000
    
    for match in rest:
        match_id, start_time, season_start_date, season_end_date = match
        
        stage_of_season = calculate_stage_of_season(start_time, season_start_date, season_end_date)
        stage_of_season_category = get_season_phase(stage_of_season)
        dict = {
            'match_id': match_id,
            'start_time': start_time,
            'season_start_date': season_start_date,
            'season_end_date': season_end_date,
            'stage_of_season': stage_of_season,
            'stage_of_season_category': stage_of_season_category
        }

        batch.append(dict)

        if len(batch) == BATCH_SIZE:
            dict_to_sqlite('api_football.db', 'stage_of_season_history', batch)
            batch = []

    if batch:
        dict_to_sqlite('api_football.db', 'stage_of_season_history', batch)

    function_end_time = time.time()
    print(f"Function took {function_end_time - function_start_time} seconds to run")


#Helper function to calculate the stage of season normalised between 0 and 1
def calculate_stage_of_season(start_time, season_start_date, season_end_date):
    """
    Helper function to calculate the stage of season normalized between 0 and 1
    
    Parameters:
    start_time (datetime or str): Match start time
    season_start_date (datetime or str): Season start date
    season_end_date (datetime or str): Season end date
    
    Returns:
    float: Normalized position in season (0 = start, 1 = end)
    """
    # Convert strings to datetime objects if needed
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    if isinstance(season_start_date, str):
        # Handle date-only strings by adding time component
        season_start_date = datetime.fromisoformat(season_start_date + 'T00:00:00+00:00')
    if isinstance(season_end_date, str):
        season_end_date = datetime.fromisoformat(season_end_date + 'T00:00:00+00:00')
    
    # Calculate days from season start
    days_from_season_start = (start_time - season_start_date).total_seconds() / (24 * 3600)
    
    # Calculate total season length in days
    season_length_days = (season_end_date - season_start_date).total_seconds() / (24 * 3600)
    # Calculate normalized position in season (clamped between 0 and 1)
    if season_length_days > 0:  # Prevent division by zero
        return max(0.0, min(1.0, days_from_season_start / season_length_days))
    else:
        return 0.0  # Default if season length is invalid

def get_season_phase(season_progress):
    """
    Convert numerical season progress to categorical phase
    
    Parameters:
    season_progress (float): Normalized position in season (0 to 1)
    
    Returns:
    str: Season phase category
    """
    if season_progress < 0.1:
        return 'Early Season (0-10%)'
    elif season_progress < 0.3:
        return 'Early-Mid Season (10-30%)'
    elif season_progress < 0.7:
        return 'Mid Season (30-70%)'
    elif season_progress < 0.9:
        return 'Mid-Late Season (70-90%)'
    else:
        return 'Late Season (90-100%)'

if __name__ == "__main__":
    conn = sqlite3.connect('api_football.db')
    matches = get_all_stage_of_season(conn)
    extract_stage_of_season(matches)
