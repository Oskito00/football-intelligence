
# The following code takes a pair of raw matches and lineups files and creates a python dictionary in the form
#   dict = {
#   "match_id":
#   "start_time":
#   "season_name":
#   "season_id":
#   "venue_id":
#   "venue_name":
#   "neutral_ground":
#   "home_team":
#   "home_team_id":
#   "away_team":
#   "away_team_id":
#   "home_final_score":
#   "away_final_score":
#   "half_time_home_score":
#   "half_time_away_score":
#   "home_team_stats": {*all useful match stats*}
#   "away_team_stats": {*all useful match stats*}
#   "home_players": [{*all useful player stats*} for each home player]
#   "away_players": [{*all useful player stats*} for each away player]
#   }

####   main function -- constructs the clean dictionary    #########################
def extract_useful_match_data(raw_match_data, raw_lineups_data, useful_match_data=[]):
    """
    Extract useful information from the JSON data. Makes a list of Python dictionaries.
    
    Args:
        raw_match_data (dict): JSON data from the Sportradar API
        raw_lineups_data (dict): JSON data from the Sportradar API

    Returns:
        useful_data (dict): Extracted data containing useful information
    """
    # must differentiate for basic, deeper and extended stats
    for raw_match in raw_match_data["summaries"]:

        match_stats = get_match_stats(raw_match);
        player_stats = get_all_player_stats(raw_match, raw_lineups_data);

        clean_match = {
            "match_id": extract_piece_of_info(raw_match, '["sport_event"]["id"]'),
            "start_time": extract_piece_of_info(raw_match, '["sport_event"]["start_time"]'),
            "season_name": extract_piece_of_info(raw_match, '["sport_event"]["sport_event_context"]["season"]["name"]'),
            "season_id": extract_piece_of_info(raw_match, '["sport_event"]["sport_event_context"]["season"]["id"]'),
            "venue_id": extract_piece_of_info(raw_match, '["sport_event"]["venue"]["id"]'),
            "venue_name": extract_piece_of_info(raw_match, '["sport_event"]["venue"]["name"]'),
            "neutral_ground": extract_piece_of_info(raw_match, '["sport_event"]["sport_event_conditions"]["ground"]["neutral"]'),
            "home_team": extract_piece_of_info(raw_match, '["sport_event"]["competitors"][0]["name"]'),
            "home_team_id": extract_piece_of_info(raw_match, '["sport_event"]["competitors"][0]["id"]'),
            "away_team": extract_piece_of_info(raw_match, '["sport_event"]["competitors"][1]["name"]'),
            "away_team_id": extract_piece_of_info(raw_match, '["sport_event"]["competitors"][1]["id"]'),
            "home_final_score": extract_piece_of_info(raw_match, '["sport_event_status"]["home_score"]'),
            "away_final_score": extract_piece_of_info(raw_match, '["sport_event_status"]["away_score"]'),
            "half_time_home_score": extract_piece_of_info(raw_match, '["sport_event_status"]["period_scores"][0]["home_score"]'),
            "half_time_away_score": extract_piece_of_info(raw_match, '["sport_event_status"]["period_scores"][0]["away_score"]'),
            "home_team_stats": match_stats[0],
            "away_team_stats": match_stats[1],
            "home_players": player_stats[0],
            "away_players": player_stats[1]
        }

        useful_match_data.append(clean_match);
####  ^^^^^  main function #########################################################


######   HELPER FUNCTIONS and useful feature lists  ####################################

def extract_piece_of_info(raw_match, path_to_info):
    '''
    Lets you try extracting the info from the raw data. If it doesnt exist, it returns None.
    '''

    piece_of_info = None;

    try:
        piece_of_info = eval(f'{raw_match}'+ path_to_info)
    except KeyError:
        pass

    return piece_of_info;

all_useful_match_stats = [
    "cards_given",
    "chances_created",
    "clearances",
    "crosses_successful",
    "crosses_unsuccessful",
    "defensive_blocks",
    "diving_saves",
    "dribbles_completed",
    "interceptions",
    "long_passes_successful",
    "long_passes_unsuccessful",
    "loss_of_possession",
    "passes_successful",
    "passes_unsuccessful",
    "red_cards",
    "substitutions",
    "tackles_successful",
    "tackles_unsuccessful",
    "was_fouled",
    "yellow_cards",
    "yellow_red_cards",
    "ball_possession",
    "corner_kicks",
    "fouls",
    "free_kicks",
    "goal_kicks",
    "injuries",
    "offsides",
    "shots_blocked",
    "shots_off_target",
    "shots_on_target",
    "shots_saved",
    "throw_ins"
]

def get_match_stats(raw_match):
    '''
    Extracts the useful match stats from any sportradar match dataset for both home and away teams.
    If a stat doesnt exist, it is set to None.
    '''


    home_match_stats = {};
    away_match_stats = {};

    for stat in all_useful_match_stats:
        try:
            if raw_match["statistics"]["totals"]["competitors"][0]["statistics"][stat] is not None:

                home_match_stats[stat] = raw_match["statistics"]["totals"]["competitors"][0]["statistics"][stat]
                away_match_stats[stat] = raw_match["statistics"]["totals"]["competitors"][1]["statistics"][stat]
            else:
                home_match_stats[stat] = None
                away_match_stats[stat] = None

        except KeyError:
            home_match_stats[stat] = None
            away_match_stats[stat] = None

    return home_match_stats, away_match_stats;

