"""
League Finder - Search and filter leagues/competitions

Provides fuzzy search functionality for leagues and competitions.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Import database connection
try:
    from config import get_config
    import psycopg2
    from psycopg2.extras import RealDictCursor
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

def similarity(a: str, b: str) -> float:
    """Calculate similarity between two strings (reused from match_finder)."""
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def normalize_league_name(league_name: str) -> str:
    """Normalize league names for better matching."""
    if not league_name:
        return ""
    
    # Convert to lowercase and clean
    normalized = league_name.lower().strip()
    
    # Remove common words that don't help with matching
    remove_words = ['football', 'soccer', 'fc', 'association', 'federation']
    for word in remove_words:
        normalized = normalized.replace(word, '').strip()
    
    # Normalize spaces and hyphens
    normalized = ' '.join(normalized.split())
    normalized = normalized.replace('-', ' ')
    
    return normalized

def search_leagues(league_query: str, country_hint: str = None) -> List[Dict[str, Any]]:
    """
    Search for leagues using fuzzy matching.
    
    Args:
        league_query: League name or partial name to search for
        country_hint: Optional country to prioritize results
        
    Returns:
        List of matching leagues sorted by relevance
    """
    if not DB_AVAILABLE:
        return _get_mock_league_data(league_query)
    
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
        
        # Get all leagues
        query = """
        SELECT 
            id,
            name,
            type,
            country,
            current_season
        FROM leagues 
        WHERE name IS NOT NULL
        ORDER BY name
        """
        
        cursor.execute(query)
        all_leagues = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Debug: Show query
        print(f"🔍 Searching for leagues matching: '{league_query}'")
        
        # Fuzzy match against query
        query_normalized = normalize_league_name(league_query)
        query_words = set(query_normalized.lower().split())
        
        matching_leagues = []
        
        for league in all_leagues:
            league_name = league['name'] or ""
            league_normalized = normalize_league_name(league_name)
            league_words = set(league_normalized.lower().split())
            
            # Calculate different similarity metrics
            
            # 1. Overall string similarity
            string_similarity = similarity(query_normalized.lower(), league_normalized.lower())
            
            # 2. Word overlap (what percentage of query words are in league name)
            word_overlap = len(query_words.intersection(league_words)) / len(query_words) if query_words else 0
            
            # 3. Coverage (what percentage of league words are in query)
            coverage = len(query_words.intersection(league_words)) / len(league_words) if league_words else 0
            
            # 4. Length-based scoring
            length_penalty = 0
            if len(league_name) <= 5 and word_overlap < 0.8:
                # Penalize very short names unless they're a very good match
                length_penalty = 0.4
            
            # 5. Prefer exact word matches
            exact_word_bonus = 0
            if any(word in league_normalized.lower() for word in query_words):
                exact_word_bonus = 0.2
            
            # 6. Completeness bonus - prefer leagues that contain more of the query
            completeness_bonus = word_overlap * 0.3
            
            # Combine all scores
            final_score = (string_similarity * 0.4 + 
                          word_overlap * 0.4 + 
                          coverage * 0.2 + 
                          exact_word_bonus + 
                          completeness_bonus - 
                          length_penalty)
            
            # Country boost if specified
            if country_hint:
                try:
                    league_country = league.get('country', {})
                    if isinstance(league_country, dict):
                        country_name = league_country.get('name', '').lower()
                        if country_hint.lower() in country_name or country_name in country_hint.lower():
                            final_score += 0.2
                except:
                    pass
            
            # Only include if reasonable match
            if final_score > 0.2:
                matching_leagues.append({
                    'league_id': league['id'],
                    'league_name': league['name'],
                    'league_type': league.get('type'),
                    'country': league.get('country'),
                    'current_season': league.get('current_season'),
                    'relevance_score': final_score,
                    'word_overlap': word_overlap,
                    'string_similarity': string_similarity,
                    'length': len(league_name)
                })
        
        # Sort by relevance score
        matching_leagues.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Debug: Show top matches
        print("   • Top 5 matches:")
        for i, league in enumerate(matching_leagues[:5]):
            print(f"     {i+1}. {league['league_name']} (score: {league['relevance_score']:.2f})")
        
        return matching_leagues[:10]  # Return top 10
        
    except Exception as e:
        print(f"Error searching leagues: {str(e)}")
        return _get_mock_league_data(league_query)

def _get_league_name_variations(league_query: str) -> List[str]:
    """Generate basic variations of league names without hard-coding."""
    variations = [league_query.lower().strip()]
    
    # Add word combinations
    words = league_query.lower().split()
    if len(words) > 1:
        # Add individual words
        variations.extend(words)
        # Add first and last word
        variations.append(words[0])
        variations.append(words[-1])
        # Add pairs of words
        if len(words) >= 2:
            for i in range(len(words) - 1):
                variations.append(f"{words[i]} {words[i+1]}")
    
    # Remove duplicates
    return list(set(variations))

def get_league_by_id(league_id: int) -> Optional[Dict[str, Any]]:
    """Get league information by ID."""
    if not DB_AVAILABLE:
        return None
    
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
        
        query = """
        SELECT 
            id,
            name,
            type,
            country,
            current_season
        FROM leagues 
        WHERE id = %s
        """
        
        cursor.execute(query, (league_id,))
        league = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if league:
            return {
                'league_id': league['id'],
                'league_name': league['name'],
                'league_type': league.get('type'),
                'country': league.get('country'),
                'current_season': league.get('current_season')
            }
        
        return None
        
    except Exception as e:
        print(f"Error getting league {league_id}: {str(e)}")
        return None

def _get_mock_league_data(league_query: str) -> List[Dict[str, Any]]:
    """Generate mock league data for testing."""
    mock_leagues = [
        {
            'league_id': 39,
            'league_name': 'Premier League',
            'league_type': 'League',
            'country': {'name': 'England'},
            'current_season': '2024',
            'relevance_score': 0.9
        },
        {
            'league_id': 140,
            'league_name': 'La Liga',
            'league_type': 'League',
            'country': {'name': 'Spain'},
            'current_season': '2024',
            'relevance_score': 0.8
        }
    ]
    
    # Filter based on query
    query_lower = league_query.lower()
    filtered = [l for l in mock_leagues if query_lower in l['league_name'].lower()]
    
    return filtered if filtered else mock_leagues[:1] 