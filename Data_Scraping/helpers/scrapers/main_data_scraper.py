import json
import os
from collections import defaultdict
from psycopg2.extras import execute_batch

from data_scraping.helpers.requests import fetch_with_retry
from utils.formatting.time import datetime_string_converter


base_url = "https://v3.football.api-sports.io/"
headers = {
    'x-rapidapi-key': os.getenv('API_FOOTBALL_KEY'),
    'x-rapidapi-host': 'v3.football.api-sports.io'
}
payload = {}

def scrape_matches_from_api(leagues, latest_only=False):
    scraped_data = []

    for i, league in enumerate(leagues):
        print(f"----- Processing League {league[0]}\n League {i} of {len(leagues)}------")
        competition_id = league[0]
        years = league[1]
        current_season = league[2]

        target_years = [current_season] if latest_only else years
        for year in target_years:
            print(f"-------- Processing Year {year} --------")
            try:
                fixtures_url = base_url + f"fixtures?league={competition_id}&season={year}"
                json_fixtures_response = fetch_with_retry(fixtures_url, headers, payload)
                if json_fixtures_response is None:
                    print(f"No fixture data for league {competition_id}, year {year}")
                    continue

                season_info_url = base_url + f"leagues?id={competition_id}&season={year}"
                json_season_info_response = fetch_with_retry(season_info_url, headers, payload)
                if json_season_info_response is None:
                    print(f"No season info for league {competition_id}, year {year}")
                    continue

                season_info = json_season_info_response['response']
                season_fixtures = json_fixtures_response['response']
                season_start_date = season_info[0]['seasons'][0]['start']
                season_end_date = season_info[0]['seasons'][0]['end']

                for content in season_fixtures:
                    home_score = content['score']['fulltime'].get('home')
                    away_score = content['score']['fulltime'].get('away')

                    result = None
                    if home_score is not None and away_score is not None:
                        result = 'Draw' if home_score == away_score else 'Home Win' if home_score > away_score else 'Away Win'

                    match_data = {
                        'match_id': content['fixture']['id'],
                        'start_time': content['fixture']['date'],
                        'clean_date': datetime_string_converter(content['fixture']['date']),
                        'competition_name': season_info[0]['league']['name'],
                        'competition_id': competition_id,
                        'competition_country': season_info[0]['country']['name'],
                        'competition_season_name': f"{season_info[0]['league']['name']}_{year}",
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
                        'all_fixture_data': json.dumps(content),
                        'all_season_info': json.dumps(season_info),
                        'home_team_formation': None,
                        'away_team_formation': None,
                        'home_team_lineup': None,
                        'away_team_lineup': None,
                        'attempted_formation_scrape': False,
                        'is_current_season': season_info[0]['seasons'][0]['current'],
                        'has_odds': season_info[0]['seasons'][0]['coverage']['odds'],
                        'has_players': season_info[0]['seasons'][0]['coverage']['players'],
                        'has_lineups': season_info[0]['seasons'][0]['coverage']['fixtures']['lineups'],
                        'has_events': season_info[0]['seasons'][0]['coverage']['fixtures']['events'],
                        'has_statistics_players': season_info[0]['seasons'][0]['coverage']['fixtures']['statistics_players'],
                        'has_statistics_fixtures': season_info[0]['seasons'][0]['coverage']['fixtures']['statistics_fixtures']
                    }
                    scraped_data.append(match_data)

            except Exception as e:
                print(f"Error while processing {competition_id} {year}: {e}")

    # Enrich scraped data
    _assign_domestic_leagues(scraped_data)
    return scraped_data

def _assign_domestic_leagues(scraped_data):
    domestic_league_dict = defaultdict(lambda: {
        'seasons': defaultdict(lambda: defaultdict(int)),
        'countries': defaultdict(int)
    })

    for match in scraped_data:
        year = match['competition_season_id'].split('_')[1]
        home_id, away_id = match['home_team_id'], match['away_team_id']
        comp_id, country = match['competition_id'], match['competition_country']

        for team_id in [home_id, away_id]:
            domestic_league_dict[team_id]['countries'][country] += 1
            domestic_league_dict[team_id]['seasons'][year][comp_id] += 1

    for match in scraped_data:
        year = match['competition_season_id'].split('_')[1]
        for side in ['home', 'away']:
            team_id = match[f'{side}_team_id']
            league_counts = domestic_league_dict[team_id]['seasons'][year]
            
            country_counts = domestic_league_dict[team_id]['countries']
            match[f'{side}_team_domestic_league_id'] = max(league_counts, key=league_counts.get)
            match[f'{side}_team_domestic_country'] = max(country_counts, key=country_counts.get)