from utils.data_processing.processing_functions.elo_manager import EloManager
from utils.data_processing.processing_functions.fatigue_manager import FatigueManager
from utils.data_processing.processing_functions.formation_manager import FormationManager
from utils.data_processing.processing_functions.match_info_manager import MatchInfoManager
from utils.data_processing.processing_functions.stage_of_season_manager import StageOfSeasonManager
from utils.database_helpers.clean_tables import drop_future_tables
from utils.database_helpers.create_tables import create_future_tables
from config import get_config
import psycopg2
from psycopg2.extras import RealDictCursor
from utils.database_helpers.get_and_set_functions import get_from_matches, update_processed_status
from utils.database_helpers.prune_future_features import prune_old_future_features


def process_future_matches(conn):
    drop_future_tables(conn)
    create_future_tables(conn)

    print("Pruning old future features...")
    prune_old_future_features(conn, days_threshold=2)


    BATCH_SIZE = 1000
    
    # Query for unprocessed future matches
    matches = get_from_matches(
        conn, 
        select_str='SELECT DISTINCT', 
        columns=[
            'match_id', 'start_time', 'competition_id', 'competition_name', 
            'competition_country', 'competition_season_name', 'season_start_date', 
            'season_end_date', 'home_team_id', 'home_team_name', 'away_team_id', 
            'away_team_name', 'home_team_domestic_league_id', 'home_team_domestic_country', 
            'away_team_domestic_league_id', 'away_team_domestic_country', 
            'home_team_formation', 'away_team_formation'
        ], 
        where_clause='''
            home_score IS NULL AND away_score IS NULL AND match_status = 'NS' AND start_time > NOW() AND start_time < NOW() + INTERVAL ' 7 days'
            AND match_id NOT IN (
                SELECT match_id FROM processed_info 
                WHERE is_processed = true AND processing_mode = 'inference' AND with_formation = true
            )
        ''', 
        order_by='start_time'
    )

    if len(matches) == 0:
        print("No matches to process")
        return

    for i in range(0, len(matches), BATCH_SIZE):
        batch = matches[i:i+BATCH_SIZE]
        print(f"Processing future matches batch {i//BATCH_SIZE + 1} of {len(matches)//BATCH_SIZE + 1}")

        with (EloManager(conn, batch, mode='inference') as elo_manager, 
              MatchInfoManager(conn, batch, mode='inference') as match_info_manager, 
              StageOfSeasonManager(conn, batch, mode='inference') as stage_of_season_manager, 
              FormationManager(conn, batch, mode='inference') as formation_manager):
            
            match_ids = []
            with_formation_flags = []
            
            for match in batch:
                elo_manager.process_match(match)
                match_info_manager.process_match(match)
                stage_of_season_manager.process_match(match)
                
                has_formation = bool(match.get('home_team_formation') and match.get('away_team_formation'))
                if has_formation:
                    formation_manager.process_match(match)
                
                match_ids.append(match['match_id'])
                with_formation_flags.append(has_formation)
        
        # Update processed status for inference
        update_processed_status(conn, match_ids, with_formation_flags, mode='inference')


if __name__ == "__main__":
    config = get_config()
    conn = psycopg2.connect(
        host=config.DB_HOST,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        cursor_factory=RealDictCursor
    )
    process_future_matches(conn)