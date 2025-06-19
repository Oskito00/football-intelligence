"""
Odds Retrieval - Get latest odds from bookmakers

Retrieves the most recent odds for matches from the odds table.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
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

def get_latest_match_odds(match_id: int, bet_type_id: int = 1) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get the latest odds for a specific match from all bookmakers.
    
    Args:
        match_id: Match ID to get odds for
        bet_type_id: Bet type ID (1 = match result)
        
    Returns:
        Dictionary with odds grouped by bet_value (Home Win, Draw, Away Win)
    """
    # Use the multiple match function with a single match
    multiple_results = get_odds_for_multiple_matches([match_id], bet_type_id, return_all_bookmakers=True)
    return multiple_results.get(match_id, {})

def get_best_odds_for_match(match_id: int, bet_type_id: int = 1) -> Dict[str, Dict[str, Any]]:
    """
    Get the best (highest) odds for each outcome from all bookmakers.
    
    Args:
        match_id: Match ID to get odds for
        bet_type_id: Bet type ID (1 = match result)
        
    Returns:
        Dictionary with best odds for each outcome
    """
    # Use the multiple match function with a single match
    multiple_results = get_best_odds_for_multiple_matches([match_id], bet_type_id)
    return multiple_results.get(match_id, {})

def get_odds_for_multiple_matches(
    match_ids: List[int], 
    bet_type_id: int = 1, 
    return_all_bookmakers: bool = False
) -> Dict[int, Dict[str, Any]]:
    """
    Get odds for multiple matches efficiently.
    
    Args:
        match_ids: List of match IDs
        bet_type_id: Bet type ID (1 = match result)
        return_all_bookmakers: If True, returns all bookmakers; if False, returns only best odds
        
    Returns:
        Dictionary mapping match_id to odds data
    """
    if not DB_AVAILABLE or not match_ids:
        return {match_id: _get_mock_odds_data(match_id) for match_id in match_ids}
    
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
        
        # Get latest odds for all matches
        placeholders = ','.join(['%s'] * len(match_ids))
        query = f"""
        WITH latest_odds AS (
            SELECT 
                match_id,
                bookmaker_id,
                bookmaker_name,
                bet_value,
                odds_value,
                retrieved_at,
                ROW_NUMBER() OVER (
                    PARTITION BY match_id, bookmaker_id, bet_value 
                    ORDER BY retrieved_at DESC
                ) as rn
            FROM odds 
            WHERE match_id IN ({placeholders})
            AND bet_type_id = %s
        )
        SELECT 
            match_id,
            bookmaker_id,
            bookmaker_name,
            bet_value,
            odds_value,
            retrieved_at
        FROM latest_odds 
        WHERE rn = 1
        ORDER BY match_id, bet_value, odds_value DESC
        """
        
        cursor.execute(query, match_ids + [bet_type_id])
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if return_all_bookmakers:
            return _group_odds_by_match_and_outcome(results)
        else:
            return _get_best_odds_from_results(results)
        
    except Exception as e:
        print(f"Error getting odds for matches {match_ids}: {str(e)}")
        return {match_id: _get_mock_odds_data(match_id) for match_id in match_ids}

def get_best_odds_for_multiple_matches(match_ids: List[int], bet_type_id: int = 1) -> Dict[int, Dict[str, Dict[str, Any]]]:
    """
    Get best odds for multiple matches efficiently.
    
    Args:
        match_ids: List of match IDs
        bet_type_id: Bet type ID (1 = match result)
        
    Returns:
        Dictionary mapping match_id to best odds for each outcome
    """
    return get_odds_for_multiple_matches(match_ids, bet_type_id, return_all_bookmakers=False)

def _group_odds_by_match_and_outcome(results: List[Dict[str, Any]]) -> Dict[int, Dict[str, List[Dict[str, Any]]]]:
    """Group odds results by match_id and outcome, including all bookmakers."""
    odds_by_match = {}
    
    for row in results:
        match_id = row['match_id']
        bet_value = _normalize_bet_value(row['bet_value'])
        
        if match_id not in odds_by_match:
            odds_by_match[match_id] = {}
        
        if bet_value not in odds_by_match[match_id]:
            odds_by_match[match_id][bet_value] = []
        
        odds_by_match[match_id][bet_value].append({
            'bookmaker_id': row['bookmaker_id'],
            'bookmaker_name': row['bookmaker_name'],
            'odds_value': float(row['odds_value']),
            'retrieved_at': row['retrieved_at']
        })
    
    return odds_by_match

def _get_best_odds_from_results(results: List[Dict[str, Any]]) -> Dict[int, Dict[str, Dict[str, Any]]]:
    """Extract best odds for each match and outcome from query results."""
    odds_by_match = {}
    
    for row in results:
        match_id = row['match_id']
        bet_value = _normalize_bet_value(row['bet_value'])
        odds_value = float(row['odds_value'])
        
        if match_id not in odds_by_match:
            odds_by_match[match_id] = {}
        
        # Since results are ordered by odds_value DESC, first occurrence is the best
        if bet_value not in odds_by_match[match_id]:
            odds_by_match[match_id][bet_value] = {
                'odds_value': odds_value,
                'bookmaker_name': row['bookmaker_name'],
                'bookmaker_id': row['bookmaker_id'],
                'retrieved_at': row['retrieved_at'],
                'implied_probability': 1.0 / odds_value
            }
    
    return odds_by_match

def _normalize_bet_value(bet_value: str) -> str:
    """
    Normalize bet_value strings to standard format.
    
    Args:
        bet_value: Raw bet value from database
        
    Returns:
        Normalized bet value
    """
    bet_value_lower = bet_value.lower().strip()
    
    # Map various formats to standard outcomes
    if any(term in bet_value_lower for term in ['home', '1', 'win', 'home win']):
        return 'Home Win'
    elif any(term in bet_value_lower for term in ['draw', 'x', 'tie']):
        return 'Draw'  
    elif any(term in bet_value_lower for term in ['away', '2', 'away win']):
        return 'Away Win'
    else:
        # Return original if can't classify
        return bet_value.title()

def _get_mock_odds_data(match_id: int) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generate mock odds data for testing.
    
    Args:
        match_id: Match ID
        
    Returns:
        Mock odds data
    """
    import random
    random.seed(match_id)
    
    # Generate realistic odds
    home_odds = round(random.uniform(1.5, 4.0), 2)
    draw_odds = round(random.uniform(2.8, 4.5), 2)
    away_odds = round(random.uniform(1.8, 5.0), 2)
    
    return {
        'Home Win': [
            {'bookmaker_id': 1, 'bookmaker_name': 'Bet365', 'odds_value': home_odds, 'retrieved_at': datetime.now()},
            {'bookmaker_id': 2, 'bookmaker_name': 'William Hill', 'odds_value': home_odds + 0.05, 'retrieved_at': datetime.now()}
        ],
        'Draw': [
            {'bookmaker_id': 1, 'bookmaker_name': 'Bet365', 'odds_value': draw_odds, 'retrieved_at': datetime.now()},
            {'bookmaker_id': 2, 'bookmaker_name': 'William Hill', 'odds_value': draw_odds - 0.10, 'retrieved_at': datetime.now()}
        ],
        'Away Win': [
            {'bookmaker_id': 1, 'bookmaker_name': 'Bet365', 'odds_value': away_odds, 'retrieved_at': datetime.now()},
            {'bookmaker_id': 2, 'bookmaker_name': 'William Hill', 'odds_value': away_odds + 0.15, 'retrieved_at': datetime.now()}
        ]  
    } 