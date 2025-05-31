import http.client
from datetime import datetime, timedelta
import urllib.parse
import json
import sqlite3
from statistics import mean
import time

COMPETITION_LIST_FOR_ODDS_API = ["soccer_epl","soccer_spain_la_liga","soccer_germany_bundesliga","soccer_italy_serie_a","soccer_france_ligue_one","soccer_uefa_champs_league","soccer_uefa_europa_league","soccer_uefa_europa_conference_league","soccer_fa_cup","soccer_england_efl_cup"]


def process_odds_data(json_data):
    # Parse JSON data
    data = json.loads(json_data)
    
    # Create SQLite connection
    conn = sqlite3.connect('odds.db')
    cursor = conn.cursor()
    
    # Create table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS match_odds (
        competition TEXT,
        home_team TEXT,
        away_team TEXT,
        start_time TEXT,
        home_win_odds REAL,
        draw_odds REAL,
        away_win_odds REAL,
        UNIQUE(competition, home_team, away_team, start_time)
    )
    ''')
    
    # Process each match
    for match in data:
        competition = match['sport_title']
        home_team = match['home_team']
        away_team = match['away_team']
        start_time = match['commence_time']
        
        # Calculate new odds
        home_odds = []
        draw_odds = []
        away_odds = []
        
        for bookmaker in match['bookmakers']:
            for market in bookmaker['markets']:
                if market['key'] == 'h2h':
                    for outcome in market['outcomes']:
                        if outcome['name'] == home_team:
                            home_odds.append(outcome['price'])
                        elif outcome['name'] == away_team:
                            away_odds.append(outcome['price'])
                        elif outcome['name'] == 'Draw':
                            draw_odds.append(outcome['price'])
        
        # Calculate average odds
        avg_home_odds = mean(home_odds) if home_odds else None
        avg_draw_odds = mean(draw_odds) if draw_odds else None
        avg_away_odds = mean(away_odds) if away_odds else None
        
        # Check if match exists and compare odds
        cursor.execute('''
        SELECT home_win_odds, draw_odds, away_win_odds 
        FROM match_odds 
        WHERE competition = ? 
        AND home_team = ? 
        AND away_team = ? 
        AND start_time = ?
        ''', (competition, home_team, away_team, start_time))
        
        existing_match = cursor.fetchone()
        
        if existing_match:
            # Compare with tolerance to avoid floating point comparison issues
            tolerance = 0.001
            existing_home, existing_draw, existing_away = existing_match
            
            if (abs(existing_home - avg_home_odds) > tolerance or 
                abs(existing_draw - avg_draw_odds) > tolerance or 
                abs(existing_away - avg_away_odds) > tolerance):
                
                print(f"Updating odds for {home_team} vs {away_team}")
                print(f"Old odds: {existing_home:.2f} / {existing_draw:.2f} / {existing_away:.2f}")
                print(f"New odds: {avg_home_odds:.2f} / {avg_draw_odds:.2f} / {avg_away_odds:.2f}\n")
                
                cursor.execute('''
                UPDATE match_odds 
                SET home_win_odds = ?, draw_odds = ?, away_win_odds = ?
                WHERE competition = ? 
                AND home_team = ? 
                AND away_team = ? 
                AND start_time = ?
                ''', (avg_home_odds, avg_draw_odds, avg_away_odds, 
                     competition, home_team, away_team, start_time))
        else:
            # Insert new match
            print(f"Adding new match: {home_team} vs {away_team}")
            print(f"Odds: {avg_home_odds:.2f} / {avg_draw_odds:.2f} / {avg_away_odds:.2f}\n")
            
            cursor.execute('''
            INSERT INTO match_odds 
            (competition, home_team, away_team, start_time, home_win_odds, draw_odds, away_win_odds)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (competition, home_team, away_team, start_time, 
                 avg_home_odds, avg_draw_odds, avg_away_odds))
    
    # Commit and close
    conn.commit()
    conn.close()

#********************************************************************************
#API CALLS
#********************************************************************************

def get_odds(sport):
    """Fetch odds from the-odds-api.com for a specific sport."""
    
    # API configuration
    API_KEY = "8d5d21a9ae89fc4766102c64c0880cd7"
    
    # Calculate date range (today to 7 days from now)
    today = datetime.utcnow()
    next_week = today + timedelta(days=7)
    
    # Set up parameters
    params = {
        "apiKey": API_KEY,
        "regions": "uk",
        "markets": "h2h",
        "dateFormat": "iso",
        "oddsFormat": "decimal",
        "commenceTimeFrom": today.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commenceTimeTo": next_week.strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    
    # Encode parameters
    encoded_params = urllib.parse.urlencode(params)
    
    # Set up connection
    conn = http.client.HTTPSConnection("api.the-odds-api.com")
    
    # Make request
    endpoint = f"/v4/sports/{sport}/odds?{encoded_params}"
    conn.request("GET", endpoint)
    
    # Get response
    res = conn.getresponse()
    data = res.read()
    
    # Check response headers for remaining requests
    remaining = res.getheader('X-Requests-Remaining')
    if remaining:
        print(f"Remaining API requests: {remaining}")
    
    conn.close()
    return data.decode("utf-8")

def process_all_competitions():
    """Process odds for all competitions in the list."""
    
    print("Starting odds collection for all competitions...")
    
    # Delay between API calls (in seconds)
    API_DELAY = 1 # 5 seconds between each call
    
    for i, sport in enumerate(COMPETITION_LIST_FOR_ODDS_API, 1):
        try:
            print(f"\nFetching odds for {sport} ({i}/{len(COMPETITION_LIST_FOR_ODDS_API)})...")
            odds_data = get_odds(sport)
            process_odds_data(odds_data)
            print(f"Completed processing {sport}")
            
            # Don't delay after the last item
            if i < len(COMPETITION_LIST_FOR_ODDS_API):
                print(f"Waiting {API_DELAY} seconds before next request...")
                time.sleep(API_DELAY)
                
        except Exception as e:
            print(f"Error processing {sport}: {str(e)}")
            # Still wait before next request even if there's an error
            if i < len(COMPETITION_LIST_FOR_ODDS_API):
                time.sleep(API_DELAY)
    
    print("\nCompleted odds collection for all competitions.")

#********************************************************************************
#HELPER FUNCTIONS
#********************************************************************************

def check_match_exists(home_team, away_team, start_time):
    conn = sqlite3.connect('odds.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT * FROM match_odds 
    WHERE home_team = ? 
    AND away_team = ? 
    AND start_time = ?
    ''', (home_team, away_team, start_time))
    
    match = cursor.fetchone()
    
    if match:
        print(f"\nMatch found:")
        print(f"Competition: {match[0]}")
        print(f"Home Team: {match[1]} (odds: {match[4]:.2f})")
        print(f"Away Team: {match[2]} (odds: {match[6]:.2f})")
        print(f"Draw odds: {match[5]:.2f}")
        print(f"Start Time: {match[3]}")
    else:
        print(f"\nNo match found for {home_team} vs {away_team} at {start_time}")
    
    conn.close()
    return match is not None

if __name__ == "__main__":
    process_all_competitions()