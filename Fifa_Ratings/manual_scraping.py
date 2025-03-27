#This is a script that allows you to manually scrape fifaratings.com easily for players that 
# returned no data in the orgiginal scrape, due to either name formatting issues or no data on the website

from Fifa_Ratings.scrape_and_store_player_stats import add_player_ratings_to_db, parse_html_to_json, scrape_player_ratings


def get_players_with_no_data(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM player_stats WHERE acceleration = 0")
    return cursor.fetchall()

def set_player_no_data(conn, player_id):
    cursor = conn.cursor()
    cursor.execute("UPDATE player_stats SET no_data = True WHERE player_id = ?", (player_id,))
    conn.commit()

def manual_scraping(conn):
    players_with_no_data = get_players_with_no_data(conn)
    for player in players_with_no_data:
        player_id = player[0]
        player_name = player[1]
        player_formatted_name = player[2]
        print(f"Player {player_id} {player_name} has no data")
        print(f"Formatted name: {player_formatted_name}")
        new_formatted_name = input("Enter the new formatted name: ")
        scrape_player_ratings(new_formatted_name)
        #check if the response is not None
        if scrape_player_ratings(new_formatted_name) is not None:
            parsed_data = parse_html_to_json(scrape_player_ratings(new_formatted_name))
            add_player_ratings_to_db(player_id, player_name, player_formatted_name, parsed_data)
        else:
            set_player_no_data(conn, player_id)
            print(f"No data found for player {player_id} {player_name}")
