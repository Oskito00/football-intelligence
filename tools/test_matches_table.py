import sqlite3
from Data_Migration.oscar_SQLite_migration.migrate_jsons_to_sql import create_matches_table

def create_test_table():
    conn = sqlite3.connect('test_v2db.sqlite')
    
    # Drop table if exists
    conn.execute("DROP TABLE IF EXISTS matches")
    print("Dropped existing matches table if present")
    
    # Create fresh table
    create_matches_table(conn)
    print("Table created successfully")
    
    conn.close()

def copy_matches(source_db, target_db, competition_season_id, limit=10):
    """Copy matches between databases"""
    source_conn = sqlite3.connect(source_db)
    target_conn = sqlite3.connect(target_db)
    
    # Get column names from schema
    columns = [
        'match_id', 'start_time', 'competition_id', 'competition_name',
        'competition_season_id', 'competition_season_name', 'season_start_date',
        'season_end_date', 'round_info', 'home_team_id', 'home_team_name',
        'away_team_id', 'away_team_name', 'venue_id', 'venue_name', 'venue_capacity',
        'status', 'match_status', 'home_score', 'away_score', 'period_scores',
        'winner_id', 'home_team_stats', 'home_team_player_stats', 'away_team_stats',
        'away_team_player_stats', 'home_team_lineup_info', 'home_team_manager_info',
        'home_team_formation', 'away_team_lineup_info', 'away_team_manager_info',
        'away_team_formation'
    ]
    
    # Query to select matches
    select_query = f'''
        SELECT {', '.join(columns)}
        FROM matches
        WHERE competition_season_id = ?
        LIMIT ?
    '''
    
    # Insert query
    insert_query = f'''
        INSERT INTO matches ({', '.join(columns)})
        VALUES ({', '.join(['?']*len(columns))})
    '''

    print(f"Copying {limit} matches from {source_db} to {target_db}")
    
    with source_conn:
        cursor = source_conn.cursor()
        cursor.execute(select_query, (competition_season_id, limit))
        matches = cursor.fetchall()
        print(f"Fetched {len(matches)} matches")
    with target_conn:
        target_conn.executemany(insert_query, matches)
    
    source_conn.close()
    target_conn.close()

# Usage
create_test_table()
copy_matches(
    source_db='v2db.sqlite',
    target_db='test_v2db.sqlite',
    competition_season_id='sr:season:118689',  # Replace with actual ID
    limit=1
)