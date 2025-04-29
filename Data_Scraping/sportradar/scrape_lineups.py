import os
import random
from dotenv import load_dotenv
import requests
import json
from pathlib import Path
import time
from urllib.parse import quote

load_dotenv()

def scrape_all_lineups():
    """Scrapes all the lineups for all the top seasons that have been identified"""

    # This is the file that contains the seasons to scrape
    with open('Data/sportradar/raw/season_info/top_seasons.json', 'r') as f:
        competitions = json.load(f)
    
    # Iterate over each competition and season
    for competition_name, competition_data in competitions.items():
        print(f"\nProcessing {competition_name}...")
        
        for season in competition_data['seasons']:
            season_id = season['id']
            season_name = season['name']
            
            # Extract lineup data for each match in the season
            season_data = get_season_lineups(season_id, competition_name, season_name)
            
            if season_data:
                print(f"Successfully fetched lineups for {competition_name} - {season_name}")
            else:
                print(f"Failed to fetch lineups for {competition_name} - {season_name}")

def get_season_lineups(season_id, competition_name, season_name):
    """
    Fetch all lineups for a specific season using the Sportradar API
    
    Args:
        season_id (str): The Sportradar season ID
        competition_name (str): Name of the competition
        season_name (str): Name of the season
        
    Returns:
        dict: JSON response containing season's lineup data if successful, None otherwise
    """
    # Get API key from .env file
    api_key = os.getenv('SPORTRADAR_API_KEY')
    
    try:
        print(f"\nFetching lineups for {competition_name} - {season_name} (ID: {season_id})")
        
        all_lineups = []
        offset = 0
        limit = 200
        
        while True:
            # API request to get lineups for all matches in the season so far
            encoded_season_id = quote(season_id)
            api_url = f"https://api.sportradar.com/soccer-extended/trial/v4/en/seasons/{encoded_season_id}/lineups.json"
            
            # Parameters for the API request
            params = {
                'api_key': api_key,
                'offset': offset,
                'limit': limit
            }
            
            # Add delay before request to respect rate limits
            time.sleep(1.1)
            
            # Fetch the data
            print(f"Fetching lineups with offset {offset}...")
            response = requests.get(api_url, params=params)
            response.raise_for_status()
            
            # Parse JSON data
            data = response.json()
            
            # Get lineups from this batch
            lineups = data.get("lineups", [])
            batch_size = len(lineups)
            
            if batch_size == 0:  # No more lineups to fetch
                break

            # Add the lineups to the list of all lineups
            all_lineups.extend(lineups)
            
            # Get total lineup info from the response header
            max_results = int(response.headers.get('X-Max-Results', 0))
            print(f"Fetched {batch_size} lineups (total so far: {len(all_lineups)} of {max_results})")
            
            # Always increment offset by actual batch size
            offset += limit
            
            # If we've fetched all available lineups, we're done
            if len(all_lineups) >= max_results:
                break
        
        print(f"Total lineups fetched: {len(all_lineups)}")
        
        # Create complete response
        complete_data = {
            "generated_at": data.get("generated_at"),
            "lineups": all_lineups
        }
        
        # Save to file
        output_dir = Path.cwd() / 'Data' / 'sportradar' / 'raw' / 'lineups_data'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Change competition and season name to a more readable format
        clean_season_name = season_name.replace(' ', '_').replace('/', '_')
        
        # Add random number to avoid filename conflicts
        random_suffix = str(random.randint(1000, 9999))  # 4-digit random number
        clean_season_name = f"{clean_season_name}_{random_suffix}"
        
        output_file = output_dir / f"{clean_season_name}_lineups.json"
        #Create the file and overwrite if it already exists
        with open(output_file, "w") as file:
            json.dump(complete_data, file, indent=4)
        
        print(f"Data saved to {output_file}")
        return complete_data
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching lineups for {competition_name} - {season_name} (ID: {season_id}): {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON for {competition_name} - {season_name} (ID: {season_id}): {e}")
        return None

if __name__ == "__main__":
    scrape_all_lineups()