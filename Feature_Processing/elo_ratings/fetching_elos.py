import requests

import os
from dotenv import load_dotenv
import psycopg2
load_dotenv()


def datetime_string_converter(raw_datetime):
    return str(raw_datetime)[:10]

def get_sql_data(conn, select_query):
    cursor = conn.cursor();
    cursor.execute(select_query);
    sql_data = cursor.fetchall()
    return sql_data


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


elo_ingredients_select_query = '''
SELECT start_time, home_team, away_team, home_final_score, away_final_score, match_id 
	FROM match_statistics 
	ORDER BY start_time ASC
'''

def add_clean_date_to_row(cursor, clean_date, match_id):
    
    datetime_converter_query = f'''
    UPDATE match_statistics
        SET clean_date = '{clean_date}' WHERE match_id = '{match_id}'
    '''
    cursor.execute(datetime_converter_query);

def add_clean_dates_to_db(conn):

    select_query = '''
    SELECT start_time, match_id 
        FROM match_statistics 
        ORDER BY start_time ASC
    '''
    cursor = conn.cursor();
    cursor.execute(select_query)
    sql_data = cursor.fetchall()

    for counter, row in enumerate(sql_data):
        clean_date = datetime_string_converter(row[0]);
        match_id = row[-1]
        add_clean_date_to_row(cursor, clean_date, match_id)

        if counter%1000 == 0:
            print(f"{counter} rows updated with clean dates")
            print("---------------------")

    conn.commit();
    print("finished! Have a look at your new clean_dates...");


def fetch_elos_on_date(date):
    '''
    Fetches the estimated/calculated elo rating from -- api.clubelo.com/YYYY-MM-DD --.

    For all clubs on one date (YYYY-MM-DD).
    '''

    api_url = f"http://api.clubelo.com/{date}"

    try:
        print(f"fetching team elos on {date}..." )
        response = requests.get(api_url)

        string_response = response.text
        parsed_response = [s.split(",") for s in string_response.split("\n")]
        return parsed_response;

    except Exception as e:
        return(e);

def find_team_elo(team_name, parsed_response):

    elo = None;
    for entry in parsed_response[1:-3]:
        name = entry[1]
        if name in team_name or team_name in name:
            elo = entry[4]

    if elo == None:
        return team_name
    else:
        return round(eval(elo), 1)

def name_clash_converter(db_name):

    if db_name == "Manchester United":
        return "Man United"

    if db_name == "Manchester City":
        return "Man City"
    
    if db_name == "Vikingur Reykjavic":
        return "Víkingur"

    
    return db_name


select_query = '''
SELECT clean_date, home_team, away_team FROM match_statistics
    ORDER BY clean_date ASC
'''

# sql_data = get_sql_data(conn, select_query);

# name_clash_teams = []
# checked_team_names = []
# fetched_dates = []

# for counter, match in enumerate(sql_data):
#     date = match[0]
#     home_team_name = match[1]
#     away_team_name = match[2]
#     elo_fetch_result = None;

#     if date not in fetched_dates and ( home_team_name not in checked_team_names or away_team_name not in checked_team_names ):
#         parsed_response = fetch_elos_on_date(date)
#         fetched_dates.append(date);

#     if home_team_name not in checked_team_names:
#         elo_fetch_result = find_team_elo(home_team_name, parsed_response);
#         checked_team_names.append(home_team_name);
#         if type(elo_fetch_result) == str and home_team_name not in name_clash_teams:
#             name_clash_teams.append(elo_fetch_result);
    
#     if away_team_name not in checked_team_names:
#         elo_fetch_result = find_team_elo(away_team_name, parsed_response);
#         checked_team_names.append(away_team_name);
#         if type(elo_fetch_result) == str and away_team_name not in name_clash_teams:
#             name_clash_teams.append(elo_fetch_result);


#     if counter%100 == 0:
#         print("---------------------")
#         print(f"processed {counter} entries")
#         print("---------------------")

# print(name_clash_teams, len(name_clash_teams));