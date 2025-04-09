import sqlite3
import time

from Fifa_Ratings.scrape_and_store_player_stats import add_player_ratings_to_db, parse_html_to_json, scrape_player_ratings
from Tools.deepseek_api import DeepSeekAPI


def get_players_with_no_data(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM player_stats WHERE acceleration = 0 AND found_with_AI = 0 and no_ai_data = 0")
    return cursor.fetchall()

def set_no_ai_data_flag(player_id, true_or_false,conn):
    cursor = None
    try:
        cursor = conn.cursor()
        if true_or_false:
            cursor.execute("UPDATE player_stats SET no_ai_data = 1 WHERE player_id = ?", (player_id,))
            print("Set no_ai_data flag to 1 for player ", player_id)
        else:
            cursor.execute("UPDATE player_stats SET no_ai_data  = 0 WHERE player_id = ?", (player_id,))
            print("Set no_ai_data flag to 0 for player ", player_id)
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error updating AI flag for player {player_id}: {str(e)}")
        conn.rollback()
        raise  # Re-raise exception to handle at higher level
    except Exception as e:
        print(f"General error updating AI flag for player {player_id}: {str(e)}")
        conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
    return 0

def scrape_and_process_player(ds, player_name, player_formatted_name, player_id, conn):
    """Deepseek enhanced scraping 
    and processing of player data"""
    #For each player in deepseeks response, check to see if it returns data
    prompt = f"""**Task:** Generate plausible URL slugs for fifaratings.com based on player names.
    
**Rules to Follow:**
1. Name Formatting:
   - All lowercase with hyphens
   - No special characters/accents
   - Maximum 3 hyphens total
   - No spaces between hyphens

2. Priority Variations:
   - Add common middle names (e.g., "mohamed-salah" → "mo-salah")
   - If you can find out the players middle names add them to the middle of the name (e.g "bruno fernandes" → "bruno-miguel-borges-fernandes)
   - Look at their wikipedia page and see if they have any nicknames or middle names
   - Use cultural nicknames (Spanish "Fernando" → "fer", Portuguese "João" → "joao")
   - Hyphenate compound surnames ("van dijk" → "virgil-van-dijk")
   - Shorten first names ("Nicolas" → "nico", "Christopher" → "chris")
   - Handle Jr./Sr. suffixes ("vinicius-junior" or "vinicius-jr")

**Input Format:**
Database Name: "Last, First"
Attempted URL: failed_url (for context)

**Output Requirements:**
- Comma-separated variants ONLY
- No numbering or additional text
- Order by likelihood (most common first)
- 5-8 variations total

**Example Input:**
Database Name: Fernandez, Bruno
Attempted URL: bruno-fernandez

**Example Output:**
bruno-fernandez-jr,bruno-f,fernandez-bruno,b-fernandez,bruno-fernandez-sr

**Current Input to Process:**
Database Name: {player_name}
Attempted URL: {player_formatted_name}

**Your Output (ONLY COMMA-SEPARATED SLUGS):**"""
    response = ds.create_chat_completion(prompt)
    print("Connection: ", conn)
    print("Response: ", response)
    potential_namings = response.split(",")
    print(potential_namings)
    for name in potential_namings:
        print("Processing name: ", name)
        data = scrape_player_ratings(name)
        if data.status_code == 404:
            print(f"No data found for {name}")
            set_no_ai_data_flag(player_id, True, conn)
            continue
        elif data.url == f"https://www.fifaratings.com/{name}":
            print(f"Data found for {name}")
            parsed_data = parse_html_to_json(data)
            print(parsed_data)
            add_player_ratings_to_db(player_id, player_name, name, parsed_data, conn) 
            set_no_ai_data_flag(player_id, False, conn)
            break
    return 0

def process_players(conn):
    players = get_players_with_no_data(conn)
    ds = DeepSeekAPI()
    players_left_to_process = len(players)
    for player in players:
        print("Players left to process: ", players_left_to_process)
        player_id = player[0]
        player_name = player[1]
        player_formatted_name = player[2]
        print(f"Processing player {player_name} with formatted name {player_formatted_name}")
        if player[49] == 1 or player[51] == 1:
            print("This player has no data and has already been confirmed, either manually or with AI")
            players_left_to_process -= 1
            continue
        else:
            scrape_and_process_player(ds, player_name, player_formatted_name, player_id, conn)
            players_left_to_process -= 1
            print("Player processed")
        
if __name__ == "__main__":
    conn = sqlite3.connect('v2db.sqlite')
    process_players(conn)
    conn.close()
