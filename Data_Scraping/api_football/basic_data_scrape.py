from collections import defaultdict
import requests
import json
import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# Utility to format datetime strings
def datetime_string_converter(raw_datetime):
    if raw_datetime:
        return str(raw_datetime)[:10]
    else:
        return None;

# Storage structures
scraped_data = []

# Load dict of leagues to scrape
with open('data/api_football/league_dict.json', 'r') as file:
    dict_of_scrapable_leagues = json.load(file)

# API setup
url = "https://v3.football.api-sports.io/"
api_key = os.getenv('API_FOOTBALL_KEY')
payload = {}
headers = {
    'x-rapidapi-key': api_key,
    'x-rapidapi-host': 'v3.football.api-sports.io'
}

##### Fetch data ########################################################################
# for country in dict_of_scrapable_leagues:
for country in dict_of_scrapable_leagues:
    print(f"Uploading {country}...")
    competition_list = dict_of_scrapable_leagues[country]

    for competition in competition_list:
        print(f"---- {competition['name']}")
        competition_id = competition['id']
        years = competition['years']

        for year in years:
            print(f"-------- {year}")
            try:
                # Get fixtures info
                fixtures_response = requests.get(url + f"fixtures?league={competition_id}&season={year}", headers=headers, data=payload)
                if fixtures_response.status_code != 200:
                    print(f"Failed to fetch fixtures for {competition_id} in {year}")
                    continue
                json_fixtures_response = fixtures_response.json()

                # Get season info
                season_info_response = requests.get(url + f"leagues?id={competition_id}&season={year}", headers=headers, data=payload)
                if season_info_response.status_code != 200:
                    print(f"Failed to fetch league info for {competition_id} in {year}")
                    continue
                json_season_info_response = season_info_response.json()

                # Extract season start and end dates
                season_start_date = json_season_info_response['response'][0]['seasons'][0]['start']
                season_end_date = json_season_info_response['response'][0]['seasons'][0]['end']
                
                for content in json_fixtures_response['response']:
                    match_id = content['fixture']['id']
                    start_time = content['fixture']['date']
                    clean_date = datetime_string_converter(start_time)
                    competition_name = competition['name']
                    round_info = content['league']['round']
                    match_status = content['fixture']['status']['short']
                    home_team_name = content['teams']['home']['name']
                    home_team_id = content['teams']['home']['id']
                    away_team_name = content['teams']['away']['name']
                    away_team_id = content['teams']['away']['id']
                    home_score = content['score']['fulltime']['home']
                    away_score = content['score']['fulltime']['away']

                    if home_score and away_score:
                        result = 'Draw' if home_score == away_score else 'Home Win' if home_score > away_score else 'Away Win';
                    else:
                        result = None
                    
                    
                    match_obj = {
                        'match_id': match_id,
                        'start_time': start_time,
                        'clean_date': clean_date,
                        'competition_id': competition_id,
                        'competition_name': competition_name,
                        'competition_country': country,
                        'competition_season_name': year,
                        'competition_season_id': f"{competition_id}_{year}",
                        'season_start_date': season_start_date,
                        'season_end_date': season_end_date,
                        'round_info': round_info,
                        'home_team_id': home_team_id,
                        'home_team_name': home_team_name,
                        'home_team_domestic_league_id': None,
                        'away_team_domestic_league_id': None,
                        'home_team_domestic_country': None,
                        'away_team_domestic_country': None,
                        'away_team_id': away_team_id,
                        'away_team_name': away_team_name,
                        'match_status': match_status,
                        'home_score': home_score,
                        'away_score': away_score,
                        'result': result,
                        'is_processed': 0
                    }

                    
                    scraped_data.append(match_obj)

            except Exception as e:
                print("------ PROCESSING FAILED -----")
                print(e)
                print("Fixtures Response:")
                print(fixtures_response, '\n')
                print("Season Info Response:")
                print(season_info_response, '\n\n')

########### Assign domestic leagues to matches #################################################

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
output_path = 'data/api_football/raw/basic_match_data.json'
with open(output_path, 'w') as file:
    json.dump(scraped_data, file, indent=4)
    print(f"Data saved to {output_path}")
