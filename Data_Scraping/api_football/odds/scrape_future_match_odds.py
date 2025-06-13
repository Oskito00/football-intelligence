import os
import requests
import psycopg2
from datetime import datetime
from time import sleep
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from functools import partial

from config import get_config
from utils.database_helpers.create_tables import create_odds_table
from utils.database_helpers.get_and_set_functions import get_future_matches_with_odds

config = get_config()

# Target bookmakers: Betfair, Bwin, William Hill, Bet365, Betfred
TARGET_BOOKMAKERS = [3, 6, 7, 8, 12]

# Thread-safe counter for API calls
api_call_lock = threading.Lock()
api_call_count = 0

def fetch_odds_for_match_and_bet(match_id: int, bet_type: int, max_retries: int = 3) -> Dict[str, Any]:
    """Fetch odds for a specific match and bet type from the API"""
    global api_call_count
    
    api_key = config.API_FOOTBALL_KEY
    url = "https://v3.football.api-sports.io/odds"
    
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "v3.football.api-sports.io"
    }
    
    params = {
        "fixture": match_id,
        "bet": bet_type
    }
    
    for attempt in range(max_retries):
        try:
            with api_call_lock:
                api_call_count += 1
                current_call = api_call_count
            
            print(f"  🌐 API call #{current_call}: Match {match_id}, Bet {bet_type} (attempt {attempt + 1})")
            
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if data.get('errors'):
                error_msg = str(data['errors'])
                if 'requests' in error_msg.lower() and 'limit' in error_msg.lower():
                    print(f"❌ API request limit reached: {error_msg}")
                    return None
                print(f"❌ API error for match {match_id}, bet {bet_type}: {error_msg}")
                return None
                
            print(f"  ✅ Success: Match {match_id}, Bet {bet_type}")
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed for match {match_id}, bet {bet_type} (attempt {attempt + 1}): {str(e)}")
            if attempt < max_retries - 1:
                sleep(2 ** attempt)  # Exponential backoff
            else:
                return None
    
    return None

def fetch_all_odds_for_match(match_id: int, bet_types: List[int] = [1, 5, 8], max_workers: int = 3) -> List[Dict[str, Any]]:
    """Fetch odds for all bet types for a match using concurrent requests"""
    all_responses = []
    
    # Create partial function with match_id
    fetch_func = partial(fetch_odds_for_match_and_bet, match_id)
    
    # Use ThreadPoolExecutor to make concurrent requests
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all bet type requests
        future_to_bet = {executor.submit(fetch_func, bet_type): bet_type for bet_type in bet_types}
        
        # Collect results as they complete
        for future in as_completed(future_to_bet):
            bet_type = future_to_bet[future]
            try:
                result = future.result()
                if result:
                    all_responses.append(result)
            except Exception as e:
                print(f"❌ Exception for match {match_id}, bet {bet_type}: {str(e)}")
    
    return all_responses

def parse_odds_data(api_responses: List[Dict[str, Any]], match_id: int) -> List[Dict[str, Any]]:
    """Parse odds data from multiple API responses, filtering for target bookmakers"""
    odds_records = []
    bookmaker_count = 0
    bet_type_breakdown = {}
    filtered_bookmaker_count = 0
    
    for api_response in api_responses:
        if not api_response or not api_response.get('response'):
            continue
            
        response_data = api_response['response']
        
        for match_data in response_data:
            if match_data['fixture']['id'] != match_id:
                continue
                
            api_last_updated = match_data.get('update')
            bookmakers = match_data.get('bookmakers', [])
            
            if not bookmaker_count:  # Only count once
                bookmaker_count = len(bookmakers)
            
            for bookmaker in bookmakers:
                bookmaker_id = bookmaker['id']
                bookmaker_name = bookmaker['name']
                
                # Filter to only target bookmakers
                if bookmaker_id not in TARGET_BOOKMAKERS:
                    continue
                
                if bookmaker_id not in [b['bookmaker_id'] for b in odds_records]:
                    filtered_bookmaker_count += 1
                
                for bet in bookmaker.get('bets', []):
                    bet_type_id = bet['id']
                    bet_type_name = bet['name']
                    
                    # Track bet type breakdown
                    if bet_type_id not in bet_type_breakdown:
                        bet_type_breakdown[bet_type_id] = {
                            'name': bet_type_name,
                            'values': len(bet.get('values', []))
                        }
                    
                    for value in bet.get('values', []):
                        odds_records.append({
                            'match_id': match_id,
                            'bookmaker_id': bookmaker_id,
                            'bookmaker_name': bookmaker_name,
                            'bet_type_id': bet_type_id,
                            'bet_type_name': bet_type_name,
                            'bet_value': value['value'],
                            'odds_value': float(value['odd']),
                            'api_last_updated': api_last_updated
                        })
    
    # Print breakdown
    print(f"  📊 Match {match_id} breakdown:")
    print(f"     Total bookmakers available: {bookmaker_count}")
    print(f"     Target bookmakers found: {filtered_bookmaker_count}")
    for bet_id, bet_info in bet_type_breakdown.items():
        print(f"     Bet {bet_id} ({bet_info['name']}): {bet_info['values']} values")
    print(f"     Final records: {len(odds_records)}")
    
    return odds_records