useful_player_stats = {
    "from_lineups_data": [
        "type",
        "date_of_birth",
        "nationality",
        "country_code",
        "height",
        "weight",
        "jersey_number",
        "preferred_foot",
        "place_of_birth",
        "played",
        "position"
        ],

    "from_match_data": [
        "id",
        "name",
        "starter",
        "assists",
        "goals_scored",
        "own_goals",
        "red_cards",
        "substituted_in",
        "substituted_out",
        "yellow_cards",
        "yellow_red_cards",
        "chances_created",
        "clearances",
        "crosses_successful",
        "crosses_total",
        "defensive_blocks",
        "diving_saves",
        "dribbles_completed",
        "fouls_committed",
        "goals_by_head",
        "goals_by_penalty",
        "goals_conceded",
        "interceptions",
        "long_passes_successful",
        "long_passes_unsuccessful",
        "loss_of_possession",
        "minutes_played",
        "passes_successful",
        "passes_unsuccessful",
        "penalties_faced",
        "penalties_missed",
        "penalties_saved",
        "shots_faced_saved",
        "shots_faced_total",
        "was_fouled"
        ],
    }

def get_all_player_stats(raw_match, raw_lineups_data):
    '''
    A driver function that uses the three above functions to return a list of dictionaries containing all useful_player_stats.
    If a stat doesnt exist it is saved as null. 
    If lineups for that match don't exist, instead of a list of dictionaries, it returns None.
    '''

    home_players_match_data, away_players_match_data, home_players_lineup_data, away_players_lineup_data = get_players(raw_match, raw_lineups_data);

    home_players_stats = [];
    away_players_stats = [];

    try:
        for player in home_players_match_data:
            player_from_lineups = match_player_to_lineup(player, home_players_lineup_data);
            player_stats = get_one_players_stats(player, player_from_lineups);
            home_players_stats.append(player_stats);

        for player in away_players_match_data:
            player_from_lineups = match_player_to_lineup(player, away_players_lineup_data);
            player_stats = get_one_players_stats(player, player_from_lineups);
            away_players_stats.append(player_stats);
    
    except (TypeError, KeyError):
        home_players_stats = None;
        away_players_stats = None;

    return home_players_stats, away_players_stats;

###### ^^^^ HELPER FUNCTIONS and useful feature lists  ################################


########  functions in  "get_all_player_stats"  ####################
def get_players(raw_match, raw_lineups_data):
    '''
    Given a raw match,
    Returns the list of player objects from the lineups and matches data (home and away).
    '''
    home_players_match_data = None;
    away_players_match_data = None;
    home_players_lineup_data = None;
    away_players_lineup_data = None;


    try:
        home_players_match_data = raw_match["statistics"]["totals"]["competitors"][0]["players"]
        away_players_match_data = raw_match["statistics"]["totals"]["competitors"][1]["players"]
    except (KeyError, TypeError):
        pass

    for match in raw_lineups_data["lineups"]:
        if match["sport_event"]["id"] == raw_match["sport_event"]["id"]:
            
            try:
                home_players_lineup_data = match["lineups"]["competitors"][0]["players"]
                away_players_lineup_data = match["lineups"]["competitors"][1]["players"]
            except (KeyError, TypeError):
                continue
                
    return home_players_match_data, away_players_match_data, home_players_lineup_data, away_players_lineup_data;

def match_player_to_lineup(player_from_match_data, players_lineup_data):
    '''
    Given a player object from the matches data,
    finds the matching player object from the lineups data.
    '''
    player_from_lineup_data = None

    player_id = player_from_match_data["id"];
    for player in players_lineup_data:
        try:
            if player["id"] == player_id:
                player_from_lineup_data = player;
        except (KeyError, TypeError):
                break
    
    return player_from_lineup_data;

def get_one_players_stats(player_from_match, player_from_lineups):
    '''
    Given a player object from lineups and its corresponding object from matches,
        returns all useful match stats as a new object.
        All non-existent entries are saved as None.
    '''
    player_stats = {};

    for stat in useful_player_stats["from_lineups_data"]:
        try:
            player_stats[stat] = player_from_lineups[stat]
        except (KeyError, TypeError):
            player_stats[stat] = None

    for stat in useful_player_stats["from_match_data"]:
        if stat in ["id", "name", "starter"]:
            try:
                player_stats[stat] = player_from_match[stat]
            except (KeyError, TypeError):
                player_stats[stat] = None
        else:
            try:
                player_stats[stat] = player_from_match["statistics"][stat]
            except (KeyError, TypeError):
                player_stats[stat] = None

    return player_stats;
####  ^^^^^  functions in  "get_all_player_stats" ##################


#### Export main function ####
extract_useful_match_data;
