import os
from dotenv import load_dotenv
import requests
import json
from pathlib import Path
import time

load_dotenv()

def get_season_matches(season_id, competition_name, season_name):
    """
    Fetch all matches for a specific season using the Sportradar API
    
    Args:
        season_id (str): The Sportradar season ID
        competition_name (str): Name of the competition
        season_name (str): Name of the season
        
    Returns:
        dict: JSON response containing season's match schedule data if successful, None otherwise
    """
    # Get API key from environment variables
    api_key = os.getenv('SPORTRADAR_API_KEY')
    
    try:
        print(f"\nFetching matches for {competition_name} - {season_name} (ID: {season_id})")
        
        all_summaries = []
        offset = 0
        limit = 100  # API seems to enforce 100 as max per page
        
        while True:
            # Define the API URL with pagination
            api_url = f"https://api.sportradar.com/soccer-extended/trial/v4/en/seasons/{season_id}/summaries.json"
            
            # Add pagination parameters
            params = {
                'api_key': api_key,
                'offset': offset,
                'limit': limit
            }
            
            # Add delay before request to respect rate limits
            time.sleep(1.1)
            
            # Fetch the data
            print(f"Fetching matches with offset {offset}...")
            response = requests.get(api_url, params=params)
            response.raise_for_status()
            
            # Parse JSON data
            data = response.json()
            
            # Get summaries from this batch
            summaries = data.get("summaries", [])
            batch_size = len(summaries)
            
            if batch_size == 0:  # No more matches to fetch
                break
                
            all_summaries.extend(summaries)
            
            # Get total available from headers
            max_results = int(response.headers.get('X-Max-Results', 0))
            print(f"Fetched {batch_size} matches (total so far: {len(all_summaries)} of {max_results})")
            
            # Always increment offset by actual batch size
            offset += 100
            
            # If we've fetched all available matches, we're done
            if len(all_summaries) >= max_results:
                break
        
        print(f"Total matches fetched: {len(all_summaries)}")
        
        # Create complete response
        complete_data = {
            "generated_at": data.get("generated_at"),
            "summaries": all_summaries
        }
        
        # Save to file
        output_dir = Path.cwd() / 'sportradar' / 'data' / 'matches_data2'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        clean_comp_name = competition_name.replace(' ', '_')
        clean_season_name = season_name.replace(' ', '_').replace('/', '_')
        
        output_file = output_dir / f"{clean_comp_name}_{clean_season_name}_{season_id}.json"
        with open(output_file, "w") as file:
            json.dump(complete_data, file, indent=4)
        
        print(f"Data saved to {output_file}")
        return complete_data
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {competition_name} - {season_name} (ID: {season_id}): {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON for {competition_name} - {season_name} (ID: {season_id}): {e}")
        return None

def scrape_all_seasons():
    """Scrape matches for all seasons in top_seasons.json"""
    # Load the seasons data
    with open('sportradar/data/top_seasons.json', 'r') as f:
        competitions = json.load(f)
    
    for competition_name, competition_data in competitions.items():
        print(f"\nProcessing {competition_name}...")
        
        for season in competition_data['seasons']:
            season_id = season['id']
            season_name = season['name'].replace('/', '_')  # Replace / with _ for filename
            
            # Get matches for the season
            season_data = get_season_matches(season_id, competition_name, season_name)
            
            if season_data:
                print(f"Successfully fetched {competition_name} - {season_name}")
            else:
                print(f"Failed to fetch data for {competition_name} - {season_name}")

if __name__ == "__main__":
    scrape_all_seasons()