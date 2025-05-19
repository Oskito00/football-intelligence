import json
import sqlite3
from helpers.database_helpers.get_and_set_functions import bulk_insert_formations, get_all_formations

def formation_extraction(matches):
    """Extracts the formation for each match
    
    Args:
        matches (list): The list of matches to extract formations from.
    
    Returns:
        formations (list): The list of formations.
        Saves the formations to formation_history table.
    """
    formations = []
    for match in matches:
        try:
            match_id, home_formation_str, away_formation_str = match

            formations.append({
                'match_id': match_id,
                'home_team_formation': home_formation_str,
                'away_team_formation': away_formation_str
            })
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Skipping match {match_id}: {str(e)}")
            continue
    
    bulk_insert_formations(formations)
            
    return formations

if __name__ == "__main__":
    conn = sqlite3.connect('api_football.db')
    formations = get_all_formations(conn)
    formation_extraction(formations)