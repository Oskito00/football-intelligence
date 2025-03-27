import json
import re
import sqlite3
import requests
from bs4 import BeautifulSoup
import random

from Fifa_Ratings.utils.helpers import check_if_player_exists
from Tools.player_name_formatting_helper import format_player_name, normalise_player_name

#********************************************************************************
#MAIN FUNCTION
#********************************************************************************

def process_player_ratings(conn):
    cursor = conn.cursor()

    season_ids = [
        'sr:season:118693', 'sr:season:118961', 'sr:season:120759',
        'sr:season:118713', 'sr:season:119835', 'sr:season:118689',
        'sr:season:118975'
    ]

    placeholders = ','.join(['?'] * len(season_ids))
    query = f"""
        SELECT home_team_lineup_info, away_team_lineup_info 
        FROM matches
        WHERE competition_season_id IN ({placeholders})
    """
    
    # Fetch all matches at once
    all_matches = cursor.execute(query, season_ids).fetchall()
    print(f"Found {len(all_matches)} matches to process")
    
    print("Total matches:", len(all_matches))
    
    for match_idx, match in enumerate(all_matches, 1):
        try:
            # Handle potential None values in lineup info
            home_lineup_json = match[0] or '[]'  # Default to empty array if None
            away_lineup_json = match[1] or '[]'
            
            home_team_lineup_info = json.loads(home_lineup_json)
            away_team_lineup_info = json.loads(away_lineup_json)
            
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Skipping match {match_idx} due to invalid lineup data: {str(e)}")
            continue
        
        print(f"\nProcessing match {match_idx}/{len(all_matches)}")

        # Process home team players
        for player in home_team_lineup_info:
            player_id = player.get("id")
            player_name = player.get("name")
            player_name = normalise_player_name(player_name)
            player_formatted_name = format_player_name(player_name)
            
            # Check if player exists in database
            if check_if_player_exists(player_id, conn):
                print(f"Player {player_id} already exists in database")
                continue

            else:
                print(f"Scraping player {player_id} {player_name}")
                response = scrape_player_ratings(player_formatted_name)
                print(f"Parsing player {player_id} {player_name}")
                data = parse_html_to_json(response)
                print("Data for player: ", data)
                print(f"Adding player {player_id} {player_name} to database")
                add_player_ratings_to_db(player_id, player_name, player_formatted_name, data)
        
        # Process away team players
        for player in away_team_lineup_info:
            player_id = player.get("id")
            player_name = player.get("name")
            player_formatted_name = format_player_name(player_name)

            # Check if player exists in database
            cursor.execute("SELECT 1 FROM player_stats WHERE player_id = ?", (player_id,))
            if cursor.fetchone():
                print(f"Player {player_id} already exists in database")
                continue

            else:
                print(f"Scraping player {player_id} {player_name}")
                response = scrape_player_ratings(player_formatted_name)
                print(f"Parsing player {player_id} {player_name}")
                data = parse_html_to_json(response)
                print("Data for player: ", data)
                print(f"Adding player {player_id} {player_name} to database")
                add_player_ratings_to_db(player_id, player_name, player_formatted_name, data)

        # Commit after each match to prevent memory issues
        conn.commit()

#********************************************************************************
# Helper Functions
#********************************************************************************

def scrape_player_ratings(player_name):
    """Takes a player name and returns the html
    response after scraping the fifa ratings website"""
    
    try:

        base_url = "https://www.fifaratings.com"
        url = f"{base_url}/{player_name}"

        user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/118.0'
        ]

        headers = {
        'User-Agent': random.choice(user_agents),
        'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/'
        }

        print(f"Scraping player {player_name}")
        response = requests.get(url, headers=headers)

    except Exception as e:
        print(f"Error fetching player ratings: {e}")
        return None

    return response

def parse_html_to_json(response):
    """Parse HTML response to JSON data"""
    try:
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        data = {}

        print("Parsing html response to JSON")
        
        # Extract main attributes container
        statistics_selector = "#nav-attributes > div"
        statistics_content = soup.select_one(statistics_selector)

        player_attributes = soup.find('div', class_="header-subtitle")
        if player_attributes:
            # print(height_content)
            for ps in player_attributes.find_all('p'):
                text = ps.get_text(strip=True)
                if text.startswith("Height"):
                    split_text = text.split("|")
                    height_string = split_text[0].split(" ")
                    weight_string = split_text[1].split(" ")
                    height_info = re.sub(r'[()]', '', height_string[2])
                    weight_info= weight_string[0].split(":")[1]
                    data["Height"] = height_info
                    data["Weight"] = weight_info
                if text.startswith("Skill Moves:"):
                    number_of_stars = len(ps.find_all('span', class_='text-warning'))
                    data["Skill Moves"] = number_of_stars
            
        if statistics_content:
            # Process each attribute category card
            for card in statistics_content.select('.card'):
                category_header = card.select_one('.card-header h5')
                if not category_header:
                    continue
                    
                # Extract category name and average
                category_text = category_header.get_text(strip=True)
                avg_value = category_header.select_one('.attribute-box').get_text(strip=True)
                category_name = category_text.replace(avg_value, '').strip()
                data[f"{category_name} Average"] = avg_value
                
                # Process individual attributes
                for li in card.select('li'):
                    attr_text = li.get_text(strip=True)
                    attr_value = li.select_one('.attribute-box').get_text(strip=True)
                    attr_name = attr_text.replace(attr_value, '').strip()
                    data[attr_name] = attr_value

                # Need to extract skill moves

        return data
        
    except Exception as e:
        print(f"Error parsing HTML: {str(e)}")
        return None

