#This file contains all the code to create the necessary tables in the database

def create_tables(conn):
    """Creates tables of use to processing functions"""
    create_team_match_history_table(conn)
    create_counter_table(conn)
    create_elo_history_table(conn)
    create_club_elo_rating_table(conn)
    create_league_elo_table(conn)
    create_nation_elo_table(conn)
    create_match_info_table(conn)
    create_stage_of_season_table(conn)
    create_league_standings_table(conn)
    create_league_standings_history_table(conn)
    create_formation_history_table(conn)

def create_match_result_predictions_table(conn):
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS match_result_predictions (
        match_id INTEGER PRIMARY KEY,
        predicted_result INTEGER,
        start_time TIMESTAMP,
        home_team_name TEXT,
        away_team_name TEXT,
        prob_home_win REAL,
        prob_draw REAL,
        prob_away_win REAL,
        model_type TEXT,  -- 'basic' or 'with_formation'
        prediction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    cursor.close()

def create_future_tables(conn):
    """Creates tables of use to processing functions"""
    create_elo_future_table(conn)
    create_stage_of_season_future_table(conn)
    create_match_info_future_table(conn)
    create_league_standings_future_table(conn)
    create_formation_future_table(conn)

def create_stage_of_season_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stage_of_season_history (
            match_id INTEGER,
            start_time TIMESTAMP,
            season_start_date TIMESTAMP,
            season_end_date TIMESTAMP,
            stage_of_season REAL,
            stage_of_season_category TEXT
        )
    """)
    conn.commit()
    cursor.close()

def create_formation_history_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS formation_history (
            match_id INTEGER,
            start_time TIMESTAMP,
            home_team_formation TEXT,
            away_team_formation TEXT
        )
    """)
    conn.commit()
    cursor.close()

def create_formation_future_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS formation_future (
            match_id INTEGER,
            start_time TIMESTAMP,
            home_team_formation TEXT,
            away_team_formation TEXT
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_formation_future_start_time 
        ON formation_future(start_time)
    """)
    conn.commit()
    cursor.close()

def create_stage_of_season_future_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stage_of_season_future (
            match_id INTEGER,
            start_time TIMESTAMP,
            season_start_date TIMESTAMP,
            season_end_date TIMESTAMP,
            stage_of_season REAL,
            stage_of_season_category TEXT
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_stage_of_season_future_start_time 
        ON stage_of_season_future(start_time)
    """)
    conn.commit()
    cursor.close()

