

import sqlite3
from helpers.database_helpers.get_and_set_functions import get_all_matches


def extract_league_standings(matches):
    pass



if __name__ == "__main__":
    conn = sqlite3.connect('api_football.db')
    matches = get_all_matches(conn)
    extract_league_standings(matches)