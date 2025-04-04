import sqlite3
from Tools.database_helpers.get_and_set_functions import get_all_matches
from Tools.elo_helpers import calculate_elo_rating


def calculate_elos(conn):
    matches = get_all_matches(conn)
    for match in matches:
        calculate_elo_rating(conn, match)
        set_elo_processed(conn, match[0])

def set_elo_processed(conn, match_id):
    cursor = conn.cursor()
    cursor.execute("UPDATE matches SET elo_processed = 1 WHERE match_id = ?", (match_id,))
    conn.commit()
    cursor.close()

if __name__ == "__main__":
    conn = sqlite3.connect('v2db.sqlite')
    calculate_elos(conn)
