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
domestic_leagues = defaultdict(lambda: defaultdict(str))
scraped_data = []

# Load dict of leagues to scrape
with open('C:/Users/Will Boyd/InBETments Predictor/Data/APIfootball/league_dict.json', 'r') as file:
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
for country in dict_of_scrapable_leagues:
    print(f"Uploading {country}...")
    competition_list = dict_of_scrapable_leagues[country]

    for competition in competition_list:
        print(f"---- {competition['name']}")
        competition_id = competition['id']
        years = competition['years']

        for year in years:
            print(f"-------- {year}")
            
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
                clean_date = datetime_string_converter(content['fixture']['date'])
                competition_name = competition['name']
                round_info = content['league']['round']
                match_status = content['fixture']['status']['short']
                home_team_name = content['teams']['home']['name']
                home_team_id = content['teams']['home']['id']
                away_team_name = content['teams']['away']['name']
                away_team_id = content['teams']['away']['id']
                home_score = content['score']['fulltime']['home']
                away_score = content['score']['fulltime']['away']

                try:
                    home_win = int(home_score > away_score);
                    away_win = int(away_score > home_score);
                    draw = int(home_score == away_score);
                except TypeError:
                    home_win = None;
                    away_win = None;
                    draw = None;
                
                
                match_obj = {
                    'match_id': match_id,
                    'match_date': clean_date,
                    'competition_id': competition_id,
                    'competition_name': competition_name,
                    'competition_country': country,
                    'competition_season_name': year,
                    'season_start_date': season_start_date,
                    'season_end_date': season_end_date,
                    'round_info': round_info,
                    'home_team_id': home_team_id,
                    'home_team_name': home_team_name,
                    'home_team_domestic_league': None,
                    'away_team_domestic_league': None,
                    'away_team_id': away_team_id,
                    'away_team_name': away_team_name,
                    'home_score': home_score,
                    'away_score': away_score,
                    'home_win': home_win,
                    'away_win': away_win,
                    'draw': draw
                }
                
                # If match is part of the regular season, mark team domestic league
                if round_info.startswith("Regular Season"):
                    for team in [home_team_id, away_team_id]:
                        domestic_leagues[team][year] = competition_id

                
                scraped_data.append(match_obj)


########### Assign domestic leagues to matches #################################################
def add_domestic_leagues(scraped_data, domestic_leagues):
    for i, match in enumerate(scraped_data):
        home_leagues = domestic_leagues.get(match['home_team_id'], {})
        away_leagues = domestic_leagues.get(match['away_team_id'], {})
        season = match['competition_season_name']

        scraped_data[i]['home_team_domestic_league'] = home_leagues.get(season, None)
        scraped_data[i]['away_team_domestic_league'] = away_leagues.get(season, None)
    return 0

add_domestic_leagues(scraped_data, domestic_leagues)

######### Save to JSON file ###################################################################
output_path = 'C:/Users/Will Boyd/InBETments Predictor/Data/APIfootball/basic_raw_match_data.json'
with open(output_path, 'w') as file:
    json.dump(scraped_data, file, indent=4)
    print(f"Data saved to {output_path}")
   