def add_player_ratings_to_db(player_id, player_name, player_formatted_name, data):
    """Adds the players rating to the sqlite database"""
    conn = sqlite3.connect('v2db.sqlite')

    print("Adding player to database: ", player_id, player_name, player_formatted_name)
    
    try:
        conn.execute('''
            INSERT OR REPLACE INTO player_stats (
                player_id, player_name, player_formatted_name, height, weight,
                pace_avg, acceleration, sprint_speed,
                shooting_avg, positioning, finishing, shot_power, long_shots, volleys, penalties,
                passing_avg, vision, crossing, free_kick_accuracy, short_passing, long_passing, curve,
                dribbling_avg, agility, reactions, balance, dribbling, ball_control, composure,
                defense_avg, interceptions, heading_accuracy, def_awareness, standing_tackle, sliding_tackle,
                physicality_avg, jumping, stamina, strength, aggression,
                goalkeeping_avg, gk_diving, gk_handling, gk_kicking, gk_positioning, gk_reflexes, skill_moves,
                total_attributes
            ) VALUES (
                ?,?,?,?,?,?,?,?,?,?,?,?,
                ?,?,?,?,?,?,?,?,?,?,?,?,
                ?,?,?,?,?,?,?,?,?,?,?,?,
                ?,?,?,?,?,?,?,?,?,?,?,?
            )
        ''', (
            # First 12 parameters
            player_id, player_name, player_formatted_name,
            data.get('Height', 0),
            data.get('Weight', 0),
            data.get('Pace Average Average', 0),
            data.get('Acceleration', 0),
            data.get('Sprint Speed', 0),
            data.get('Shooting Average Average', 0),
            data.get('Positioning', 0),
            data.get('Finishing', 0),
            data.get('Shot Power', 0),
            data.get('Long Shots', 0),
            data.get('Volleys', 0),
            data.get('Penalties', 0),
            
            # Next 11 parameters
            data.get('Passing Average Average', 0),
            data.get('Vision', 0),
            data.get('Crossing', 0),
            data.get('Free Kick Accuracy', 0),
            data.get('Short Passing', 0),
            data.get('Long Passing', 0),
            data.get('Curve', 0),
            data.get('Dribbling Average Average', 0),
            data.get('Agility', 0),
            data.get('Reactions', 0),
            data.get('Balance', 0),
            
            # Next 11 parameters
            data.get('Dribbling', 0),
            data.get('Ball Control', 0),
            data.get('Composure', 0),
            data.get('Defense Average Average', 0),
            data.get('Interceptions', 0),
            data.get('Heading Accuracy', 0),
            data.get('Def Awareness', 0),
            data.get('Standing Tackle', 0),
            data.get('Sliding Tackle', 0),
            data.get('Physicality Average Average', 0),
            data.get('Jumping', 0),
            
            # Final 11 parameters
            data.get('Stamina', 0),
            data.get('Strength', 0),
            data.get('Aggression', 0),
            data.get('Goalkeeping Average Average', 0),
            data.get('GK Diving', 0),
            data.get('GKH andling', 0),
            data.get('GK Kicking', 0),
            data.get('GK Positioning', 0),
            data.get('GK Reflexes', 0),
            data.get('Skill Moves', 0),
            data.get('Total Attributes Average', 0).replace(',', '') if 'Total Attributes Average' in data else 0,
        ))
        conn.commit()
        print("Player added to database")
    except KeyError as e:
        print(f"Missing key in data: {e}")
    except sqlite3.IntegrityError as e:
        print(f"Duplicate entry for {player_id}: {e}")
    except Exception as e:
        print(f"Error saving {player_id}: {e}")
        conn.rollback()
    finally:
        conn.close()  # Always close connection



conn = sqlite3.connect('v2db.sqlite')
process_player_ratings(conn)


