#This is a script that allows you to manually scrape fifaratings.com easily for players that 
# returned no data in the orgiginal scrape, due to either name formatting issues or no data on the website

import sqlite3
from fifa_ratings.scrape_and_store_player_stats import add_player_ratings_to_db, parse_html_to_json, scrape_player_ratings

def get_all_players(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM player_stats")
    return cursor.fetchall()

def get_players_with_no_data(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM player_stats WHERE acceleration = 0 and no_data = 0")
    return cursor.fetchall()

def set_player_no_data(conn, player_id):
    cursor = conn.cursor()
    cursor.execute("UPDATE player_stats SET no_data = True WHERE player_id = ?", (player_id,))
    conn.commit()

def set_acceleration_to_0(conn, player_id):
    cursor = conn.cursor()
    cursor.execute("UPDATE player_stats SET acceleration = 0 WHERE player_id = ?", (player_id,))
    conn.commit()

def set_new_formatted_name(conn, player_id, new_formatted_name):
    cursor = conn.cursor()
    cursor.execute("UPDATE player_stats SET player_formatted_name = ? WHERE player_id = ?", (new_formatted_name, player_id))
    conn.commit()

def manual_scraping(conn):
    players_with_no_data = get_players_with_no_data(conn)
    players_left = len(players_with_no_data)
    for player in enumerate(players_with_no_data):
        print(player)
        player_id = player[1][0]
        player_name = player[1][1]
        player_formatted_name = player[1][2]
        print(f"Player {player_id} {player_name} has no data")
        print(f"Formatted name: {player_formatted_name}")
        if player[1][49] == 1:
            print("This player has no data and has already been confirmed")
            players_left -= 1
            continue
        new_formatted_name = input("Enter the new formatted name: ")
        if new_formatted_name == "":
            set_player_no_data(conn, player_id)
            print(f"This player has no data {player_id} {player_name}")
            print("Setting player no_data field to True")
            players_left -= 1
        else:
            scrape_player_ratings(new_formatted_name)
            parsed_data = parse_html_to_json(scrape_player_ratings(new_formatted_name))
            print(parsed_data)
            add_player_ratings_to_db(player_id, player_name, player_formatted_name, parsed_data, conn)
            set_new_formatted_name(conn, player_id, new_formatted_name)
            print(f"New formatted name set for player {player_id} {player_name}")
            players_left -= 1
            print(f"Players left: {players_left}")

# For every player, scrape using their formatted name.
#Check that the url we scrape is fifaratings.com/{formatted_name} if it is not, we need to set all the stats to 0 and set no_data, found_with_ai, and no_ai_data = 0
def correct_stats(conn):
    players = get_all_players(conn)
    for player in players:
        formatted_name = player[2]
        data = scrape_player_ratings(formatted_name)
        if data.status_code == 404:
            print(f"No data found for {formatted_name}")
        if data.status_code == 200:
            if data.url != f"https://www.fifaratings.com/{formatted_name}":
                print("Players data is not correct")
                print(f"Setting acceleration to 0 for player {player[0]} {player[1]}")
                set_acceleration_to_0(conn, player[0])
                set_player_no_data(conn, player[0])
            else:
                print(f"Data found for {formatted_name} and is correct")
    

if __name__ == "__main__":
    conn = sqlite3.connect('v2db.sqlite')
    print("Getting all players with no data")
    # players = get_players_with_no_data(conn)
    # for player in players:
    #     print(player[2])
    # correct_stats(conn)
    manual_scraping(conn)
