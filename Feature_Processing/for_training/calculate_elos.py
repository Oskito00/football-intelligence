import sqlite3
from Tools.elo_helpers import calculate_elo_rating
from Tools.Database_helpers.get_and_set_functions import get_all_matches

def calculate_elos(conn):
    matches = get_all_matches(conn)
    for match in matches:
        calculate_elo_rating(conn, match)

if __name__ == "__main__":
    conn = sqlite3.connect('v2db.sqlite')
    calculate_elos(conn)
