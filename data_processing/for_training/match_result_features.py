from data_processing.helpers.processing_functions.elo_manager import EloManager
from data_processing.helpers.processing_functions.form_manager import FormManager
from data_processing.helpers.processing_functions.formation_manager import FormationManager
from data_processing.helpers.processing_functions.h2h_manager import H2HManager
from data_processing.helpers.processing_functions.match_history import process_matches_to_history
from data_processing.helpers.processing_functions.match_info_manager import MatchInfoManager
from data_processing.helpers.processing_functions.stage_of_season_manager import StageOfSeasonManager
from utils.database.clean_tables import drop_tables
from utils.database.create_tables import create_tables
from config import get_config
import psycopg2
from psycopg2.extras import RealDictCursor
from utils.database.get_and_set_functions import get_from_matches, update_processed_status


def process_matches(conn):
    drop_tables(conn)
    create_tables(conn)

    BATCH_SIZE = 1000
    
    print("Getting matches")
    # Updated query to use LEFT JOIN instead of NOT EXISTS
    matches = get_from_matches(
        conn, 
        select_str='SELECT DISTINCT', 
        columns=[
            'm.match_id', 'm.start_time', 'm.competition_id', 'm.competition_name', 
            'm.competition_country', 'm.competition_season_name', 'm.season_start_date', 
            'm.season_end_date', 'm.home_team_id', 'm.home_team_name', 'm.away_team_id', 
            'm.away_team_name', 'm.home_score', 'm.away_score', 'm.home_team_domestic_league_id', 
            'm.home_team_domestic_country', 'm.away_team_domestic_league_id', 
            'm.away_team_domestic_country', 'm.home_team_formation', 'm.away_team_formation'
        ], 
        from_clause='''matches m 
            LEFT JOIN processed_info p ON (
                m.match_id = p.match_id 
                AND p.is_processed = true 
                AND p.processing_mode = 'training'
            )''',
        where_clause='''
            m.home_score IS NOT NULL AND m.away_score IS NOT NULL 
            AND p.match_id IS NULL
        ''', 
        order_by='m.start_time'
    )
    print("Got matches")

    if len(matches) == 0:
        print("No matches to process")
        return
    
    process_matches_to_history(conn, batch_size=1000)

    for i in range(0, len(matches), BATCH_SIZE):
        batch = matches[i:i+BATCH_SIZE]
        print(f"Processing batch {i//BATCH_SIZE + 1} of {len(matches)//BATCH_SIZE + 1}")

        with ( 
              MatchInfoManager(conn, batch, mode='training') as match_info_manager, 
              StageOfSeasonManager(conn, batch, mode='training') as stage_of_season_manager, 
              FormationManager(conn, batch, mode='training') as formation_manager,
              EloManager(conn, batch, mode='training') as elo_manager,
              FormManager(conn, batch, mode='training', elo_manager=elo_manager) as form_manager,
              H2HManager(conn, batch, mode='training') as h2h_manager):
            
            match_ids = []
            with_formation_flags = []
            
            for match in batch:
                match_info_manager.process_match(match)
                stage_of_season_manager.process_match(match)
                form_manager.process_match(match)
                elo_manager.process_match(match)
                h2h_manager.process_match(match)
                
                has_formation = bool(match.get('home_team_formation') and match.get('away_team_formation'))
                if has_formation:
                    formation_manager.process_match(match)
                
                match_ids.append(match['match_id'])
                with_formation_flags.append(has_formation)
        
        # Update processed status after successful processing
        update_processed_status(conn, match_ids, with_formation_flags, mode='training')


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