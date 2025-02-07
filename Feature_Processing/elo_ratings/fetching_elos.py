import requests
from thefuzz import fuzz
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


def get_sql_data(conn, select_query):
    cursor = conn.cursor();
    cursor.execute(select_query);
    sql_data = cursor.fetchall()
    return sql_data


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

def nameclash_converter(db_name):

    teams_for_editing = {
    "Sheffield Wednesday": "Sheffield Weds",
    "FC Copenhagen": "FC København",
    "FC Levy Bereg Kyiv": "Livyi Bereh",
    "1. FC Cologne": "Köln",
    "Almere City FC": "Almere",
    "Derby County": "Derby",
    "Manchester City": "Man City",
    "Manchester United": "Man United",
    "FC Metalist 1925 Kharkiv": "Metal Kharkiv",
    "Qarabag FK": "Qarabağ",
    "Partick Thistle FC": "Partick"
}
    if db_name in teams_for_editing:
        db_name = teams_for_editing[f"{db_name}"]
    
    return db_name

def find_team_elo(home_team_name, away_team_name, parsed_response):

    both_elos = []
    for team_name in [home_team_name, away_team_name]:
        team_name = nameclash_converter(team_name);
        elo = None;
        top_fuzz_score = 0

        for entry in parsed_response[1:-3]:
            name = entry[1]
            fuzz_score = fuzz.partial_ratio(name, home_team_name)
            if fuzz_score > top_fuzz_score:
                top_fuzz_score = fuzz_score;
                top_match_elo = entry[4];
            if name in team_name or team_name in name:
                elo = entry[4]
            
        if elo == None:
            both_elos.append(round(eval(top_match_elo), 1))
        else:
            both_elos.append(round(eval(elo), 1))

    return tuple(both_elos)


def get_team_elos(conn):

    date_name_select_query = '''
    SELECT 
    clean_date, 
    home_team, 
    away_team,
    match_id
        FROM match_statistics
        ORDER BY clean_date ASC
    '''

    sql_data = get_sql_data(conn, date_name_select_query);

    matches_with_elos = []
    fetched_dates = []

    for counter, row in enumerate(sql_data):
        date = row[0]
        home_team_name = row[1]
        away_team_name = row[2]
        match_id = row[3]

        if date not in fetched_dates:
            parsed_response = fetch_elos_on_date(date)
            fetched_dates.append(date);

        home_elo_found, away_elo_found = find_team_elo(home_team_name, away_team_name, parsed_response);

        matches_with_elos.append((match_id, home_elo_found, away_elo_found))

        if counter%100 == 0:
            print("---------------------")
            print(f"processed {counter} entries")
            print("---------------------")

    return matches_with_elos;


def make_nameclash_table(nameclash_top_matches, total_count):


    for i, entry in enumerate(nameclash_top_matches):

        name = entry[0]
        top_match = entry[1]
        gap_len = (50 - len(name+top_match))

        print(f"{i+1}." + " "*10 + f"{name}" + " "*gap_len + f"{top_match}")

    print(f"\n\nTotal teams = {total_count}")


### I deleted these teams from my working database. I wasn't going to be able to find elo scores for them
##### mostly they are league 1 and league 2 teams from england, featuring in FA cup matches etc
unreachable_teams = [
    "FC Emmen",
    "Odds BK",
    "Wycombe Wanderers",
    "Plymouth Argyle",
    "Mansfield Town",
    "Fleetwood Town",
    "Shrewsbury Town",
    "Ipswich Town",
    "Milton Keynes Dons",
    "MFK Zemplin Michalovce",
    "AFC Wimbledon",
    "USL Dunkerque",
    "Ruzomberok",
    "FK Buducnost",
    "Crawley Town",
    "Barnsley FC",
    "Chesterfield FC",
    "Blackpool FC",
    "Grazer AK 1902",
    "Bolton Wanderers",
    "Stockport County FC",
    "FK Tekstilac Odzaci",
    "AS Trencin",
    "Stade Lausanne Ouchy",
    "Wigan Athletic",
    "KFC Komarno",
    "Fehervar FC Szekesfehervar",
    "Newport County",
    "Harrogate Town",
    "Doncaster Rovers",
    "Peterborough United",
    "Burton Albion",
    "NAC Breda",
    "AVS Futebol SAD",
    "Stevenage FC",
    "Morecambe FC",
    "Cambridge United",
    "Charlton Athletic",
    "Wrexham AFC",
    "FK Kosice",
    "FK Zeleziarne Podbrezova",
    "MFK Tatran Liptovsky Mikulas",
    "MFK Skalica",
    "WSG Tirol",
    "Bristol Rovers",
    "Leyton Orient London",
    "Oxford United",
    "Crewe Alexandra",
    "Gillingham FC",
    "FC Minaj",
    "Exeter City",
    "Accrington Stanley",
    "LNZ Cherkasy",
    "FK Spartak Subotica",
    "Le Puy Foot 43 Auvergne",
    "Barrow AFC",
    "Portsmouth FC",
    "Walsall FC",
    "UE Santa Coloma",
    "Cesena FC",
    "Vilnius FK Zalgiris",
    "MSK Zilina",
    "Kristiansund BK",
    "Birmingham City",
    "MFk Dukla Banska Bystrica",
    "MSK Zilina",
    "FC Vion Zlate Moravce - Vrable",
    "Pafos FC",
    "Fotbal Club FCSB",
    "Estrela Amadora",
    "Bate Borisov",
    "Port Vale",
    "ES Thaon Football"
]


## Problem Teams
# Derby = 1400
# Sheffield Weds = 1450
# Partick = 1100