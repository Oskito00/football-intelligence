import os
import requests



# Usage example
API_KEY = os.getenv('API_FOOTBALL_KEY')
lineup_data = get_fixture_lineups(1212557, API_KEY)
print(lineup_data)