import requests

import os
from dotenv import load_dotenv
import psycopg2
load_dotenv()

###### Connecting the postgres  #######################################
postgres_port = os.getenv("POSTGRES_PORT")
postgres_password = os.getenv("POSTGRES_PASSWORD")

try:
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password=postgres_password,
        host= "localhost",
        port = postgres_port
    )

    print("successfully connected")

except Exception as e:
    print(e)
########## ^^^ Connecting to postgres ########################################

cursor = conn.cursor()

select_query = '''
SELECT start_time, home_team, away_team, home_final_score, away_final_score 
	FROM match_statistics 
	ORDER BY start_time ASC
    LIMIT 5
'''

cursor.execute(select_query)
data = cursor.fetchall()
print(data)


def datetime_extractor(raw_datetime):
    return 0




def fetch_elos(date, home_team, away_team):
    '''
    Fetches the estimated/calculated elo rating from -- api.clubelo.com/YYYY-MM-DD --.

    For all clubs on one date (YYYY-MM-DD).
    '''

    api_url = f"http://api.clubelo.com/{date}"

    try:
        print(f"fetching team elos on {date}..." )
        response = requests.get(api_url)
    except Exception as e:
        print(e)
    
    string_response = response.text
    parsed_response = [s.split(",") for s in string_response.split("\n")]

    home_elo = None
    away_elo = None
    # return parsed_response
    for entry in parsed_response[:-3]:
        name = entry[1]
        if name in home_team or home_team in name:
            home_elo = entry[4]
        if name in away_team or away_team in name:
            away_elo = entry[4]

    if home_elo == None or away_elo == None:
        return "Error: unable to match name(s)"

    else:
        return [round(eval(home_elo), 1), round(eval(away_elo), 1)]


