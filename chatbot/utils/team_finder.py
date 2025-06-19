"""
Team Finder Function

Dynamically finds team IDs from team names using existing match data.
"""

import psycopg2
from typing import Dict, Any, Optional, List
from config import get_config


def find_team_id(team_name: str) -> Optional[int]:
    """
    Find team ID from team name using existing match data.
    
    Args:
        team_name: Name of the team to search for
        
    Returns:
        Team ID if found, None otherwise
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
        
        # First try exact match
        cursor.execute("""
            SELECT DISTINCT home_team_id as team_id, home_team_name as team_name
            FROM matches 
            WHERE LOWER(home_team_name) = LOWER(%s)
            AND home_team_id IS NOT NULL
            UNION
            SELECT DISTINCT away_team_id as team_id, away_team_name as team_name
            FROM matches 
            WHERE LOWER(away_team_name) = LOWER(%s)
            AND away_team_id IS NOT NULL
        """, (team_name, team_name))
        
        result = cursor.fetchone()
        if result:
            cursor.close()
            conn.close()
            return result[0]
        
        # Then try fuzzy search using similarity
        cursor.execute("""
            SELECT DISTINCT 
                home_team_id as team_id, 
                home_team_name as team_name,
                similarity(LOWER(home_team_name), LOWER(%s)) as sim_score
            FROM matches 
            WHERE similarity(LOWER(home_team_name), LOWER(%s)) > 0.3
            AND home_team_id IS NOT NULL
            UNION
            SELECT DISTINCT 
                away_team_id as team_id, 
                away_team_name as team_name,
                similarity(LOWER(away_team_name), LOWER(%s)) as sim_score
            FROM matches 
            WHERE similarity(LOWER(away_team_name), LOWER(%s)) > 0.3
            AND away_team_id IS NOT NULL
            ORDER BY sim_score DESC
            LIMIT 5
        """, (team_name, team_name, team_name, team_name))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if results:
            # Return the best match if similarity is high enough
            best_match = results[0]
            if best_match[2] > 0.6:  # 60% similarity threshold
                return best_match[0]
            else:
                # Return multiple options for user to choose
                return {
                    "suggestions": [
                        {"team_id": r[0], "team_name": r[1], "similarity": r[2]}
                        for r in results
                    ]
                }
        
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