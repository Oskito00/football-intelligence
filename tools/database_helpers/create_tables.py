#Create elo_history table
import sqlite3

#ELO TABLES
#The following tables are used to store the ELO ratings for each team, league, and nation.

def create_elo_tables(conn):
    create_elo_history_table(conn)
    create_club_elo_rating_table(conn)
    create_league_elo_table(conn)
    create_nation_elo_table(conn)

def create_elo_history_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS elo_history (
            match_id TEXT,
            home_team_id TEXT,
            away_team_id TEXT,
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
            team_id TEXT,
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
            league_id TEXT,
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

# Table for storing the main competition and country for each team
def create_team_main_competition_table(conn):
    """Create a table to store the main competition and country for each team"""
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS team_main_competition (
        team_id TEXT PRIMARY KEY,
        team_name TEXT,
        main_competition_id TEXT,
        main_competition_name TEXT,
        main_competition_country TEXT,
        match_count INTEGER
    )
    ''')
    conn.commit()

# Table for storing the form of each team
def create_team_match_history_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE TeamMatchHistory (
            team_id      TEXT,
            match_id     TEXT,
            date         DATE,
            goals_scored INT,
            goals_conceded INT,
            result       VARCHAR(4),  -- 'win', 'loss', 'draw'
            points       INT,         -- e.g., 3 for a win
            is_home      INTEGER,     -- 0 for away, 1 for home
            PRIMARY KEY (team_id, match_id)
        )
    """)
    conn.commit()
    cursor.close()

def create_counter_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS counter_table (
            competition_id TEXT,
            home_wins INTEGER,
            draw_wins INTEGER,
            away_wins INTEGER,
            count INTEGER,
            last_updated TEXT,
            PRIMARY KEY (competition_id)
        )
    """)
    conn.commit()
    cursor.close()

if __name__ == "__main__":
    conn = sqlite3.connect('v2db.sqlite')
    # create_counter_table(conn)
    create_elo_history_table(conn)