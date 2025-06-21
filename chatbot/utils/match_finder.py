"""
Match Finder - Find matches by team names with fuzzy search

Searches for upcoming matches between specified teams using fuzzy string matching.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher

# Add project root to path to import database helpers
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Import database connection (you'll need to adjust this based on your DB setup)
try:
    from config import get_config
    import psycopg2
    from psycopg2.extras import RealDictCursor
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

def similarity(a: str, b: str) -> float:
    """
    Calculate similarity between two strings.
    
    Args:
        a: First string
        b: Second string
        
    Returns:
        Similarity score between 0 and 1
    """
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def normalize_team_name(team_name: str) -> str:
    """
    Normalize team name for better matching.
    
    Args:
        team_name: Raw team name
        
    Returns:
        Normalized team name
    """
    # Common normalization
    normalized = team_name.lower().strip()
    
    # Handle common abbreviations and variations
    substitutions = {
        'man united': 'manchester united',
        'man city': 'manchester city',
        'man utd': 'manchester united',
        'tottenham': 'tottenham hotspur',
        'spurs': 'tottenham hotspur',
        'arsenal': 'arsenal',
        'chelsea': 'chelsea',
        'liverpool': 'liverpool',
        'real madrid': 'real madrid',
        'barca': 'barcelona',
        'barcelona': 'fc barcelona',
        'bayern': 'bayern munich',
        'psg': 'paris saint-germain'
    }
    
    for abbrev, full_name in substitutions.items():
        if abbrev in normalized:
            normalized = normalized.replace(abbrev, full_name)
    
    return normalized

def find_matches_by_teams(home_team: str, away_team: str, days_ahead: int = 30) -> List[Dict[str, Any]]:
    """
    Find upcoming matches between specified teams using optimized match_status query.
    """
    try:
        config = get_config()
        conn = psycopg2.connect(
            host=config.DB_HOST,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            cursor_factory=RealDictCursor
        )
        
        cursor = conn.cursor()
        
        # Calculate date range
        start_date = datetime.now()
        end_date = start_date + timedelta(days=days_ahead)
        
        # Generate team name variations for better matching
        home_variations = _get_team_name_variations(home_team)
        away_variations = _get_team_name_variations(away_team)
        
        print(f"🔍 Searching for: {home_team} vs {away_team}")
        print(f"🏠 Home variations: {home_variations}")
        print(f"🏃 Away variations: {away_variations}")
        
        # Try exact match first with more permissive patterns
        query = """
        SELECT 
            match_id,
            start_time,
            home_team_name,
            away_team_name,
            competition_name,
            competition_country
        FROM matches 
        WHERE match_status = 'NS'
        AND start_time >= %s 
        AND start_time <= %s
        AND home_team_name IS NOT NULL 
        AND away_team_name IS NOT NULL
        AND (
            (home_team_name ILIKE ANY(%s) AND away_team_name ILIKE ANY(%s)) OR
            (home_team_name ILIKE ANY(%s) AND away_team_name ILIKE ANY(%s))
        )
        ORDER BY start_time ASC
        LIMIT 10
        """
        
        # Prepare ILIKE patterns
        home_patterns = [f"%{var}%" for var in home_variations]
        away_patterns = [f"%{var}%" for var in away_variations]
        
        cursor.execute(query, (
            start_date, end_date,
            home_patterns, away_patterns,
            away_patterns, home_patterns  # Check reverse order too
        ))
        
        results = cursor.fetchall()
        print(f"📊 Database returned {len(results)} potential matches")
        
        # If no results, try a broader search
        if not results:
            print("🔍 Trying broader search...")
            broader_query = """
            SELECT 
                match_id,
                start_time,
                home_team_name,
                away_team_name,
                competition_name,
                competition_country
            FROM matches 
            WHERE match_status = 'NS'
            AND start_time >= %s 
            AND start_time <= %s
            AND (
                home_team_name ILIKE ANY(%s) OR away_team_name ILIKE ANY(%s) OR
                home_team_name ILIKE ANY(%s) OR away_team_name ILIKE ANY(%s)
            )
            ORDER BY start_time ASC
            LIMIT 20
            """
            
            cursor.execute(broader_query, (
                start_date, end_date,
                home_patterns, away_patterns,
                away_patterns, home_patterns
            ))
            
            broader_results = cursor.fetchall()
            print(f"📊 Broader search returned {len(broader_results)} matches")
            for match in broader_results:
                print(f"   • {match['home_team_name']} vs {match['away_team_name']}")
        
        cursor.close()
        conn.close()
        
        # Convert to expected format with relevance scoring
        matches = []
        home_normalized = normalize_team_name(home_team)
        away_normalized = normalize_team_name(away_team)
        
        for match in results:
            home_db = normalize_team_name(match['home_team_name'])
            away_db = normalize_team_name(match['away_team_name'])
            
            # Calculate similarity scores
            home_score = max(
                similarity(home_normalized, home_db),
                similarity(home_normalized, away_db)
            )
            away_score = max(
                similarity(away_normalized, home_db),
                similarity(away_normalized, away_db)
            )
            
            relevance = (home_score + away_score) / 2
            
            print(f"🎯 Match: {match['home_team_name']} vs {match['away_team_name']} (relevance: {relevance:.2f})")
            
            matches.append({
                "match_id": match['match_id'],
                "start_time": match['start_time'].isoformat() if match['start_time'] else None,
                "home_team": match['home_team_name'],
                "away_team": match['away_team_name'],
                "competition": match['competition_name'],
                "country": match['competition_country'],
                "relevance_score": relevance,
                "direct_match": True
            })
        
        # Sort by relevance and return top 5
        matches.sort(key=lambda x: x['relevance_score'], reverse=True)
        return matches[:5]
        
    except Exception as e:
        print(f"Database error in match finder: {str(e)}")
        return []

def search_team_matches(team_name: str, days_ahead: int = 14) -> List[Dict[str, Any]]:
    """
    Find all upcoming matches for a specific team using optimized match_status query.
    """
    if not DB_AVAILABLE:
        return []
    
    try:
        config = get_config()
        conn = psycopg2.connect(
            host=config.DB_HOST,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            cursor_factory=RealDictCursor
        )
        
        cursor = conn.cursor()
        
        # Calculate date range  
        start_date = datetime.now()
        end_date = start_date + timedelta(days=days_ahead)
        
        # Generate team variations
        team_variations = _get_team_name_variations(team_name)
        team_patterns = [f"%{var}%" for var in team_variations]
        
        # Optimized query using match_status
        query = """
        SELECT 
            match_id,
            start_time,
            home_team_name,
            away_team_name,
            competition_name,
            competition_country
        FROM matches 
        WHERE match_status = 'NS'
        AND start_time >= %s 
        AND start_time <= %s
        AND (home_team_name ILIKE ANY(%s) OR away_team_name ILIKE ANY(%s))
        ORDER BY start_time ASC
        LIMIT 20
        """
        
        cursor.execute(query, (start_date, end_date, team_patterns, team_patterns))
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Convert to expected format
        team_matches = []
        normalized_team = normalize_team_name(team_name)
        
        for match in results:
            home_db = normalize_team_name(match['home_team_name'])
            away_db = normalize_team_name(match['away_team_name'])
            
            # Only include if similarity is high enough
            if (similarity(normalized_team, home_db) > 0.7 or 
                similarity(normalized_team, away_db) > 0.7):
                
                team_matches.append({
                    "match_id": match['match_id'],
                    "start_time": match['start_time'].isoformat(),
                    "home_team": match['home_team_name'],
                    "away_team": match['away_team_name'],
                    "competition": match['competition_name'],
                    "country": match['competition_country']
                })
        
        return team_matches
        
    except Exception as e:
        print(f"Database error in team search: {str(e)}")
        return []

def _get_team_name_variations(team_name: str) -> List[str]:
    """Generate common variations of team names for database matching."""
    variations = [team_name.lower().strip()]
    
    # Add normalized version
    normalized = normalize_team_name(team_name)
    if normalized not in variations:
        variations.append(normalized)
    
    # Add common abbreviations and variations
    team_lower = team_name.lower().strip()
    
    # Enhanced abbreviations dictionary
    abbreviations = {
        # Premier League
        'manchester united': ['man united', 'man utd', 'mufc', 'united'],
        'manchester city': ['man city', 'mcfc', 'city'],
        'tottenham': ['spurs', 'thfc', 'tottenham hotspur'],
        'arsenal': ['afc', 'gunners', 'arsenal fc'],
        'liverpool': ['lfc', 'reds', 'liverpool fc'],
        'chelsea': ['cfc', 'blues', 'chelsea fc'],
        'newcastle': ['nufc', 'newcastle united', 'toon'],
        'west ham': ['west ham united', 'hammers', 'whu'],
        'brighton': ['brighton & hove albion', 'seagulls', 'bhafc'],
        
        # European clubs
        'paris saint germain': ['psg', 'paris sg', 'paris saint-germain'],
        'paris saint-germain': ['psg', 'paris sg', 'paris saint germain'],
        'athletico madrid': ['atletico madrid', 'atletico', 'atleti'],
        'atletico madrid': ['athletico madrid', 'atletico', 'atleti'],
        'real madrid': ['madrid', 'real', 'rmcf'],
        'barcelona': ['barca', 'fc barcelona', 'fcb'],
        'bayern munich': ['bayern', 'fc bayern', 'fcb munich'],
        'borussia dortmund': ['dortmund', 'bvb'],
        'juventus': ['juve', 'juventus fc'],
        'ac milan': ['milan', 'ac milan'],
        'inter milan': ['inter', 'internazionale'],
        'ajax': ['afc ajax', 'ajax amsterdam'],
    }
    
    # Check for matches in abbreviations
    for full_name, abbrevs in abbreviations.items():
        if (full_name in team_lower or 
            team_lower in full_name or
            any(abbrev in team_lower for abbrev in abbrevs) or
            any(team_lower in abbrev for abbrev in abbrevs)):
            variations.extend(abbrevs)
            variations.append(full_name)
    
    # Add partial matches (first word, last word)
    words = team_name.lower().split()
    if len(words) > 1:
        variations.append(words[0])  # First word
        variations.append(words[-1])  # Last word
        
        # Add combinations
        if len(words) >= 2:
            variations.append(f"{words[0]} {words[-1]}")  # First + last
    
    # Remove duplicates and empty strings
    variations = list(set([v.strip() for v in variations if v.strip()]))
    
    return variations

def get_upcoming_matches(
    days_ahead: int = 7,
    competition_ids: List[int] = None,
    country: str = None,
) -> List[Dict[str, Any]]:
    """
    Get upcoming matches with optional filtering.
    
    Args:
        days_ahead: Number of days to look ahead
        competition_ids: Optional list of competition IDs to filter by
        country: Optional country name to filter by
        
    Returns:
        List of upcoming matches
    """    
    try:
        # Convert days_ahead to int if it's a string
        days_ahead = int(days_ahead)
        
        config = get_config()
        conn = psycopg2.connect(
            host=config.DB_HOST,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            cursor_factory=RealDictCursor
        )
        
        cursor = conn.cursor()
        
        # Calculate date range
        start_date = datetime.now()
        end_date = start_date + timedelta(days=days_ahead)
        
        # Build query with optional filters
        where_conditions = [
            "match_status = 'NS'",
            "start_time >= %s",
            "start_time <= %s",
            "home_team_name IS NOT NULL",
            "away_team_name IS NOT NULL"
        ]
        params = [start_date, end_date]
        
        # Add competition filter if provided
        if competition_ids:
            placeholders = ','.join(['%s'] * len(competition_ids))
            where_conditions.append(f"competition_id IN ({placeholders})")
            params.extend(competition_ids)
        
        # Add country filter if provided
        if country:
            where_conditions.append("competition_country ILIKE %s")
            params.append(f"%{country}%")
        
        query = f"""
        SELECT 
            match_id,
            start_time,
            home_team_name,
            away_team_name,
            competition_name,
            competition_country,
            competition_id
        FROM matches 
        WHERE {' AND '.join(where_conditions)}
        ORDER BY start_time ASC
        """
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Convert to expected format
        matches = []
        for match in results:
            matches.append({
                'match_id': match['match_id'],
                'start_time': match['start_time'].isoformat() if match['start_time'] else None,
                'home_team': match['home_team_name'],
                'away_team': match['away_team_name'],
                'competition': match['competition_name'],
                'country': match['competition_country'],
                'competition_id': match['competition_id']
            })
        
        return matches
        
    except Exception as e:
        print(f"Error getting upcoming matches: {str(e)}")
        return []