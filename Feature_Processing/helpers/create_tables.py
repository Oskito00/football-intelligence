import sqlite3


def create_h2h_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS h2h (
            team1_id INTEGER NOT NULL,
            team2_id INTEGER NOT NULL,
            matches JSON NOT NULL DEFAULT '[]',
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (team1_id, team2_id),
            CHECK (team1_id < team2_id)
        )
    """)

if __name__ == "__main__":
    conn = sqlite3.connect("v2db.sqlite")
    create_h2h_table(conn)