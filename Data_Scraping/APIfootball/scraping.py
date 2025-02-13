
import requests;
import json;

def datetime_string_converter(raw_datetime):
    return str(raw_datetime)[:10]

scraped_data = []

with open('C:/Users/Will Boyd/InBETments Predictor/Data/APIfootball/league_list.json', 'r') as file:
    season_scrape_info = json.load(file);

url = "https://v3.football.api-sports.io/fixtures?";
api_key = "57199d6a3f17fa2348e9bb3eab7daf42";
payload={}
headers = {
  'x-rapidapi-key': api_key,
  'x-rapidapi-host': 'v3.football.api-sports.io'
}

for country in season_scrape_info:
    print(f"Uploading {country}...")
    league_list = season_scrape_info[country];
    for league in league_list:
        print(f"---- {league['name']}")
        league_id = league['id'];
        years = league['years']
        for year in years:
          print(f"-------- {year}")
          response = requests.request("GET", url+f"league={league_id}&season={year}", headers=headers, data=payload)
          json_response = response.json()

          for content in json_response['response']:
            match_id = content['fixture']['id'];
            country = country;
            league_name = league['name'];
            season_year = year
            league_id = league_id;
            clean_date = datetime_string_converter(content['fixture']['date'])
            home_team = content['teams']['home']['name']
            home_team_id = content['teams']['home']['id']
            away_team = content['teams']['away']['name']
            away_team_id = content['teams']['away']['id']
            home_score = content['score']['fulltime']['home']
            away_score = content['score']['fulltime']['away']

            match_obj = {
                'match_id': match_id,
                'country': country,
                'league_name': league_name,
                'season_year': season_year,
                'league_id': league_id,
                'clean_date': clean_date,
                'home_team': home_team,
                'home_team_id': home_team_id,
                'away_team': away_team,
                'away_team_id': away_team_id,
                'home_score': home_score,
                'away_score': away_score
            }

            scraped_data.append(match_obj);

### Creating a master json file with all clean, useful data
clean_data_json = json.dumps(scraped_data, indent=4)

with open('C:/Users/Will Boyd/InBETments Predictor/Data/APIfootball/clean_data.json', 'w') as file:
    file.write(clean_data_json)
    print("Data saved to Data/APIfootbal/clean_data.json")
        