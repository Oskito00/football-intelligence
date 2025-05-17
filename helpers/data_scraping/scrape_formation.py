import os
import requests
from requests.exceptions import HTTPError
import time
from dotenv import load_dotenv

load_dotenv()

def get_fixture_lineups(match_id: int):
    api_key = os.getenv('API_FOOTBALL_API_KEY')
    url = "https://v3.football.api-sports.io/fixtures/lineups"
    headers = {
        "x-rapidapi-key": api_key
    }
    params = {
        "fixture": match_id
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Request failed for match {match_id}: {str(e)}")
        raise