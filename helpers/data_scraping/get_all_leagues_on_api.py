# API setup


import os

import requests


url = "https://v3.football.api-sports.io/"
api_key = os.getenv('API_FOOTBALL_KEY')
payload = {}
headers = {
    'x-rapidapi-key': api_key,
    'x-rapidapi-host': 'v3.football.api-sports.io'
}


def get_all_leagues_on_api():
    response = requests.get("https://v3.football.api-sports.io/leagues", headers=headers, data=payload)

    #create a text file and write the response to it
    with open("data/api_football/raw/all_leagues.txt", "w") as file:
        file.write(str(response.json()))

if __name__ == "__main__":
    print(get_all_leagues_on_api())
