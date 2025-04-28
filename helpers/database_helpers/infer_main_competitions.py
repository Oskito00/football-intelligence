import sqlite3
from collections import defaultdict
from helpers.database_helpers.get_and_set_functions import get_main_league_and_nation_data
from helpers.database_helpers.create_tables import create_team_main_competition_table

def count_competitions_per_year(matches):
    """Counts the number of competitions per year"""
    team_dict = defaultdict(lambda: {
        'seasons': defaultdict(lambda: defaultdict(int)),
        'countries': defaultdict(int)
    })

    for match in matches:
        # Unpack match data
        (match_id, home_team_id, home_team_name, 
         away_team_id, away_team_name, competition_season_id,
         season_start_date, season_end_date, competition_id,
         competition_name, competition_country) = match

        # Process season years
        season_start_year = season_start_date.split(',')[0].strip()
        season_end_year = season_end_date.split(',')[0].strip()
        combined_season_years = f"{season_start_year}_{season_end_year}"

        # Update home team data
        team_dict[home_team_id]['seasons'][combined_season_years][competition_id] += 1
        team_dict[home_team_id]['countries'][competition_country] += 1

        # Update away team data
        team_dict[away_team_id]['seasons'][combined_season_years][competition_id] += 1
        team_dict[away_team_id]['countries'][competition_country] += 1

    return team_dict

def get_main_league_per_season(conn):
    """Infer the main competition and country for each team"""
    main_league_and_nation_data = get_main_league_and_nation_data(conn)
    #These are all the matches that have been scraped

    domestic_league_dict = count_competitions_per_year(main_league_and_nation_data);

    update_batch = []
    BATCH_SIZE = 1000  # Adjust based on memory

    for match in main_league_and_nation_data:
        match_id, home_team_id, home_team_name, away_team_id, away_team_name, competition_season_id, season_start_date, season_end_date, competition_id, competition_name, competition_country = match

        # Split on comma and take first element
        season_start_year = season_start_date.split(',')[0]
        season_end_year = season_end_date.split(',')[0]
        combined_season_years = f"{season_start_year}_{season_end_year}"

        home_team_all_competitions_dict = domestic_league_dict[home_team_id]['seasons'][combined_season_years];
        away_team_all_competitions_dict = domestic_league_dict[away_team_id]['seasons'][combined_season_years];

        home_team_country_dict = domestic_league_dict[home_team_id]['countries'];
        away_team_country_dict = domestic_league_dict[away_team_id]['countries'];

        home_team_domestic_league_id = max(home_team_all_competitions_dict, key=home_team_all_competitions_dict.get);
        away_team_domestic_league_id = max(away_team_all_competitions_dict, key=away_team_all_competitions_dict.get);

        home_team_domestic_country = max(home_team_country_dict, key=home_team_country_dict.get);
        away_team_domestic_country = max(away_team_country_dict, key=away_team_country_dict.get);

        # Collect update data instead of immediate update
        update_data = (
            home_team_domestic_league_id,
            away_team_domestic_league_id,
            home_team_domestic_country,
            away_team_domestic_country,
            match_id
        )
        update_batch.append(update_data)

        # Batch update when threshold reached
        if len(update_batch) >= BATCH_SIZE:
            batch_update_domestic_info(conn, update_batch)
            update_batch = []

    # Update remaining records
    if update_batch:
        batch_update_domestic_info(conn, update_batch)

def batch_update_domestic_info(conn, update_data):
    """Update multiple matches in one query
    update_data: List of tuples (home_league, away_league, home_country, away_country, match_id)
    """
    if not update_data:
        return

    query = """
        UPDATE matches
        SET home_team_domestic_league_id = ?,
            away_team_domestic_league_id = ?,
            home_team_domestic_country = ?,
            away_team_domestic_country = ?
        WHERE match_id = ?
    """
    
    try:
        cursor = conn.cursor()
        cursor.executemany(query, update_data)
        conn.commit()
        print(f"Updated {len(update_data)} matches")
    except sqlite3.Error as e:
        print(f"Batch update failed: {e}")
        conn.rollback()
    finally:
        cursor.close()

if __name__ == "__main__":
    conn = sqlite3.connect('v2db.sqlite')
    get_main_league_per_season(conn)
    conn.close()