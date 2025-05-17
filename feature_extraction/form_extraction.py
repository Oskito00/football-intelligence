from asyncio import sleep
import time
import sqlite3
from helpers.database_helpers.dict_to_sqlite import dict_to_sqlite
from helpers.database_helpers.form_history import combine_stats
from helpers.form.form import calculate_form_stats_for_multiple_ns, enrich_matches_data_with_elo_ratings, get_last_n_matches_for_team, get_elo_ratings_for_multiple_matches
from helpers.database_helpers.get_and_set_functions import get_all_matches

def form_extraction(matches):
    conn = sqlite3.connect('v2db.sqlite')
    n = [1, 3, 5, 10, 20]

    function_start_time = time.time()

    #Always ignore the first 5000 matches for elo parameter tuning
    first_5000 = matches[:5000]
    rest = matches[5000:]
    remaining_matches = len(rest)

    # Ignore first 1000 matches for parameter tuning as in all the other processing files.
    batch = []
    BATCH_SIZE = 3000  # Tune based on memory
    
    for match in rest:
        match_id, start_time, competition_id, competition_name, competition_country, home_team_id, home_team_name, away_team_id, away_team_name, \
        home_score, away_score, home_main_comp_id, home_main_comp_country, \
        away_main_comp_id, away_main_comp_country = match

        print("Running Form Extraction for match: ", match_id)

        home_matches = get_last_n_matches_for_team(conn, home_team_id, start_time, 50)
        away_matches = get_last_n_matches_for_team(conn, away_team_id, start_time, 50)

        home_elo_ratings = get_elo_ratings_for_multiple_matches(conn, home_matches, home_team_id)
        away_elo_ratings = get_elo_ratings_for_multiple_matches(conn, away_matches, away_team_id)

        home_matches_and_elo_ratings = enrich_matches_data_with_elo_ratings(home_matches,home_elo_ratings)
        away_matches_and_elo_ratings = enrich_matches_data_with_elo_ratings(away_matches,away_elo_ratings)

        home_stats = calculate_form_stats_for_multiple_ns(home_matches_and_elo_ratings, n)
        away_stats = calculate_form_stats_for_multiple_ns(away_matches_and_elo_ratings, n)

        combined_stats = combine_stats(match_id, home_stats, away_stats)
        batch.append(combined_stats)
        
        if len(batch) >= BATCH_SIZE:
            print("Processing batch of size: ", len(batch))
            dict_to_sqlite('api_football.db', 'form_history', batch)
            remaining_matches -= BATCH_SIZE
            print("Matches remaining: ", remaining_matches)
            batch = []
    # Process remaining items
    if batch:
        print("Processing remaining items of size: ", len(batch))
        dict_to_sqlite('api_football.db', 'form_history', batch)

    function_end_time = time.time()
    print(f"Function took {function_end_time - function_start_time} seconds to run")

if __name__ == "__main__":
    conn = sqlite3.connect('api_football.db')
    matches = get_all_matches(conn)
    form_extraction(matches)






