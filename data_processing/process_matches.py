from helpers.database_helpers.get_and_set_functions import get_from_matches
from config import get_config
import psycopg2


def process_matches(matches):
    for match in matches:
        #call processing/extracting functions on individual matches
        #TeamMatchHistory
        #ELO
        #Fatigue
        #league_standing
        #match_info
        #stage_of_season

        

        #Formation (if it has it)



if __name__ == "__main__":
    config = get_config()
    conn = psycopg2.connect(
        host=config.DB_HOST,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD
    )
    matches = get_from_matches(conn, select_str='SELECT', columns=['match_id', 'start_time', 'clean_date','competition_name', 'competition_id', 'competition_country', 'competition_season_name', 'competition_season_id', 'season_start_date', 'season_end_date', 'round_info', 'home_team_id', 'home_team_name', 'home_team_domestic_league_id','away_team_domestic_league_id', 'home_team_domestic_country', 'away_team_domestic_country', 'away_team_id', 'away_team_name', 'match_status', 'home_score', 'away_score', 'result'], where_clause='home_score IS NOT NULL AND away_score IS NOT NULL AND is_processed = false', order_by='start_time')
    print(len(matches))    