def create_elo_future_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS elo_future (
            match_id INTEGER,
            start_time TIMESTAMP,
            home_team_id INTEGER,
            away_team_id INTEGER,
            home_team_name TEXT,
            away_team_name TEXT,
            k_draw_parameter REAL,
            eta_home_advantage REAL,
            
            -- HOME TEAM ELO RATINGS
            home_team_nation_elo_K5 INTEGER,
            home_team_nation_elo_K10 INTEGER,
            home_team_nation_elo_K20 INTEGER,
            home_team_nation_elo_K30 INTEGER,
            home_team_nation_elo_K40 INTEGER,
            home_team_nation_elo_K80 INTEGER,
            home_team_league_domestic_elo_K5 INTEGER,
            home_team_league_domestic_elo_K10 INTEGER,
            home_team_league_domestic_elo_K20 INTEGER,
            home_team_league_domestic_elo_K30 INTEGER,
            home_team_league_domestic_elo_K40 INTEGER,
            home_team_league_domestic_elo_K80 INTEGER,
            home_team_league_continental_elo_K5 INTEGER,
            home_team_league_continental_elo_K10 INTEGER,
            home_team_league_continental_elo_K20 INTEGER,
            home_team_league_continental_elo_K30 INTEGER,
            home_team_league_continental_elo_K40 INTEGER,
            home_team_league_continental_elo_K80 INTEGER,
            home_team_elo_home_matches_K5 INTEGER,
            home_team_elo_home_matches_K10 INTEGER,
            home_team_elo_home_matches_K20 INTEGER,
            home_team_elo_home_matches_K30 INTEGER,
            home_team_elo_home_matches_K40 INTEGER,
            home_team_elo_home_matches_K80 INTEGER,
            home_team_elo_away_matches_K5 INTEGER,
            home_team_elo_away_matches_K10 INTEGER,
            home_team_elo_away_matches_K20 INTEGER,
            home_team_elo_away_matches_K30 INTEGER,
            home_team_elo_away_matches_K40 INTEGER,
            home_team_elo_away_matches_K80 INTEGER,
            home_team_elo_K5 INTEGER,
            home_team_elo_K10 INTEGER,
            home_team_elo_K20 INTEGER,
            home_team_elo_K30 INTEGER,
            home_team_elo_K40 INTEGER,
            home_team_elo_K80 INTEGER,
            home_team_elo_domestic_K5 INTEGER,
            home_team_elo_domestic_K10 INTEGER,
            home_team_elo_domestic_K20 INTEGER,
            home_team_elo_domestic_K30 INTEGER,
            home_team_elo_domestic_K40 INTEGER,
            home_team_elo_domestic_K80 INTEGER,
            home_team_elo_intraleague_K5 INTEGER,
            home_team_elo_intraleague_K10 INTEGER,
            home_team_elo_intraleague_K20 INTEGER,
            home_team_elo_intraleague_K30 INTEGER,
            home_team_elo_intraleague_K40 INTEGER,
            home_team_elo_intraleague_K80 INTEGER,
            home_team_elo_international_K5 INTEGER,
            home_team_elo_international_K10 INTEGER,
            home_team_elo_international_K20 INTEGER,
            home_team_elo_international_K30 INTEGER,
            home_team_elo_international_K40 INTEGER,
            home_team_elo_international_K80 INTEGER,
                
            -- AWAY TEAM ELO RATINGS
            away_team_nation_elo_K5 INTEGER,
            away_team_nation_elo_K10 INTEGER,
            away_team_nation_elo_K20 INTEGER,
            away_team_nation_elo_K30 INTEGER,
            away_team_nation_elo_K40 INTEGER,
            away_team_nation_elo_K80 INTEGER,
            away_team_league_domestic_elo_K5 INTEGER,
            away_team_league_domestic_elo_K10 INTEGER,
            away_team_league_domestic_elo_K20 INTEGER,
            away_team_league_domestic_elo_K30 INTEGER,
            away_team_league_domestic_elo_K40 INTEGER,
            away_team_league_domestic_elo_K80 INTEGER,
            away_team_league_continental_elo_K5 INTEGER,
            away_team_league_continental_elo_K10 INTEGER,
            away_team_league_continental_elo_K20 INTEGER,
            away_team_league_continental_elo_K30 INTEGER,
            away_team_league_continental_elo_K40 INTEGER,
            away_team_league_continental_elo_K80 INTEGER,
            away_team_elo_home_matches_K5 INTEGER,
            away_team_elo_home_matches_K10 INTEGER,
            away_team_elo_home_matches_K20 INTEGER,
            away_team_elo_home_matches_K30 INTEGER,
            away_team_elo_home_matches_K40 INTEGER,
            away_team_elo_home_matches_K80 INTEGER,
            away_team_elo_away_matches_K5 INTEGER,
            away_team_elo_away_matches_K10 INTEGER,
            away_team_elo_away_matches_K20 INTEGER,
            away_team_elo_away_matches_K30 INTEGER,
            away_team_elo_away_matches_K40 INTEGER,
            away_team_elo_away_matches_K80 INTEGER,
            away_team_elo_K5 INTEGER,
            away_team_elo_K10 INTEGER,
            away_team_elo_K20 INTEGER,
            away_team_elo_K30 INTEGER,
            away_team_elo_K40 INTEGER,
            away_team_elo_K80 INTEGER,
            away_team_elo_domestic_K5 INTEGER,
            away_team_elo_domestic_K10 INTEGER,
            away_team_elo_domestic_K20 INTEGER,
            away_team_elo_domestic_K30 INTEGER,
            away_team_elo_domestic_K40 INTEGER,
            away_team_elo_domestic_K80 INTEGER,
            away_team_elo_intraleague_K5 INTEGER,
            away_team_elo_intraleague_K10 INTEGER,
            away_team_elo_intraleague_K20 INTEGER,
            away_team_elo_intraleague_K30 INTEGER,
            away_team_elo_intraleague_K40 INTEGER,
            away_team_elo_intraleague_K80 INTEGER,
            away_team_elo_international_K5 INTEGER,
            away_team_elo_international_K10 INTEGER,
            away_team_elo_international_K20 INTEGER,
            away_team_elo_international_K30 INTEGER,
            away_team_elo_international_K40 INTEGER,
            away_team_elo_international_K80 INTEGER
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_elo_future_start_time 
        ON elo_future(start_time)
    """)
    conn.commit()
    cursor.close()

def create_elo_history_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS elo_history (
            match_id INTEGER,
            home_team_id INTEGER,
            away_team_id INTEGER,
            home_team_name TEXT,
            away_team_name TEXT,
            k_draw_parameter REAL,
            eta_home_advantage REAL,
            
            -- HOME TEAM ELO RATINGS
            home_team_nation_elo_K5 INTEGER,
            home_team_nation_elo_K10 INTEGER,
            home_team_nation_elo_K20 INTEGER,
            home_team_nation_elo_K30 INTEGER,
            home_team_nation_elo_K40 INTEGER,
            home_team_nation_elo_K80 INTEGER,
            home_team_league_domestic_elo_K5 INTEGER,
            home_team_league_domestic_elo_K10 INTEGER,
            home_team_league_domestic_elo_K20 INTEGER,
            home_team_league_domestic_elo_K30 INTEGER,
            home_team_league_domestic_elo_K40 INTEGER,
            home_team_league_domestic_elo_K80 INTEGER,
            home_team_league_continental_elo_K5 INTEGER,
            home_team_league_continental_elo_K10 INTEGER,
            home_team_league_continental_elo_K20 INTEGER,
            home_team_league_continental_elo_K30 INTEGER,
            home_team_league_continental_elo_K40 INTEGER,
            home_team_league_continental_elo_K80 INTEGER,
            home_team_elo_home_matches_K5 INTEGER,
            home_team_elo_home_matches_K10 INTEGER,
            home_team_elo_home_matches_K20 INTEGER,
            home_team_elo_home_matches_K30 INTEGER,
            home_team_elo_home_matches_K40 INTEGER,
            home_team_elo_home_matches_K80 INTEGER,
            home_team_elo_away_matches_K5 INTEGER,
            home_team_elo_away_matches_K10 INTEGER,
            home_team_elo_away_matches_K20 INTEGER,
            home_team_elo_away_matches_K30 INTEGER,
            home_team_elo_away_matches_K40 INTEGER,
            home_team_elo_away_matches_K80 INTEGER,
            home_team_elo_K5 INTEGER,
            home_team_elo_K10 INTEGER,
            home_team_elo_K20 INTEGER,
            home_team_elo_K30 INTEGER,
            home_team_elo_K40 INTEGER,
            home_team_elo_K80 INTEGER,
            home_team_elo_domestic_K5 INTEGER,
            home_team_elo_domestic_K10 INTEGER,
            home_team_elo_domestic_K20 INTEGER,
            home_team_elo_domestic_K30 INTEGER,
            home_team_elo_domestic_K40 INTEGER,
            home_team_elo_domestic_K80 INTEGER,
            home_team_elo_intraleague_K5 INTEGER,
            home_team_elo_intraleague_K10 INTEGER,
            home_team_elo_intraleague_K20 INTEGER,
            home_team_elo_intraleague_K30 INTEGER,
            home_team_elo_intraleague_K40 INTEGER,
            home_team_elo_intraleague_K80 INTEGER,
            home_team_elo_international_K5 INTEGER,
            home_team_elo_international_K10 INTEGER,
            home_team_elo_international_K20 INTEGER,
            home_team_elo_international_K30 INTEGER,
            home_team_elo_international_K40 INTEGER,
            home_team_elo_international_K80 INTEGER,
                
            -- AWAY TEAM ELO RATINGS
            away_team_nation_elo_K5 INTEGER,
            away_team_nation_elo_K10 INTEGER,
            away_team_nation_elo_K20 INTEGER,
            away_team_nation_elo_K30 INTEGER,
            away_team_nation_elo_K40 INTEGER,
            away_team_nation_elo_K80 INTEGER,
            away_team_league_domestic_elo_K5 INTEGER,
            away_team_league_domestic_elo_K10 INTEGER,
            away_team_league_domestic_elo_K20 INTEGER,
            away_team_league_domestic_elo_K30 INTEGER,
            away_team_league_domestic_elo_K40 INTEGER,
            away_team_league_domestic_elo_K80 INTEGER,
            away_team_league_continental_elo_K5 INTEGER,
            away_team_league_continental_elo_K10 INTEGER,
            away_team_league_continental_elo_K20 INTEGER,
            away_team_league_continental_elo_K30 INTEGER,
            away_team_league_continental_elo_K40 INTEGER,
            away_team_league_continental_elo_K80 INTEGER,
            away_team_elo_home_matches_K5 INTEGER,
            away_team_elo_home_matches_K10 INTEGER,
            away_team_elo_home_matches_K20 INTEGER,
            away_team_elo_home_matches_K30 INTEGER,
            away_team_elo_home_matches_K40 INTEGER,
            away_team_elo_home_matches_K80 INTEGER,
            away_team_elo_away_matches_K5 INTEGER,
            away_team_elo_away_matches_K10 INTEGER,
            away_team_elo_away_matches_K20 INTEGER,
            away_team_elo_away_matches_K30 INTEGER,
            away_team_elo_away_matches_K40 INTEGER,
            away_team_elo_away_matches_K80 INTEGER,
            away_team_elo_K5 INTEGER,
            away_team_elo_K10 INTEGER,
            away_team_elo_K20 INTEGER,
            away_team_elo_K30 INTEGER,
            away_team_elo_K40 INTEGER,
            away_team_elo_K80 INTEGER,
            away_team_elo_domestic_K5 INTEGER,
            away_team_elo_domestic_K10 INTEGER,
            away_team_elo_domestic_K20 INTEGER,
            away_team_elo_domestic_K30 INTEGER,
            away_team_elo_domestic_K40 INTEGER,
            away_team_elo_domestic_K80 INTEGER,
            away_team_elo_intraleague_K5 INTEGER,
            away_team_elo_intraleague_K10 INTEGER,
            away_team_elo_intraleague_K20 INTEGER,
            away_team_elo_intraleague_K30 INTEGER,
            away_team_elo_intraleague_K40 INTEGER,
            away_team_elo_intraleague_K80 INTEGER,
            away_team_elo_international_K5 INTEGER,
            away_team_elo_international_K10 INTEGER,
            away_team_elo_international_K20 INTEGER,
            away_team_elo_international_K30 INTEGER,
            away_team_elo_international_K40 INTEGER,
            away_team_elo_international_K80 INTEGER,
            
            -- MATCH RESULT
            home_team_score INTEGER,
            away_team_score INTEGER
        )
    """)
    conn.commit()
    cursor.close()

