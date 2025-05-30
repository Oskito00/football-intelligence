

from collections import defaultdict
import psycopg2
import requests
import json
import os
from config import get_config
from helpers.formatting.time import datetime_string_converter

base_url = "https://v3.football.api-sports.io/"

headers = {
    'x-rapidapi-key': os.getenv('API_FOOTBALL_KEY'),
    'x-rapidapi-host': 'v3.football.api-sports.io'
}
payload = {}

config = get_config()

conn = psycopg2.connect(
    host=config.DB_HOST,
    database=config.DB_NAME,
    user=config.DB_USER,
    password=config.DB_PASSWORD
)

select_query = "SELECT id, years FROM leagues"

scraped_data = []

with conn.cursor() as cursor:
    cursor.execute(select_query)
    leagues = cursor.fetchall()

    for league in leagues[:1]:
        print(f"---- {league[0]}")
        competition_id = league[0]
        years = league[1]

        for year in years[:1]:
            print(f"-------- {year}")
            try:
                # Get fixtures info
                fixtures_response = requests.get(base_url + f"fixtures?league={competition_id}&season={year}", headers=headers, data=payload)
                if fixtures_response.status_code != 200:
                    print(f"Failed to fetch fixtures for {competition_id} in {year}")
                    continue
                json_fixtures_response = fixtures_response.json()

                # Get season info
                season_info_response = requests.get(base_url + f"leagues?id={competition_id}&season={year}", headers=headers, data=payload)
                if season_info_response.status_code != 200:
                    print(f"Failed to fetch league info for {competition_id} in {year}")
                    continue
                json_season_info_response = season_info_response.json()

                season_info = json_season_info_response['response']
                season_fixtures = json_fixtures_response['response']

                result = None
                print(season_info)

                print("11111")
                season_start_date = season_info[0]['seasons'][0]['start']
                season_end_date = season_info[0]['seasons'][0]['end']
                print("Start DATE = True" if season_start_date else "False")
                print("End DATE = True" if season_end_date else "False")

                for content in season_fixtures:
                    print(content)

                    home_score = content['score']['fulltime'].get('home')
                    away_score = content['score']['fulltime'].get('away')

                    print("Home Score = True" if home_score else "False")
                    print("Away Score = True" if away_score else "False")

                    #Extract result
                    if home_score and away_score:
                        result = 'Draw' if home_score == away_score else 'Home Win' if home_score > away_score else 'Away Win';
                    else:
                        result = None
                    
                    print("Result = True" if result else "False")

                    match_data = {
                        'match_id': content['fixture']['id'],
                        'start_time': content['fixture']['date'],
                        'clean_date': datetime_string_converter(content['fixture']['date']),
                        'competition_name': season_info[0]['league']['name'],
                        'competition_country': season_info[0]['country'],
                        'competition_season_name': season_info[0]['season'],
                        'competition_season_id': f"{competition_id}_{year}",
                        'season_start_date': season_start_date,
                        'season_end_date': season_end_date,
                        'round_info': content['league']['round'],
                        'home_team_id': content['teams']['home']['id'],
                        'home_team_name': content['teams']['home']['name'],
                        'home_team_domestic_league_id': None,
                        'away_team_domestic_league_id': None,
                        'home_team_domestic_country': None,
                        'away_team_domestic_country': None,
                        'away_team_id': content['teams']['away']['id'],
                        'away_team_name': content['teams']['away']['name'],
                        'match_status': content['fixture']['status']['short'],
                        'home_score': home_score,
                        'away_score': away_score,
                        'result': result,
                        'is_processed': 0
                    }
                    print("Match Data = True" if match_data else "False")
                    scraped_data.append(match_data)

            except Exception as e:
                print("------ PROCESSING FAILED -----")
                print(e)
                print("Fixtures Response:")
                print(fixtures_response, '\n')
                print("Season Info Response:")
                print(season_info_response, '\n\n')

########### Assign domestic leagues to matches #################################################


print("Getting to here")
domestic_league_dict = defaultdict(lambda: {
    'seasons': defaultdict(lambda: defaultdict(int)),
    'countries': defaultdict(int)
})


for i, match in enumerate(scraped_data):

    year = match['competition_season_name']
    home_team_id = match['home_team_id']
    away_team_id = match['away_team_id']
    competition_id = match['competition_id']
    country = match['competition_country']

    #A team never changes countries so we just count the occurunces of different countries for that team and take the most common one
    domestic_league_dict[home_team_id]['countries'][country] += 1
    domestic_league_dict[away_team_id]['countries'][country] += 1
    
    domestic_league_dict[home_team_id]['seasons'][year][competition_id] += 1
    domestic_league_dict[away_team_id]['seasons'][year][competition_id] += 1

       
for i, match in enumerate(scraped_data):

    year = match['competition_season_name']
    home_team_id = match['home_team_id']
    away_team_id = match['away_team_id']

    home_team_all_competitions_dict = domestic_league_dict[home_team_id]['seasons'][year]
    away_team_all_competitions_dict = domestic_league_dict[away_team_id]['seasons'][year]

    home_team_country_dict = domestic_league_dict[home_team_id]['countries']
    away_team_country_dict = domestic_league_dict[away_team_id]['countries']

    home_team_domestic_league = max(home_team_all_competitions_dict, key=home_team_all_competitions_dict.get)
    away_team_domestic_league = max(away_team_all_competitions_dict, key=away_team_all_competitions_dict.get)

    home_team_domestic_country = max(home_team_country_dict, key=home_team_country_dict.get)
    away_team_domestic_country = max(away_team_country_dict, key=away_team_country_dict.get)

    scraped_data[i]['home_team_domestic_league_id'] = home_team_domestic_league
    scraped_data[i]['away_team_domestic_league_id'] = away_team_domestic_league

    scraped_data[i]['home_team_domestic_country'] = home_team_domestic_country
    scraped_data[i]['away_team_domestic_country'] = away_team_domestic_country


######### Save to JSON file ###################################################################
output_path = 'data/api_football/raw/basic_match_data3.json'
with open(output_path, 'w') as file:
    json.dump(scraped_data, file, indent=4)
    print(f"Data saved to {output_path}")
