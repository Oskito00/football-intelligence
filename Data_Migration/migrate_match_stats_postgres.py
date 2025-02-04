import json

from db_connection import conn;

cursor = conn.cursor()
########## ^^^ Connecting to postgres #######################################

## Load clean data file
with open("C:/Users/Will Boyd/InBETments Predictor/Data/clean_data.json", "r") as file:
    clean_data = json.load(file)

#########################   Columns of the match stats database ############################################################
match_data_columns = [
    "match_id",
    "start_time",
    "season_name",
    "season_id",
    "venue_id",
    "venue_name",
    "neutral_ground",
    "home_team",
    "home_team_id",
    "away_team",
    "away_team_id",
    "home_final_score",
    "away_final_score",
    "half_time_home_score",
    "half_time_away_score",
    "cards_given_home",
    "cards_given_away",
    "chances_created_home",
    "chances_created_away",
    "clearances_home",
    "clearances_away",
    "crosses_successful_home",
    "crosses_successful_away",
    "crosses_unsuccessful_home",
    "crosses_unsuccessful_away",
    "defensive_blocks_home",
    "defensive_blocks_away",
    "diving_saves_home",
    "diving_saves_away",
    "dribbles_completed_home",
    "dribbles_completed_away",
    "interceptions_home",
    "interceptions_away",
    "long_passes_successful_home",
    "long_passes_successful_away",
    "long_passes_unsuccessful_home",
    "long_passes_unsuccessful_away",
    "loss_of_possession_home",
    "loss_of_possession_away",
    "passes_successful_home",
    "passes_successful_away",
    "passes_unsuccessful_home",
    "passes_unsuccessful_away",
    "red_cards_home",
    "red_cards_away",
    "substitutions_home",
    "substitutions_away",
    "tackles_successful_home",
    "tackles_successful_away",
    "tackles_unsuccessful_home",
    "tackles_unsuccessful_away",
    "was_fouled_home",
    "was_fouled_away",
    "yellow_cards_home",
    "yellow_cards_away",
    "yellow_red_cards_home",
    "yellow_red_cards_away",
    "ball_possession_home",
    "ball_possession_away",
    "corner_kicks_home",
    "corner_kicks_away",
    "fouls_home",
    "fouls_away",
    "free_kicks_home",
    "free_kicks_away",
    "goal_kicks_home",
    "goal_kicks_away",
    "injuries_home",
    "injuries_away",
    "offsides_home",
    "offsides_away",
    "shots_blocked_home",
    "shots_blocked_away",
    "shots_off_target_home",
    "shots_off_target_away",
    "shots_on_target_home",
    "shots_on_target_away",
    "shots_saved_home",
    "shots_saved_away",
    "throw_ins_home",
    "throw_ins_away"
]
############################################################################################################################

### Form a generic SQL insert query based on the columns of the match stats db
def create_insert_query(table_name, columns):
    return f'''
        INSERT INTO {table_name} ({", ".join(columns)})
        VALUES ({", ".join(["%s" for _ in columns])})
    '''

### create a tuple of the paramter values for each match instance
def define_params(match_data, columns):
    params = [];
    for col in columns:
        if col[-5:] == "_home":
            params.append(match_data['home_team_stats'][col[:-5]])
        elif col[-5:] == "_away":
            params.append(match_data['away_team_stats'][col[:-5]])
        else:
            params.append(match_data[col])

    return tuple(params)

#### Insert clean data into the match stats db
general_insert_query = create_insert_query("match_statistics", match_data_columns)
for match in clean_data:
    params = define_params(match, match_data_columns)
    cursor.execute(general_insert_query, params)
    conn.commit()