def create_club_elo_rating_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS club_elo_ratings (
            team_id INTEGER PRIMARY KEY,
            team_name TEXT,
            elo_home_matches_K5 INTEGER,
            elo_home_matches_K10 INTEGER,
            elo_home_matches_K20 INTEGER,
            elo_home_matches_K30 INTEGER,
            elo_home_matches_K40 INTEGER,
            elo_home_matches_K80 INTEGER,
            elo_away_matches_K5 INTEGER,
            elo_away_matches_K10 INTEGER,
            elo_away_matches_K20 INTEGER,
            elo_away_matches_K30 INTEGER,
            elo_away_matches_K40 INTEGER,
            elo_away_matches_K80 INTEGER,
            elo_K5 INTEGER,
            elo_K10 INTEGER,
            elo_K20 INTEGER,
            elo_K30 INTEGER,
            elo_K40 INTEGER,
            elo_K80 INTEGER,
            elo_domestic_K5 INTEGER,
            elo_domestic_K10 INTEGER,
            elo_domestic_K20 INTEGER,
            elo_domestic_K30 INTEGER,
            elo_domestic_K40 INTEGER,
            elo_domestic_K80 INTEGER,
            elo_intraleague_K5 INTEGER,
            elo_intraleague_K10 INTEGER,
            elo_intraleague_K20 INTEGER,
            elo_intraleague_K30 INTEGER,
            elo_intraleague_K40 INTEGER,
            elo_intraleague_K80 INTEGER,
            elo_international_K5 INTEGER,
            elo_international_K10 INTEGER,
            elo_international_K20 INTEGER,
            elo_international_K30 INTEGER,
            elo_international_K40 INTEGER,
            elo_international_K80 INTEGER
        )
    """)
    conn.commit()
    cursor.close()

def create_league_elo_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS league_elo_ratings (
            league_id INTEGER PRIMARY KEY,
            league_domestic_elo_K5 INTEGER,
            league_domestic_elo_K10 INTEGER,
            league_domestic_elo_K20 INTEGER,
            league_domestic_elo_K30 INTEGER,
            league_domestic_elo_K40 INTEGER,
            league_domestic_elo_K80 INTEGER,
            league_continental_elo_K5 INTEGER,
            league_continental_elo_K10 INTEGER,
            league_continental_elo_K20 INTEGER,
            league_continental_elo_K30 INTEGER,
            league_continental_elo_K40 INTEGER,
            league_continental_elo_K80 INTEGER
        )
    """)
    conn.commit()
    cursor.close()

