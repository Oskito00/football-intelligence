from helpers.data_processing.processing_functions.elo import calculate_elos
from helpers.data_processing.processing_functions.fatigue import extract_fatigue_features
from helpers.data_processing.processing_functions.formation import formation_extraction
from helpers.data_processing.processing_functions.league_standing import extract_league_standings
from helpers.data_processing.processing_functions.match_history import process_matches_to_history
from helpers.data_processing.processing_functions.match_info import process_match_info_history
from helpers.data_processing.processing_functions.stage_of_season import extract_stage_of_season
from helpers.database_helpers.create_tables import create_tables
from config import get_config
import psycopg2


def process_matches(conn):
    
    create_tables(conn)

    process_matches_to_history(conn, batch_size=1000)
    calculate_elos(conn)
    process_match_info_history(conn, batch_size=10000)
    extract_stage_of_season(conn)
    extract_fatigue_features(conn)
    extract_league_standings(conn)

    #When we have formations add this
    # formation_extraction(conn)

    #set is processed to true for matches


if __name__ == "__main__":
    config = get_config()
    conn = psycopg2.connect(
        host=config.DB_HOST,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD
    )

    process_matches(conn)