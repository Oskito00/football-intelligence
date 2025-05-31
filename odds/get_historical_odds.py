import http.client
import os
conn = http.client.HTTPSConnection("v3.football.api-sports.io")

headers = {
    'x-rapidapi-host': "v3.football.api-sports.io",
    'x-rapidapi-key': os.getenv('API_FOOTBALL_KEY')
    }

conn.request("GET", "/odds?season=2024&league=39&bet=1", headers=headers)

res = conn.getresponse()
data = res.read()


print(data.decode("utf-8"))
