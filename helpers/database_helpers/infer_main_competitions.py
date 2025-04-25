import sqlite3
from collections import defaultdict
from helpers.database_helpers.get_and_set_functions import get_main_league_and_nation_data
from helpers.database_helpers.create_tables import create_team_main_competition_table

def count_competitions_per_year(matches):
    """Counts the number of competitions per year"""
    domestic_league_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(int)));
    for i, match in enumerate(matches):
        match_id, home_team_id, home_team_name, away_team_id, away_team_name, competition_season_id, season_start_date, season_end_date, competition_id, competition_name, competition_country = match

        # Split on comma and take first element
        season_start_year = season_start_date.split(',')[0]
        season_end_year = season_end_date.split(',')[0]
        combined_season_years = f"{season_start_year}_{season_end_year}"

        #A team never changes countries so we just count the occurunces of different countries for that team and take the most common one
        domestic_league_dict[home_team_id][competition_country] += 1;
        domestic_league_dict[away_team_id][competition_country] += 1;
    
        #Adds one to competition id for that season.
        domestic_league_dict[home_team_id][combined_season_years][competition_id] += 1;
        domestic_league_dict[away_team_id][combined_season_years][competition_id] += 1;

    return domestic_league_dict;

def get_main_league_per_season(conn):
    """Infer the main competition and country for each team"""
    main_league_and_nation_data = get_main_league_and_nation_data(conn)
    #These are all the matches that have been scraped

    domestic_league_dict = count_competitions_per_year(main_league_and_nation_data);

    for match in main_league_and_nation_data:
        match_id, home_team_id, home_team_name, away_team_id, away_team_name, competition_season_id, season_start_date, season_end_date, competition_id, competition_name, competition_country = match

        # Split on comma and take first element
        season_start_year = season_start_date.split(',')[0]
        season_end_year = season_end_date.split(',')[0]
        combined_season_years = f"{season_start_year}_{season_end_year}"

        home_team_all_competitions_dict = domestic_league_dict[home_team_id][combined_season_years];
        away_team_all_competitions_dict = domestic_league_dict[away_team_id][combined_season_years];

        home_team_country_dict = domestic_league_dict[home_team_id][competition_country];
        away_team_country_dict = domestic_league_dict[away_team_id][competition_country];

        home_team_domestic_league_id = max(home_team_all_competitions_dict, key=home_team_all_competitions_dict.get);
        away_team_domestic_league_id = max(away_team_all_competitions_dict, key=away_team_all_competitions_dict.get);

        home_team_domestic_country = max(home_team_country_dict, key=home_team_country_dict.get);
        away_team_domestic_country = max(away_team_country_dict, key=away_team_country_dict.get);

        update_match_domestic_league_and_country(conn, match_id, home_team_domestic_league_id, away_team_domestic_league_id, home_team_domestic_country, away_team_domestic_country)
    

def update_match_domestic_league_and_country(conn, match_id, home_league, away_league, home_country, away_country):
    query = """
    UPDATE matches
    SET 
        home_team_domestic_league_id = %s,
        away_team_domestic_league_id = %s,
        home_team_domestic_country = %s,
        away_team_domestic_country = %s
    WHERE match_id = %s
    """
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, (home_league, away_league, home_country, away_country, match_id))
        conn.commit()
    except Exception as e:
        print(f"Error updating match {match_id}: {str(e)}")
        conn.rollback()



if __name__ == "__main__":