def create_nation_elo_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nation_elo_ratings (
            nation_name TEXT PRIMARY KEY,
            nation_elo_K5 INTEGER,
            nation_elo_K10 INTEGER,
            nation_elo_K20 INTEGER,
            nation_elo_K30 INTEGER,
            nation_elo_K40 INTEGER,
            nation_elo_K80 INTEGER
        )
    """)
    conn.commit()
    cursor.close()

#MAIN COMPETITION
def create_team_main_competition_table(conn):
    """Create a table to store the main competition and country for each team"""
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS team_main_competition (
        team_id INTEGER PRIMARY KEY,
        team_name TEXT,
        main_competition_id INTEGER,
        main_competition_name TEXT,
        main_competition_country TEXT,
        match_count INTEGER
    )
    ''')
    conn.commit()

#MATCH HISTORY
def create_team_match_history_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS TeamMatchHistory (
            team_id      INTEGER,
            match_id     INTEGER,
            start_time   TIMESTAMP,
            competition_season_name TEXT,
            competition_id TEXT,
            competition_name TEXT,
            competition_country TEXT,
            goals_scored INT,
            goals_conceded INT,
            result       VARCHAR(4),  -- 'win', 'loss', 'draw'
            is_home      INTEGER,     -- 0 for away, 1 for home
            is_intraleague_match INTEGER,
            is_domestic_cup_match INTEGER,
            is_continental_cup_match INTEGER,
            PRIMARY KEY (team_id, match_id)
        )
    """)
    conn.commit()
    cursor.close()

