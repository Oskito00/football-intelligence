from helpers.data_processing.processing_functions.elo_manager import EloManager
from helpers.data_processing.processing_functions.fatigue_manager import FatigueManager
from helpers.data_processing.processing_functions.formation_manager import FormationManager
from helpers.data_processing.processing_functions.match_info_manager import MatchInfoManager
from helpers.data_processing.processing_functions.stage_of_season_manager import StageOfSeasonManager
from helpers.database_helpers.clean_tables import drop_tables
from helpers.database_helpers.create_tables import create_tables
from config import get_config
import psycopg2
from psycopg2.extras import RealDictCursor
from helpers.database_helpers.get_and_set_functions import get_from_matches


def process_matches(conn):
    drop_tables(conn)
    create_tables(conn)

    # process_matches_to_history(conn, batch_size=1000) #Makes form/fatigue much easier to extract

    BATCH_SIZE = 1000
    matches = get_from_matches(conn, select_str='SELECT DISTINCT', columns=['match_id', 'start_time', 'competition_id', 'competition_name', 'competition_country', 'competition_season_name', 'season_start_date', 'season_end_date', 'home_team_id', 'home_team_name', 'away_team_id', 'away_team_name', 
               'home_score', 'away_score', 'home_team_domestic_league_id', 'home_team_domestic_country', 'away_team_domestic_league_id', 'away_team_domestic_country', 'home_team_formation', 'away_team_formation'], where_clause='home_score IS NOT NULL AND away_score IS NOT NULL AND is_processed = false', order_by='start_time')

    for i in range(0,len(matches),BATCH_SIZE):
        batch = matches[i:i+BATCH_SIZE]
        print(f"Processing batch {i//BATCH_SIZE + 1} of {len(matches)//BATCH_SIZE}")

        with EloManager(conn, batch) as elo_manager, MatchInfoManager(conn, batch) as match_info_manager, StageOfSeasonManager(conn, batch) as stage_of_season_manager, FormationManager(conn, batch) as formation_manager:
            for match in batch:
                elo_manager.process_match(match)
                match_info_manager.process_match(match)
                stage_of_season_manager.process_match(match)
                formation_manager.process_match(match)


            

    # process_match_info_history(conn, batch_size=10000)
    # extract_stage_of_season(conn)
    # extract_fatigue_features(conn)
    # extract_league_standings(conn)

    #When we have formations add this
    # formation_extraction(conn)

    #set is processed to true for matches


if __name__ == "__main__":
    config = get_config()
    conn = psycopg2.connect(
        host=config.DB_HOST,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        cursor_factory=RealDictCursor
    )
    process_matches(conn)