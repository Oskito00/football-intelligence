"""
Team Finder Function

Dynamically finds team IDs from team names using existing match data.
"""

import psycopg2
from typing import Dict, Any, Optional, List, Union
from config import get_config


def find_team_id(conn, team_name: str) -> Optional[List[Dict[str, Any]]]:
    """
    Find team ID from team name using teams mapping table.
    Always returns a list of matches, even for single results.
    """
    try:
        cursor = conn.cursor()
        
        # Try exact match first
        cursor.execute("""
            SELECT team_id, team_name, domestic_country
            FROM teams_mapping
            WHERE LOWER(team_name) = LOWER(%s)
        """, (team_name,))
        
        exact_matches = cursor.fetchall()
        
        # If we have exact matches, return them all
        if exact_matches:
            return [
                {
                    "team_id": match[0],
                    "team_name": match[1],
                    "country": match[2]
                }
                for match in exact_matches
            ]
            
        # If no exact match, try fuzzy search
        cursor.execute("""
            SELECT 
                team_id,
                team_name,
                domestic_country,
                similarity(LOWER(team_name), LOWER(%s)) as sim_score
            FROM teams_mapping
            WHERE similarity(LOWER(team_name), LOWER(%s)) > 0.3
            ORDER BY sim_score DESC
            LIMIT 5
        """, (team_name, team_name))
        
        fuzzy_matches = cursor.fetchall()
        cursor.close()
        
        if fuzzy_matches:
            # If best match has high similarity, return it as single item list
            if fuzzy_matches[0][3] > 0.6:
                return [{
                    "team_id": fuzzy_matches[0][0],
                    "team_name": fuzzy_matches[0][1],
                    "country": fuzzy_matches[0][2],
                    "similarity": fuzzy_matches[0][3]
                }]
            # Return all fuzzy matches
            return [
                {
                    "team_id": match[0],
                    "team_name": match[1],
                    "country": match[2],
                    "similarity": match[3]
                }
                for match in fuzzy_matches
            ]
            
        return None
        
    except Exception as e:
        print(f"Error finding team ID: {str(e)}")
        return None


def get_team_suggestions(partial_name: str) -> List[Dict[str, Any]]:
    """
    Get team suggestions for partial team name.
    
    Args:
        partial_name: Partial team name to search for
        
    Returns:
        List of matching teams
    """
    config = get_config()
    
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT 
                home_team_id as team_id, 
                home_team_name as team_name,
                home_team_domestic_country as country
            FROM matches 
            WHERE LOWER(home_team_name) LIKE LOWER(%s)
            AND home_team_id IS NOT NULL
            UNION
            SELECT DISTINCT 
                away_team_id as team_id, 
                away_team_name as team_name,
                away_team_domestic_country as country
            FROM matches 
            WHERE LOWER(away_team_name) LIKE LOWER(%s)
            AND away_team_id IS NOT NULL
            ORDER BY team_name
            LIMIT 10
        """, (f"%{partial_name}%", f"%{partial_name}%"))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return [
            {
                "team_id": row[0],
                "team_name": row[1], 
                "country": row[2]
            }
            for row in results
        ]
        
    except Exception as e:
        print(f"Error getting team suggestions: {str(e)}")
        return [] 