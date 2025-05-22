

import sqlite3

from helpers.database_helpers.create_tables import create_league_standings_table, create_league_standings_history_table
from helpers.database_helpers.get_and_set_functions import get_from_matches, get_from_standings
from helpers.league_standings.helper import find_team_standing, save_to_standings_history


def extract_league_standings(conn, matches):

    create_league_standings_table(conn)
    create_league_standings_history_table(conn)

    rest = matches[5000:] # First 5000 matches are used for setting the priors for calculate_elos.

    standings_history = []
    BATCH_SIZE = 1000

    for match in rest:
        match_id, start_time, competition_season_id, round_info, home_team_id, away_team_id, home_score, away_score = match

        if round_info.startswith('Regular Season'):
            league_info = get_from_standings(conn, select_str='SELECT', columns=['team_id','matches_played', 'wins', 'draws', 'losses', 'goals_for', 'goals_against', 'goal_difference', 'points'], where_clause=f'competition_season_id = {competition_season_id}')

            if len(league_info) == 0:
                home_team_info = [-1] + [0] * 8
                away_team_info = [-1] + [0] * 8
            else:
                league_info.sort(key=lambda x: (-x[8], -x[7], -x[6], -x[5]))  # Sorts by:

                home_team_standing = find_team_standing(home_team_id, league_info)
                home_team_info = league_info[home_team_standing] if home_team_standing else [0] * 8
                away_team_standing = find_team_standing(away_team_id, league_info)
                away_team_info = league_info[away_team_standing] if away_team_standing else [0] * 8

                #combine standings with info
                home_team_info = home_team_standing + home_team_info
                away_team_info = away_team_standing + away_team_info
            
            standings_history.append([match_id] + home_team_info + away_team_info)

            print(standings_history)
            break
            
            if len(standings_history) >= BATCH_SIZE:
                save_to_standings_history(conn, standings_history)
                standings_history = []
            
            #Now we need to upsert into the standings table
            upsert_into_standings(conn, home_team_info, away_team_info, competition_season_id, home_score, away_score)

            print(home_team_info)
            print(away_team_info)


    pass

if __name__ == "__main__":
    conn = sqlite3.connect('api_football.db')
    matches = get_from_matches(conn, select_str='SELECT DISTINCT', columns=['match_id', 'start_time','competition_season_id', 'round_info', 'home_team_id', 'away_team_id', 'home_score', 'away_score'], where_clause='home_score IS NOT NULL AND away_score IS NOT NULL AND is_processed = 0', order_by='datetime(start_time)')
    extract_league_standings(matches)