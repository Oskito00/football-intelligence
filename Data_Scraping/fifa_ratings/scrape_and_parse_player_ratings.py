import sqlite3
import requests
from bs4 import BeautifulSoup
import random

from Tools.html_helper import read_html, save_html

def create_players_stats_table(conn):
    """Create table if not exists"""
    conn.execute('''CREATE TABLE IF NOT EXISTS player_stats (
        player_id TEXT PRIMARY KEY,
        player_name TEXT,
        -- Pace Section
        pace_avg INTEGER,
        acceleration INTEGER,
        sprint_speed INTEGER,
        
        -- Shooting Section
        shooting_avg INTEGER,
        positioning INTEGER,
        finishing INTEGER,
        shot_power INTEGER,
        long_shots INTEGER,
        volleys INTEGER,
        penalties INTEGER,
        
        -- Passing Section
        passing_avg INTEGER,
        vision INTEGER,
        crossing INTEGER,
        free_kick_accuracy INTEGER,
        short_passing INTEGER,
        long_passing INTEGER,
        curve INTEGER,
        
        -- Dribbling Section
        dribbling_avg INTEGER,
        agility INTEGER,
        reactions INTEGER,
        balance INTEGER,
        dribbling INTEGER,
        ball_control INTEGER,
        composure INTEGER,
        
        -- Defense Section
        defense_avg INTEGER,
        interceptions INTEGER,
        heading_accuracy INTEGER,
        def_awareness INTEGER,
        standing_tackle INTEGER,
        sliding_tackle INTEGER,
        
        -- Physicality Section
        physicality_avg INTEGER,
        jumping INTEGER,
        stamina INTEGER,
        strength INTEGER,
        aggression INTEGER,
        
        -- Goalkeeping Section
        goalkeeping_avg INTEGER,
        gk_diving INTEGER,
        gk_handling INTEGER,
        gk_kicking INTEGER,
        gk_positioning INTEGER,
        gk_reflexes INTEGER,
        
        -- Special Fields
        total_attributes INTEGER,
        skill_moves INTEGER,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

#********************************************************************************
#MAIN FUNCTION
#********************************************************************************

def process_player_ratings(conn):
    conn = sqlite3.connect('v2db.sqlite')
    cursor = conn.cursor()

    matches = cursor.execute("SELECT home_team_lineup_info, away_team_lineup_info FROM matches")
    for match in matches:
        print("Home Team Lineup Info: ", match[0])  # First column
        print("Away Team Lineup Info: ", match[1])  # Second column


    #For all matches
    #For all players
    #Check if they have an entry in the database
    #If they do, skip them
    #If they don't, scrape their ratings and add them to the database

conn = sqlite3.connect('v2db.sqlite')
process_player_ratings(conn)


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

        response = requests.get(url, headers=headers)

    except Exception as e:
        print(f"Error fetching player ratings: {e}")
        return None

    return response

def parse_html_to_json(response):
    """Pares the html response to a json object"""
    soup = BeautifulSoup(response, "html.parser")
    data = {}
    
    # Extract main attributes container
    statistics_selector = "#nav-attributes > div"
    statistics_content = soup.select_one(statistics_selector)

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

    # TODO: Figure out how to extract skill moves
    # skill_moves_p = soup.find('p', string=lambda t: t and 'Skill Moves:' in t)
    # if skill_moves_p:
    #     stars = skill_moves_p.find_all('span', class_='fa-star')
    #     data['Skill Moves'] = sum(1 for s in stars if 'text-warning' in s.get('class', []))
    # else:
    #     data['Skill Moves'] = 0

    return data

def add_player_ratings_to_db(player_name, player_id, data):
    """Adds the players rating to the sqlite database"""
    conn = sqlite3.connect('v2db.sqlite')
    
    try:
        conn.execute('''
            INSERT INTO player_stats (
                player_id, player_name, 
                pace_avg, acceleration, sprint_speed,
                shooting_avg, positioning, finishing, shot_power, long_shots, volleys, penalties,
                passing_avg, vision, crossing, free_kick_accuracy, short_passing, long_passing, curve,
                dribbling_avg, agility, reactions, balance, dribbling, ball_control, composure,
                defense_avg, interceptions, heading_accuracy, def_awareness, standing_tackle, sliding_tackle,
                physicality_avg, jumping, stamina, strength, aggression,
                goalkeeping_avg, gk_diving, gk_handling, gk_kicking, gk_positioning, gk_reflexes,
                total_attributes, skill_moves
            ) VALUES (
                ?,?,?,?,?,?,?,?,?,?,?,?,
                ?,?,?,?,?,?,?,?,?,?,?,
                ?,?,?,?,?,?,?,?,?,?,?,
                ?,?,?,?,?,?,?,?,
                ?,?,?
            )
        ''', (
            # First 12 parameters
            player_id, player_name,
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
            data.get('GK Handling', 0),
            data.get('GK Kicking', 0),
            data.get('GK Positioning', 0),
            data.get('GK Reflexes', 0),
            data.get('Total Attributes Average', 0).replace(',', '') if 'Total Attributes Average' in data else 0,
            data.get('Skill Moves', 0)
        ))
        conn.commit()
    except KeyError as e:
        print(f"Missing key in data: {e}")
    except sqlite3.IntegrityError as e:
        print(f"Duplicate entry for {player_id}: {e}")
    except Exception as e:
        print(f"Error saving {player_id}: {e}")
        conn.rollback()
    finally:
        conn.close()  # Always close connection