def process_matches_batch(match_ids: List[int], max_workers: int = 2) -> List[Dict[str, Any]]:
    """Process multiple matches concurrently with individual match progress"""
    all_odds_records = []
    
    print(f"   🔄 Starting concurrent processing of {len(match_ids)} matches...")
    
    # Process matches concurrently (but limit to avoid overwhelming API)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all match processing jobs
        future_to_match = {
            executor.submit(fetch_all_odds_for_match, match_id): match_id 
            for match_id in match_ids
        }
        
        completed_count = 0
        
        # Collect results as they complete
        for future in as_completed(future_to_match):
            match_id = future_to_match[future]
            completed_count += 1
            
            try:
                print(f"   🏁 [{completed_count}/{len(match_ids)}] Processing match {match_id}...")
                api_responses = future.result()
                
                if not api_responses:
                    print(f"   ❌ [{completed_count}/{len(match_ids)}] No responses for match {match_id}")
                    continue
                
                # Parse odds data
                odds_records = parse_odds_data(api_responses, match_id)
                
                if odds_records:
                    all_odds_records.extend(odds_records)
                    print(f"   ✅ [{completed_count}/{len(match_ids)}] Match {match_id}: {len(odds_records)} records")
                else:
                    print(f"   ⚠️  [{completed_count}/{len(match_ids)}] Match {match_id}: No odds found")
                    
            except Exception as e:
                print(f"   ❌ [{completed_count}/{len(match_ids)}] Exception processing match {match_id}: {str(e)}")
    
    print(f"   🏁 Batch processing complete: {len(all_odds_records)} total records collected")
    return all_odds_records

def bulk_insert_odds(conn, odds_records: List[Dict[str, Any]]) -> int:
    """Bulk insert odds records using execute_values for better performance"""
    if not odds_records:
        return 0
    
    cursor = conn.cursor()
    
    try:
        from psycopg2.extras import execute_values
        
        # Prepare the data as tuples
        values = [
            (
                record['match_id'],
                record['bookmaker_id'], 
                record['bookmaker_name'],
                record['bet_type_id'],
                record['bet_type_name'],
                record['bet_value'],
                record['odds_value'],
                record['api_last_updated']
            )
            for record in odds_records
        ]
        
        insert_query = """
        INSERT INTO odds (
            match_id, bookmaker_id, bookmaker_name, bet_type_id, 
            bet_type_name, bet_value, odds_value, api_last_updated
        ) VALUES %s
        """
        
        execute_values(cursor, insert_query, values, page_size=1000)
        conn.commit()
        
        rows_inserted = len(values)
        cursor.close()
        return rows_inserted
        
    except Exception as e:
        print(f"❌ Error bulk inserting odds: {str(e)}")
        conn.rollback()
        cursor.close()
        return 0

