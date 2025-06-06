import requests
import json
from datetime import datetime
import os


# Set the API endpoint and headers
url = "https://v3.football.api-sports.io/fixtures?live=all"
headers = {
    "x-apisports-key": os.getenv("API_FOOTBALL_KEY")
}

def fetch_live_fixtures():
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise error for bad status

        data = response.json()
        
        # Optional: timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"live_fixtures_{timestamp}.json"
        
        # Write to file
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ Data written to {filename}")
    
    except requests.RequestException as e:
        print(f"❌ Error during request: {e}")

if __name__ == "__main__":
    fetch_live_fixtures()