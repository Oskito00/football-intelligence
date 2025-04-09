#Create elo_history table
import sqlite3


def create_elo_history_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS elo_history (
            home_team_id INTEGER,
            away_team_id INTEGER,
            elo_difference INTEGER,
            result INTEGER
        )
    """)
    conn.commit()
    cursor.close()

def create_elo_rating_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS elo_ratings (
            team_id TEXT,
            team_name TEXT,
            elo_rating INTEGER
        )
    """)
    conn.commit()
    cursor.close()

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

conn = sqlite3.connect('v2db.sqlite')
create_team_match_history_table(conn)