#COUNTER FOR ALL MATCH RESULTS
def create_counter_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS counter_table (
            competition_id TEXT,
            home_wins FLOAT,
            draw_wins FLOAT,
            away_wins FLOAT,
            count INTEGER,
            last_updated TEXT,
            PRIMARY KEY (competition_id)
        )
    """)
    conn.commit()
    cursor.close()

#MATCH INFO
def create_match_info_table(conn):
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS match_info_history (
        match_id INTEGER,
        start_time TIMESTAMP,
        competition_season_name TEXT,
        competition_id TEXT,
        competition_name TEXT,
        competition_country TEXT,
        home_team_name TEXT,
        away_team_name TEXT,
        PRIMARY KEY (match_id, competition_id)
    )
    ''')
    conn.commit()
    cursor.close()

def create_match_info_future_table(conn):
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS match_info_future (
        match_id INTEGER,
        start_time TIMESTAMP,
        competition_season_name TEXT,
        competition_id TEXT,
        competition_name TEXT,
        competition_country TEXT,
        home_team_name TEXT,
        away_team_name TEXT,
        PRIMARY KEY (match_id, competition_id)
    )
    ''')
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_match_info_future_start_time 
        ON match_info_future(start_time)
    """)
    conn.commit()
    cursor.close()

#LEAGUE STANDINGS
def create_league_standings_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS league_standings (
            team_id INTEGER,
            competition_season_id TEXT,
            matches_played INTEGER,
            wins INTEGER,
            draws INTEGER,
            losses INTEGER,
            goals_for INTEGER,
            goals_against INTEGER,
            goal_difference INTEGER,
            points INTEGER,
            PRIMARY KEY (team_id, competition_season_id)
        )
    """)
    conn.commit()
    cursor.close()

def create_league_standings_history_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS league_standings_history (
            match_id INTEGER,
            home_standing INTEGER,
            home_matches_played INTEGER,
            home_wins INTEGER,
            home_draws INTEGER,
            home_losses INTEGER,
            home_goals_for INTEGER,
            home_goals_against INTEGER,
            home_goal_difference INTEGER,
            home_points INTEGER,
            away_standing INTEGER,
            away_matches_played INTEGER,
            away_wins INTEGER,
            away_draws INTEGER,
            away_losses INTEGER,
            away_goals_for INTEGER,
            away_goals_against INTEGER,
            away_goal_difference INTEGER,
            away_points INTEGER
        )
    """)
    conn.commit()
    cursor.close()

