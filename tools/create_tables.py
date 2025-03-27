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

conn = sqlite3.connect('v2db.sqlite')
create_elo_history_table(conn)