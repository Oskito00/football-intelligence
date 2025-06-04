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
    create_league_standings_table(conn)
    create_league_standings_history_table(conn)


def create_elo_history_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS elo_history (
            match_id INTEGER,
            home_team_id INTEGER,
            away_team_id INTEGER,
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
            team_id INTEGER,
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
            league_id INTEGER,
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
            nation_name TEXT,
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