def create_league_standings_future_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS league_standings_future (
            match_id INTEGER,
            start_time TIMESTAMP,
            home_standing INTEGER,
            home_matches_played INTEGER,
            home_wins INTEGER,
            home_draws INTEGER,
            home_losses INTEGER,
            home_goals_for INTEGER,
            home_goals_against INTEGER,
            home_goal_difference INTEGER,
            home_points INTEGER,
            away_standing INTEGER,
            away_matches_played INTEGER,
            away_wins INTEGER,
            away_draws INTEGER,
            away_losses INTEGER,
            away_goals_for INTEGER,
            away_goals_against INTEGER,
            away_goal_difference INTEGER,
            away_points INTEGER
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_league_standings_future_start_time 
        ON league_standings_future(start_time)
    """)
    conn.commit()
    cursor.close()

def create_odds_table(conn):
    """Create the odds table if it doesn't exist"""
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS odds (
        id SERIAL PRIMARY KEY,
        match_id INTEGER NOT NULL,
        bookmaker_id INTEGER NOT NULL,
        bookmaker_name TEXT NOT NULL,
        bet_type_id INTEGER NOT NULL,
        bet_type_name TEXT NOT NULL,
        bet_value TEXT NOT NULL,
        odds_value DECIMAL(10,2) NOT NULL,
        retrieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        api_last_updated TIMESTAMP
    )
    ''')
    
    # Create index for faster queries
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_odds_match_id 
    ON odds(match_id)
    ''')
    
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_odds_retrieved_at 
    ON odds(retrieved_at)
    ''')
    
    conn.commit()
    cursor.close()