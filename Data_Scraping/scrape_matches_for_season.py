import os
from dotenv import load_dotenv
import requests
import json
from pathlib import Path
import time

load_dotenv()

def scrape_all_seasons():
    """Function similar to scrape_all_lineups.py but for matches instead of lineups
    Scrapes all the matches for all the top seasons that have been identified"""
    # Load the seasons data
    with open('Data/sportradar_league_defs.json', 'r') as f:
        competitions = json.load(f)
    
    for competition_name, competition_data in competitions.items():
        print(f"\nProcessing {competition_name}...")
        
        for season in competition_data['seasons']:
            season_id = season['id']
            season_name = season['name'].replace('/', '_')
            #
            # Scrape matches for a specific season
            season_data = get_season_matches(season_id, competition_name, season_name)
            
            if season_data:
                print(f"Successfully fetched {competition_name} - {season_name}")
            else:
                print(f"Failed to fetch data for {competition_name} - {season_name}")

def get_season_matches(season_id, competition_name, season_name):
    """
    Fetch all matches for a specific season using the Sportradar API
    
    Args:
        season_id (str): The season ID from the Sportradar API
        competition_name (str): Name of the competition
        season_name (str): The year of the season e.g 2024/2025 or 24/25
        
    Returns:
        dict: JSON response containing season's match schedule data if successful, None otherwise
    """
    # Get API key from .env file
    api_key = os.getenv('SPORTRADAR_API_KEY')
    
    try:
        print(f"\nFetching matches for {competition_name} - {season_name} (ID: {season_id})")
        
        all_summaries = []
        offset = 0
        limit = 100  # Try 200 here #TODO: Change to 100 if API doesn't allow 200
        
        while True:
            # Request URL to get match summaries for an entire season
            api_url = f"https://api.sportradar.com/soccer-extended/trial/v4/en/seasons/{season_id}/summaries.json"
            
            ##Fetching matches for Ukrainian Premier League - Premier League 24_25 (ID: sr:season:120467)
#               Fetching matches with offset 0...
##              Error fetching data for Ukrainian Premier League - Premier League 24_25 (ID: sr:season:120467): 403 Client Error: HTTP Forbidden for url: https://api.sportradar.com/soccer-extended/trial/v4/en/seasons/sr:season:120467/summaries.json?offset=0&limit=200
#               Failed to fetch data for Ukrainian Premier League - Premier League 24_25
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
            
            # Get total number of matches available from the response header
            max_results = int(response.headers.get('X-Max-Results', 0))
            print(f"Fetched {batch_size} matches (total so far: {len(all_summaries)} of {max_results})")
            
            # Always increment offset by actual batch size
            offset += limit
            
            # If we've fetched all available matches, we're done
            if len(all_summaries) >= max_results:
                break
        
        print(f"Total matches fetched: {len(all_summaries)}")
        
        # Create complete response
        complete_data = {
            "generated_at": data.get("generated_at"),
            "summaries": all_summaries
        }

#------------------- Save the data to a file -------------------#
        # make a directory
        output_dir = Path.cwd() / 'Data' / 'raw' / 'matches_data'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Re-format the competition and season names for the file name
        clean_comp_name = competition_name.replace(' ', '_')
        clean_season_name = season_name.replace(' ', '_').replace('/', '_')
        clean_season_id = clean_season_name.replace(':', '_')
        
        # Create the file and overwrite if it already exists
        output_file = output_dir / f"{clean_comp_name}_{clean_season_name}_{clean_season_id}.json"
        with open(output_file, "w") as file:
            json.dump(complete_data, file, indent=4)
#----------------------------------------------------------------#
        

        print(f"Data saved to {output_file}")
        return complete_data
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {competition_name} - {season_name} (ID: {season_id}): {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON for {competition_name} - {season_name} (ID: {season_id}): {e}")
        return None


if __name__ == "__main__":
    scrape_all_seasons()