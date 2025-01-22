import json
import os
import requests
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def fetch_seasons_for_competitions():
    """Fetch seasons for each competition from SportRadar API"""
    
    # Load competition IDs from top_competitions.json
    with open('sportradar/data/sportradar_jsons/top_competitions_extra.json', 'r') as f:
        competitions = json.load(f)
    
    # API configuration
    BASE_URL = "https://api.sportradar.com/soccer-extended/trial/v4/en/competitions"
    API_KEY = os.getenv('SPORTRADAR_API_KEY')
    
    # Define headers
    headers = {
        'Accept': 'application/json'
    }
    
    all_seasons = {}
    
    for comp_name, comp_data in competitions.items():
        comp_id = comp_data['id']
        print(f"\nFetching seasons for {comp_name} (ID: {comp_id})")
        
        # Construct URL - add .json extension
        url = f"{BASE_URL}/{comp_id}/seasons.json?api_key={API_KEY}"
        
        try:
            # Add delay before each request to respect rate limits
            time.sleep(1.1)  # Slightly more than 1 second to be safe
            
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                print(f"Error: Status Code {response.status_code}")
                print(f"URL: {url}")
                print(f"Response: {response.text}")
                continue
            
            seasons_data = response.json()
            all_seasons[comp_name] = {
                'competition_id': comp_id,
                'seasons': seasons_data.get('seasons', [])
            }
            
            print(f"Found {len(seasons_data.get('seasons', []))} seasons")
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching seasons for {comp_name}: {str(e)}")
            continue
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON for {comp_name}: {str(e)}")
            continue
    
    # Save results
    output_file = 'sportradar/data/sportradar_jsons/top_seasons_extra.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_seasons, f, indent=4, ensure_ascii=False)
    
    print(f"\nSeasons data saved to {output_file}")
    return all_seasons

if __name__ == "__main__":
    fetch_seasons_for_competitions()
