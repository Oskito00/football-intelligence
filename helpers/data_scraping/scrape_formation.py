import os
import requests


def get_fixture_lineups(match_id: int):
    api_key = os.getenv('API_FOOTBALL_KEY')
    url = "https://v3.football.api-sports.io/fixtures/lineups"
    headers = {
        "x-rapidapi-key": api_key
    }
    params = {
        "fixture": match_id
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 204:
        return {"message": "No lineup data available for this fixture"}
    else:
        response.raise_for_status()