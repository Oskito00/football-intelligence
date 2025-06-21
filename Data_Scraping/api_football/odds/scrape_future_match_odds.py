import requests
import psycopg2
from datetime import datetime
from time import sleep

from config import get_config
from utils.database.create_tables import create_odds_table
from utils.database.get_and_set_functions import get_future_matches_with_odds

config = get_config()

# Target bookmakers: Betfair, Bwin, William Hill, Bet365, Betfred
TARGET_BOOKMAKERS = [3, 6, 7, 8, 12]

def fetch_odds_for_match(match_id: int) -> dict:
    """Fetch odds for a specific match from the API"""
    url = "https://v3.football.api-sports.io/odds"
    headers = {
        "x-rapidapi-key": config.API_FOOTBALL_KEY,
        "x-rapidapi-host": "v3.football.api-sports.io"
    }
    
    # We only want match winner odds (bet_type=1)
    params = {
        "fixture": match_id,
        "bet": 1
    }
    
    try:
        print(f"  🌐 Fetching odds for match {match_id}")
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('errors'):
            print(f"❌ API error for match {match_id}: {data['errors']}")
            return None
            
        print(f"  ✅ Success: Match {match_id}")
        return data
        
    except Exception as e:
        print(f"❌ Error fetching odds for match {match_id}: {str(e)}")
        return None

def parse_odds_data(api_response: dict, match_id: int) -> list:
    """Parse odds data from API response, filtering for target bookmakers"""
    odds_records = []
    
    if not api_response or not api_response.get('response'):
        return odds_records
        
    response_data = api_response['response']
    
    for match_data in response_data:
        if match_data['fixture']['id'] != match_id:
            continue
            
        api_last_updated = match_data.get('update')
        bookmakers = match_data.get('bookmakers', [])
        
        for bookmaker in bookmakers:
            bookmaker_id = bookmaker['id']
            
            # Skip if not in our target bookmakers
            if bookmaker_id not in TARGET_BOOKMAKERS:
                continue
                
            for bet in bookmaker.get('bets', []):
                for value in bet.get('values', []):
                    odds_records.append({
                        'match_id': match_id,
                        'bookmaker_id': bookmaker_id,
                        'bookmaker_name': bookmaker['name'],
                        'bet_type_id': bet['id'],
                        'bet_type_name': bet['name'],
                        'bet_value': value['value'],
                        'odds_value': float(value['odd']),
                        'api_last_updated': api_last_updated
                    })
    
    return odds_records

def save_odds_to_db(conn, odds_records: list):
    """Save odds records to database"""
    if not odds_records:
        return 0
    
    cursor = conn.cursor()
    rows_inserted = 0
    
    try:
        for record in odds_records:
            cursor.execute("""
                INSERT INTO odds (
                    match_id, bookmaker_id, bookmaker_name, bet_type_id, 
                    bet_type_name, bet_value, odds_value, api_last_updated
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                record['match_id'],
                record['bookmaker_id'],
                record['bookmaker_name'],
                record['bet_type_id'],
                record['bet_type_name'],
                record['bet_value'],
                record['odds_value'],
                record['api_last_updated']
            ))
            rows_inserted += 1
        
        conn.commit()
        return rows_inserted
        
    except Exception as e:
        print(f"❌ Error saving odds: {str(e)}")
        conn.rollback()
        return 0
    finally:
        cursor.close()

def scrape_future_match_odds():
    """Main function to scrape odds for future matches"""
    print("🚀 Starting odds scraping for future matches...")
    print(f"🎯 Target bookmakers: {TARGET_BOOKMAKERS}")
    
    conn = psycopg2.connect(
        host=config.DB_HOST,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD
    )
    
    try:
        # Create odds table if it doesn't exist
        create_odds_table(conn)
        
        # Get future matches
        match_ids = get_future_matches_with_odds(conn)
        print(f"📋 Found {len(match_ids)} future matches to process")
        
        successful_matches = 0
        failed_matches = 0
        total_odds_saved = 0
        
        # Process each match
        for i, match_id in enumerate(match_ids, 1):
            print(f"\n⚽ Processing match {i}/{len(match_ids)}: {match_id}")
            
            # Get odds data
            odds_data = fetch_odds_for_match(match_id)
            
            if odds_data:
                # Parse odds
                odds_records = parse_odds_data(odds_data, match_id)
                
                if odds_records:
                    # Save to database
                    saved_count = save_odds_to_db(conn, odds_records)
                    if saved_count > 0:
                        successful_matches += 1
                        total_odds_saved += saved_count
                        print(f"✅ Saved {saved_count} odds for match {match_id}")
                    else:
                        failed_matches += 1
                        print(f"❌ Failed to save odds for match {match_id}")
                else:
                    failed_matches += 1
                    print(f"⚠️ No valid odds found for match {match_id}")
            else:
                failed_matches += 1
            
            # Be nice to the API
            # sleep(1)
        
        # Final summary
        print("\n🎉 SCRAPING COMPLETED!")
        print(f"📊 Results:")
        print(f"   • Total matches processed: {len(match_ids)}")
        print(f"   • Successful matches: {successful_matches}")
        print(f"   • Failed matches: {failed_matches}")
        print(f"   • Total odds records saved: {total_odds_saved}")
        
    except Exception as e:
        print(f"❌ Error during scraping: {str(e)}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    scrape_future_match_odds()