def scrape_future_match_odds(match_batch_size: int = 5, max_workers_per_match: int = 3, max_workers_matches: int = 2):
    """Main function with concurrent processing and 7-day window filtering"""
    print("🚀 Starting concurrent odds scraping for future matches...")
    print(f"🎯 Target bookmakers: {TARGET_BOOKMAKERS}")
    print("📅 Filtering to matches in next 7 days (API recommendation)")
    
    # Connect to database
    conn = psycopg2.connect(
        host=config.DB_HOST,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD
    )
    
    try:
        # Create odds table if it doesn't exist
        create_odds_table(conn)
        
        # Get future matches with odds (within 7 days)
        match_ids = get_future_matches_with_odds(conn)
        total_matches = len(match_ids)
        print(f"📋 Found {total_matches} future matches with odds available (next 7 days)")
        
        # Also show total future matches for context
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM matches 
            WHERE has_odds = TRUE 
            AND home_score IS NULL 
            AND away_score IS NULL 
            AND start_time > NOW()
        """)
        total_future_matches = cursor.fetchone()[0]
        cursor.close()
        
        if total_future_matches > total_matches:
            print(f"📊 (Note: {total_future_matches - total_matches} additional matches beyond 14 days not included)")
        
        if not match_ids:
            print("❌ No matches to process in the next 7 days")
            return
        
        # Calculate batch info
        total_batches = (total_matches + match_batch_size - 1) // match_batch_size
        print(f"📦 Will process in {total_batches} batches of {match_batch_size} matches each")
        
        # Process matches in batches
        all_odds_records = []
        total_processed = 0
        successful_matches = 0
        failed_matches = 0
        
        for i in range(0, total_matches, match_batch_size):
            batch = match_ids[i:i + match_batch_size]
            current_batch_num = i // match_batch_size + 1
            
            print(f"\n📦 Batch {current_batch_num}/{total_batches}: Processing matches {batch}")
            print(f"📊 Overall progress: {total_processed}/{total_matches} matches completed ({total_processed/total_matches*100:.1f}%)")
            
            # Process this batch concurrently
            batch_odds = process_matches_batch(batch, max_workers_matches)
            
            # Count successful vs failed matches in this batch
            batch_successful = 0
            for match_id in batch:
                match_records = [r for r in batch_odds if r['match_id'] == match_id]
                if match_records:
                    batch_successful += 1
                else:
                    failed_matches += 1
            
            successful_matches += batch_successful
            
            if batch_odds:
                all_odds_records.extend(batch_odds)
                print(f"✅ Batch {current_batch_num} completed: {len(batch_odds)} records from {batch_successful}/{len(batch)} matches")
            else:
                print(f"❌ Batch {current_batch_num} failed: 0 records from 0/{len(batch)} matches")
            
            total_processed += len(batch)
            
            # Show running totals
            print(f"🎯 Running totals: {successful_matches} successful, {failed_matches} failed, {total_processed}/{total_matches} processed")
            
            # Save periodically
            if len(all_odds_records) >= 1000 or i + match_batch_size >= total_matches:
                if all_odds_records:
                    print(f"💾 Bulk inserting {len(all_odds_records)} odds records...")
                    saved_count = bulk_insert_odds(conn, all_odds_records)
                    print(f"✅ Successfully inserted {saved_count} records to database")
                    all_odds_records = []  # Clear
            
            # Small delay between batches to be respectful
            if i + match_batch_size < total_matches:
                print("⏳ Waiting 2 seconds before next batch...")
                sleep(2)
        
        # Final summary
        print("\n🎉 SCRAPING COMPLETED!")
        print("📊 Final Results:")
        print(f"   • Total matches in 7-day window: {total_matches}")
        print(f"   • Successful matches: {successful_matches}")
        print(f"   • Failed matches: {failed_matches}")
        print(f"   • Success rate: {successful_matches/total_matches*100:.1f}%")
        print(f"   • Total API calls made: {api_call_count}")
        
    except Exception as e:
        print(f"❌ Error during scraping: {str(e)}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    # Adjust these parameters based on your needs and API limits
    scrape_future_match_odds(
        match_batch_size=5,        # Process 5 matches at a time
        max_workers_per_match=3,   # 3 concurrent requests per match (for 3 bet types)
        max_workers_matches=2      # 2 matches processed simultaneously
    )