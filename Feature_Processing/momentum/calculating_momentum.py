# Suggested momentum calculation:
#   for match in [last 5 matches]:
#       momentum += 1 (win)
#       momentum -= 1 (loss)

###### Connecting the postgres  #######################################
import os
from dotenv import load_dotenv
import psycopg2
load_dotenv()

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


def calculate_momentum(last_five_scores):

    momentum = 0;
    for score in last_five_scores:
        
        goals = score[0]
        opp_goals = score[1]

        if goals > opp_goals:
            momentum += 1
        elif goals < opp_goals:
            momentum -= 1
        else:
            continue

    return momentum;   


def last_five_scores(scores_data, scores_data_current_row_index, is_home_team):
    '''
    ONLY works given rows ordered by clean_date.
    '''
    scores_data_current_row = scores_data[scores_data_current_row_index]
    team_id_index = 0 if is_home_team else 1;
    team_id = scores_data_current_row[team_id_index];

    last_five_scores = []

    for scores_data_row in scores_data[scores_data_current_row_index+1:]:
        
        home_id = scores_data_row[0]
        away_id = scores_data_row[1]
        home_goals = scores_data_row[2]
        away_goals = scores_data_row[3]

        if home_id == team_id:
            last_five_scores.append([home_goals, away_goals])
        elif away_id == team_id:
            last_five_scores.append([away_goals, home_goals])
        
        if len(last_five_scores) == 5:
            return last_five_scores
        
    return last_five_scores


def get_momentums(conn):

    scores_by_date_query = '''
    SELECT home_team_id, away_team_id, home_final_score, away_final_score, match_id FROM match_statistics
        ORDER BY clean_date DESC
    '''
    cursor = conn.cursor()
    cursor.execute(scores_by_date_query)
    scores_data = cursor.fetchall()

    momentums_with_ids = []

    for j, row in enumerate(scores_data):
        if j%500 == 0:
            print(f"Found momentums for {j} matches...")
            print("--------------------------------")

        match_id = row[4];
        home_plus_away_momentum = []

        for is_home in [True, False]:
            last_scores = last_five_scores(scores_data, j, is_home)
            momentum = calculate_momentum(last_scores)
            home_plus_away_momentum.append(momentum);

        momentums_with_ids.append((match_id, home_plus_away_momentum[0], home_plus_away_momentum[1]))

    
    return momentums_with_ids;


def update_db_with_momentums(conn, momentums):
    print("\n\nUploading momentums to database...")
    cursor = conn.cursor()

    for row in momentums:

        match_id = row[0]
        home_momentum = row[1]
        away_momentum = row[2]

        update_query = f'''
        UPDATE match_statistics
            SET home_momentum = {home_momentum} WHERE match_id = '{match_id}';

        UPDATE match_statistics
            SET away_momentum = {away_momentum} WHERE match_id = '{match_id}';
        '''

        cursor.execute(update_query);
        conn.commit()
    print("Done.")





    


