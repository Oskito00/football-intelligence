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

import numpy as np
import json

with open("C:/Users/Will Boyd/InBETments Predictor/Data/APIfootball/league_list.json", "r") as file:
    league_list = json.load(file);


def get_elo_changes(home_elo, away_elo, home_score, away_score, K=20):

    home_result = 0.5 if home_score == away_score else 1 if home_score > away_score else 0;
    away_result = 1 - home_result

    home_expected = 1 / (10**((away_elo-home_elo) / 400) + 1)
    home_elo_change = K * (home_result - home_expected)

    away_expected = 1 / (10**((home_elo-away_elo) / 400) + 1)
    away_elo_change = K * (away_result - away_expected)

    return home_elo_change, away_elo_change


def fetch_league_ave_elo(league_list, country, league_id):
    country_leagues = league_list[country];
    for league in country_leagues:
        if league['id'] == league_id:
            return league['ave_elo'];

    return None;


def update_elos(conn, league_list):
    cursor = conn.cursor()
    team_elos = {}

    select_query = '''
    SELECT match_id, country, league_id, home_team_id, away_team_id, home_score, away_score FROM apifootball_stats
        ORDER BY clean_date;
    '''

    set_home_elo_query = '''
    UPDATE apifootball_stats
        SET home_elo_rating = %s WHERE match_id = %s;
    '''
    
    set_away_elo_query = '''
    UPDATE apifootball_stats
        SET away_elo_rating = %s WHERE match_id = %s;
    '''

    cursor.execute(select_query)
    matches = cursor.fetchall()

    for count, match in enumerate(matches):
        match_id = match[0]
        country = match[1]
        league_id = match[2]
        home_id = match[3]
        away_id = match[4]
        home_score = match[5]
        away_score = match[6]
        

        if home_id not in team_elos:
            home_elo = fetch_league_ave_elo(league_list, country, league_id);
            team_elos[home_id] = home_elo
        else:
            home_elo = team_elos[home_id]

        if away_id not in team_elos:
            away_elo = fetch_league_ave_elo(league_list, country, league_id);
            team_elos[away_id] = away_elo;
        else:
            away_elo = team_elos[away_id]

        cursor.execute(set_home_elo_query, (home_elo, match_id));
        conn.commit()

        cursor.execute(set_away_elo_query, (away_elo, match_id));
        conn.commit()

        home_elo_change, away_elo_change = get_elo_changes(home_elo, away_elo, home_score, away_score)

        team_elos[home_id] += home_elo_change;
        team_elos[away_id] += away_elo_change;
        
        if count % 1000 == 0:
            print(f"{count} matches processed")
        

update_elos(conn, league_list);


### Oscar's advanced elo function
def calculate_elo_rating(conn, match, match_importance):


    """Calculate the Elo rating for home and away team"""
    cursor = conn.cursor()
    
    # Get or create Elo ratings for both teams
    def get_or_create_elo(team_id, team_name):
        cursor.execute("""
            INSERT OR IGNORE INTO elo_rating (team_id, team_name, elo_rating)
            VALUES (?, ?, 1500)
        """, (team_id, team_name, ))
        cursor.execute("SELECT elo_rating FROM elo_rating WHERE team_id = ?", (team_id,))
        return cursor.fetchone()[0]
    
    # Get current Elo ratings
    home_elo = get_or_create_elo(match['home_team_id'], match['home_team'])
    away_elo = get_or_create_elo(match['away_team_id'], match['away_team'])
    
    # Calculate expected scores
    elo_diff = home_elo - away_elo + 100  # +100 for home advantage
    expected_home = 1 / (1 + 10 ** (-elo_diff / 400))
    expected_away = 1 - expected_home
    
    # Calculate actual scores based on goals
    if 'home_goals' in match and 'away_goals' in match:
        goal_diff = abs(match['home_goals'] - match['away_goals'])
        
        if match['home_goals'] > match['away_goals']:
            actual_home = 1
            actual_away = 0
            # Goal margin multiplier for winner (home)
            goal_multiplier = np.log(goal_diff + 1) * (2.2 / ((home_elo - away_elo) * 0.001 + 2.2))
        elif match['home_goals'] < match['away_goals']:
            actual_home = 0
            actual_away = 1
            # Goal margin multiplier for winner (away)
            goal_multiplier = np.log(goal_diff + 1) * (2.2 / ((away_elo - home_elo) * 0.001 + 2.2))
        else:
            actual_home = 0.5
            actual_away = 0.5
            goal_multiplier = 1.0
            
        # Calculate K-factor (importance multiplier)
        # Scale match_importance to reasonable K-factor range (20-40)
        base_k = 30  # Base K-factor
        k_factor = base_k * (match_importance / 10.0) * goal_multiplier
        
        # Calculate new Elo ratings
        home_elo_new = home_elo + k_factor * (actual_home - expected_home)
        away_elo_new = away_elo + k_factor * (actual_away - expected_away)
        
        # Update database with new ratings
        cursor.execute("""
            UPDATE elo_rating 
            SET elo_rating = ? 
            WHERE team_id = ?
        """, (home_elo_new, match['home_team_id']))
        
        cursor.execute("""
            UPDATE elo_rating 
            SET elo_rating = ? 
            WHERE team_id = ?
        """, (away_elo_new, match['away_team_id']))
        
        conn.commit()
        
    return home_elo, away_elo
