import json
import requests
import psycopg2

from config import get_config
from utils.database.postgresql import upsert_records

config = get_config()

headers = {
    'x-rapidapi-key': config.API_FOOTBALL_KEY,
    'x-rapidapi-host': 'v3.football.api-sports.io'
}

def get_all_leagues_on_api(conn):
    response = requests.get("https://v3.football.api-sports.io/leagues", headers=headers)


    if response.status_code != 200:
        print("Failed to fetch leagues:", response.text)
        return

    data = response.json().get('response', [])

    rows = []
    for league in data:
        print("Processing league:", league['league']['name'])
        league_data = {
            'id': league['league']['id'],
            'name': league['league']['name'],
            'type': league['league']['type'],
            'logo': league['league']['logo'],
            'country': json.dumps(league['country']),
            'years': ([season['year'] for season in league['seasons']]),
            'current_season': next((season['year'] for season in league['seasons'] if season['current']), None),
            'seasons': json.dumps(league['seasons'])
        }
        print(league_data['years'])
        rows.append(league_data)

    upsert_records(conn, 'leagues', rows, ['id'], batch_size=1000)


if __name__ == "__main__":
    get_all_leagues_on_api(conn)