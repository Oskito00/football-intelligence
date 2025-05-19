# This file is for extracting time since last match and matches in last 30 days for each team in a match

import sqlite3
from helpers.database_helpers.dictionary_helpers import dict_to_sqlite
from helpers.database_helpers.get_and_set_functions import get_all_matches, get_all_matches_for_fatigue
from helpers.fatigue.fatigue import calculate_match_history_features
from helpers.form.form import get_last_n_matches_for_team


def extract_fatigue_features(conn, matches):
    first_5000 = matches[:5000]
    rest = matches[5000:]

    batch= []
    BATCH_SIZE = 3000

    for match in rest:
        match_id, start_time, home_team_id, away_team_id = match
        home_team_matches = get_last_n_matches_for_team(conn, home_team_id, start_time, 15)
        away_team_matches = get_last_n_matches_for_team(conn, away_team_id, start_time, 15)
        
        home_team_fatigue = calculate_match_history_features(home_team_matches, start_time)
        away_team_fatigue = calculate_match_history_features(away_team_matches, start_time)

        #add 'home_team' prefix to fatigue features
        home_team_fatigue = {f'home_team_{key}': value for key, value in home_team_fatigue.items()}
        away_team_fatigue = {f'away_team_{key}': value for key, value in away_team_fatigue.items()}

        combined_fatigue = {**home_team_fatigue, **away_team_fatigue}
        combined_fatigue['match_id'] = match_id
        
        if combined_fatigue['home_team_time_since_last_match'] == None or combined_fatigue['away_team_time_since_last_match'] == None:
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

if __name__ == "__main__":
    conn = sqlite3.connect('api_football.db')
    matches = get_all_matches_for_fatigue(conn)
    extract_fatigue_features(conn,matches)
    pass