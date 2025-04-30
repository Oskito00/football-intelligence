import json
import sqlite3
import time

from helpers.data_scraping.scrape_formation import get_fixture_lineups


def process_lineup_data(api_response):
    if not api_response.get('response') or len(api_response['response']) != 2:
        return None, None, None, None
    
    home_data = api_response['response'][0]
    away_data = api_response['response'][1]
    
    # Validate structure
    required_keys = {'formation', 'startXI', 'team'}
    if not all(key in home_data for key in required_keys) or \
       not all(key in away_data for key in required_keys):
        return None, None, None, None
    
    return (
        home_data['formation'],
        away_data['formation'],
        json.dumps(home_data),
        json.dumps(away_data)
    )

def update_match_lineups(conn):
    cur = conn.cursor()
    
    cur.execute("SELECT match_id FROM matches WHERE attempted_formation_scrape = 0")
    match_ids = [row[0] for row in cur.fetchall()]

    print(f"Found {len(match_ids)} matches to update")
    
    for match_id in match_ids:
        try:
            data = get_fixture_lineups(match_id)
            home_form, away_form, home_lineup, away_lineup = process_lineup_data(data)
            print(f"Processed match {match_id}")
            
            cur.execute("""
                UPDATE matches
                SET home_team_formation = COALESCE(?, home_team_formation),
                    away_team_formation = COALESCE(?, away_team_formation),
                    home_team_lineup = COALESCE(?, home_team_lineup),
                    away_team_lineup = COALESCE(?, away_team_lineup),
                    attempted_formation_scrape = 1
                WHERE match_id = ?
            """, (home_form, away_form, home_lineup, away_lineup, match_id))
            
            conn.commit()
            time.sleep(0)  # Maintain rate limit
            
        except Exception as e:
            print(f"Error processing match {match_id}: {str(e)}")
            conn.rollback()
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    conn = sqlite3.connect('api_football.db')
    update_match_lineups(conn)
    conn.close()