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


## Shortcut function for getting db data
def get_sql_data(conn, select_query):
    cursor = conn.cursor();
    cursor.execute(select_query);
    sql_data = cursor.fetchall()
    return sql_data


######## DATABASE APPEARANCE COUNTS ###############################
## Finds the number of times a team appears in the database. 
def find_db_appearance_counts(conn):

    select_names_query = '''
    SELECT home_team_id, away_team_id, match_id FROM match_statistics
    '''
    sql_data = get_sql_data(conn, select_names_query)
    teams_found_so_far = []
    team_counts = {}

    for row in sql_data:
        team_ids = row[:2]
        match_id = row[-1]

        for _id in team_ids:

            if _id not in teams_found_so_far:
                team_counts[f"{_id}"] = 1;
                teams_found_so_far.append(_id)
            else:
                team_counts[f"{_id}"] += 1


    return team_counts;

## Updates the db with appearance counts
def insert_appearance_counts_to_db(conn, team_counts):

    for team_id in team_counts:

        team_count = team_counts[team_id]

        counts_insert_query = f'''
        UPDATE match_statistics
            SET home_total_appearances_in_db = {team_count} WHERE home_team_id = '{team_id}';

        UPDATE match_statistics
            SET away_total_appearances_in_db = {team_count} WHERE away_team_id = '{team_id}';
        '''

        cursor = conn.cursor()
        cursor.execute(counts_insert_query)
        conn.commit();
###################################################################


######## CLEAN DATE COLUMN CREATION ###############################
## Helper function for creating a "clean_date" column
def datetime_string_converter(raw_datetime):
    return str(raw_datetime)[:10]

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
###################################################################



######## TEAM MATCH FREQUENCY IN DATABASE #########################
from datetime import date

def days_elapsed(date0, date1=0):

    year0 = int(date0[:4]);
    month0 = int(date0[5:7]);
    day0 = int(date0[-2:]);

    year1 = int(date1[:4]);
    month1 = int(date1[5:7]);
    day1 = int(date1[-2:]);
    
    return abs((date(year0, month0, day0) - date(year1, month1, day1)).days)

def get_match_dates(conn):

    select_names_query = '''
    SELECT home_team_id, away_team_id, clean_date FROM apifootball_stats
        ORDER BY clean_date ASC
    '''
    sql_data = get_sql_data(conn, select_names_query)
    teams_found_so_far = []
    team_match_dates = {}

    for count, row in enumerate(sql_data):
        ids = row[:2];
        date = row[2];
        if count % 10000 == 0:
            print(f"{count} entries processed...")
        for team_id in ids:

            if team_id not in teams_found_so_far:
                team_match_dates[f"{team_id}"] = [date];
                teams_found_so_far.append(team_id)
            else:
                team_match_dates[f"{team_id}"].append(date);

    return team_match_dates;

def calculate_gaps(team_match_dates):

    team_match_gaps = {}

    for team in team_match_dates:
        dates = team_match_dates[team];
        
        match_gaps = []
        for i in range(len(dates)-1):
            gap = days_elapsed(dates[i], dates[i+1])
            match_gaps.append(gap);
        
        team_match_gaps[team] = match_gaps;
    
    return team_match_gaps;

def process_average_frequencies(team_match_gaps):
    
    team_freqs = {}

    for team in team_match_gaps:
        gaps = team_match_gaps[team];
        if len(gaps) == 0:
            average_gap = None;
        else:
            average_gap = int(sum(gaps)/len(gaps))
        team_freqs[team] = average_gap
    
    return team_freqs

### driver
def get_team_freqs(conn):
    team_match_dates = get_match_dates(conn)
    team_match_gaps = calculate_gaps(team_match_dates);
    team_freqs = process_average_frequencies(team_match_gaps);

    return team_freqs;

## Uploader function
def upload_frequencies_to_db(conn):

    freqs = get_team_freqs(conn);
    cursor = conn.cursor()

    for count, team_id in enumerate(freqs):
        team_freq = freqs[team_id]
        if team_freq == None:
            continue
        sql_upload_query = f'''
        UPDATE apifootball_stats
            SET home_freq_in_db = {team_freq} WHERE home_team_id = '{team_id}';

        UPDATE apifootball_stats
            SET away_freq_in_db = {team_freq} WHERE away_team_id = '{team_id}'
        '''
        try:
            cursor.execute(sql_upload_query)
            conn.commit()
        except Exception as e:
            print(e)
            print(team_id)
        
        if count % 100 == 0:
            print(f"{count} freqs uploaded...")

    print("Frequency stats successfully uploaded.")

# print(len(get_team_freqs(conn)))
# upload_frequencies_to_db(conn)


### Plot frequencies:

def get_freqs_array_from_db(conn):
    query = '''
    SELECT home_freq_in_db, away_freq_in_db, home_team_id, away_team_id from apifootball_stats
    '''
    cursor = conn.cursor()
    cursor.execute(query);
    freq_data = cursor.fetchall();

    teams = []
    freqs = []

    for match in freq_data:
        home_team_id = match[2]
        away_team_id = match[3]
        home_freq = match[0]
        away_freq = match[1]

        if home_team_id not in teams:
            teams.append(home_team_id)
            freqs.append(home_freq)
        if away_team_id not in teams:
            teams.append(away_team_id)
            freqs.append(away_freq);

    return teams, freqs


## P L O T T I N G
# import numpy as np;
# x = get_freqs_array_from_db(conn)[1];
# x = np.array([f for f in x if f != None])

# import matplotlib.pyplot as plt;
# fig, ax = plt.subplots()
# ax.hist(x, bins=500)
# ax.set_xlabel("Match Frequency")
# ax.set_ylabel("Count")
# ax.set_xlim(0, 500)
# plt.show()

###################################################################


def frequency_cleanse_cascade(conn):

    upload_frequencies_to_db(conn);
    
    delete_query = '''
    DELETE FROM apifootball_stats WHERE home_freq_in_db > 50 or away_freq_in_db > 50;
    '''
    select_query = '''
    SELECT * FROM apifootball_stats WHERE home_freq_in_db > 50 or away_freq_in_db > 50;
    '''
    cursor = conn.cursor()
    cursor.execute(select_query)
    too_infrequent = cursor.fetchall()

    while len(too_infrequent) > 0:
        cursor.execute(delete_query);
        conn.commit()
        upload_frequencies_to_db(conn);

        cursor.execute(select_query)
        too_infrequent = cursor.fetchall()


frequency_cleanse_cascade(conn)