"""
Upcoming Value Bets - Find the best betting opportunities across upcoming matches

Main orchestrator for finding value bets in upcoming matches with filtering.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

from chatbot.functions.league_finder import search_leagues
from chatbot.functions.match_finder import get_upcoming_matches
from chatbot.functions.value_betting import analyze_multiple_matches_for_value

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

def get_upcoming_value_bets(
    days_ahead: int = 7,
    league_query: str = None,
    kelly_fraction: float = 0.50,
    min_value_threshold: float = 0.05,
) -> Dict[str, Any]:
    """
    Find the best value betting opportunities in upcoming matches.
    
    Args:
        days_ahead: Number of days to look ahead (default: 7)
        league_query: Optional league/competition to filter by
        kelly_fraction: Kelly safety fraction (default: 0.50)
        min_value_threshold: Minimum expected value (default: 5%)
        
    Returns:
        Dictionary with best value betting opportunities
    """
    try:
        print("🔍 Searching for upcoming value bets...")
        print(f"   • Time window: next {days_ahead} days")
        if league_query:
            print(f"   • League filter: {league_query}")
        
        # Step 1: Resolve league filter if provided
        competition_ids = None
        league_info = None
        
        if league_query:
            matching_leagues = search_leagues(league_query)
            if matching_leagues:
                # Use the best matching league
                best_league = matching_leagues[0]
                competition_ids = [best_league['league_id']]
                league_info = best_league
                print(f"   • Found league: {best_league['league_name']} (ID: {best_league['league_id']})")
                print(f"   • Will search for matches with competition_id = {best_league['league_id']}")
            else:
                return {
                    'success': False,
                    'error': f'No leagues found matching "{league_query}"',
                    'data': None
                }
        
        # Step 2: Get upcoming matches
        upcoming_matches = get_upcoming_matches(
            days_ahead=days_ahead,
            competition_ids=competition_ids,
        )
        
        if not upcoming_matches:
            # Add debug info about why no matches were found
            print("   • No matches found. Checking all upcoming matches without competition filter...")
            all_matches = get_upcoming_matches(days_ahead=days_ahead)
            if all_matches:
                print(f"   • Found {len(all_matches)} total upcoming matches:")
                for match in all_matches[:3]:
                    print(f"     - {match['home_team']} vs {match['away_team']} (competition_id: {match.get('competition_id', 'N/A')})")
            
            return {
                'success': False,
                'error': 'No upcoming matches found with the specified criteria',
                'data': None
            }
        
        print(f"   • Found {len(upcoming_matches)} upcoming matches")
        
        # Step 3: Extract match IDs and analyze for value
        match_ids = [match['match_id'] for match in upcoming_matches]
        
        value_analysis = analyze_multiple_matches_for_value(
            match_ids,
            kelly_fraction,
            min_value_threshold
        )
        
        if 'error' in value_analysis:
            return {
                'success': False,
                'error': value_analysis['error'],
                'data': None
            }
        
        # Step 4: Get top value bets and add match context
        top_value_bets = value_analysis['all_value_bets']
        
        # Enhance with full match information
        match_lookup = {match['match_id']: match for match in upcoming_matches}
        
        for bet in top_value_bets:
            match_id = bet['match_id']
            if match_id in match_lookup:
                match_info = match_lookup[match_id]
                bet.update({
                    'start_time': match_info['start_time'],
                    'competition': match_info['competition'],
                    'country': match_info['country'],
                    'competition_id': match_info.get('competition_id')
                })
        
        print(f"   • Found {len(top_value_bets)} value betting opportunities")
        
        return {
            'success': True,
            'error': None,
            'data': {
                'search_criteria': {
                    'days_ahead': days_ahead,
                    'league_query': league_query,
                    'league_info': league_info,
                    'kelly_fraction': kelly_fraction,
                    'min_value_threshold': min_value_threshold
                },
                'analysis_summary': {
                    'total_matches_found': len(upcoming_matches),
                    'matches_analyzed': value_analysis['matches_processed'],
                    'matches_with_value': value_analysis['matches_with_value_bets'],
                    'total_value_opportunities': value_analysis['total_value_bets']
                },
                'value_bets': top_value_bets,
                'summary_stats': value_analysis.get('summary', {})
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Error finding upcoming value bets: {str(e)}',
            'data': None
        }

def get_upcoming_value_bets_by_country(
    country: str,
    days_ahead: int = 7,
    kelly_fraction: float = 0.25,
    min_value_threshold: float = 0.05,
) -> Dict[str, Any]:
    """
    Find value bets in upcoming matches filtered by country.
    
    Args:
        country: Country name to filter by
        days_ahead: Number of days to look ahead
        kelly_fraction: Kelly safety fraction
        min_value_threshold: Minimum expected value
        max_results: Maximum results to return
        
    Returns:
        Value betting opportunities in specified country
    """
    try:
        # Get upcoming matches filtered by country
        upcoming_matches = get_upcoming_matches(
            days_ahead=days_ahead,
            country=country,
            limit=100
        )
        
        if not upcoming_matches:
            return {
                'success': False,
                'error': f'No upcoming matches found in {country}',
                'data': None
            }
        
        # Analyze for value
        match_ids = [match['match_id'] for match in upcoming_matches]
        value_analysis = analyze_multiple_matches_for_value(
            match_ids,
            kelly_fraction,
            min_value_threshold
        )
        
        if 'error' in value_analysis:
            return {
                'success': False,
                'error': value_analysis['error'],
                'data': None
            }
        
        # Get top results with match context
        top_value_bets = value_analysis['all_value_bets']
        match_lookup = {match['match_id']: match for match in upcoming_matches}
        
        for bet in top_value_bets:
            match_id = bet['match_id']
            if match_id in match_lookup:
                match_info = match_lookup[match_id]
                bet.update({
                    'start_time': match_info['start_time'],
                    'competition': match_info['competition'],
                    'country': match_info['country']
                })
        
        return {
            'success': True,
            'error': None,
            'data': {
                'search_criteria': {
                    'country': country,
                    'days_ahead': days_ahead,
                    'kelly_fraction': kelly_fraction,
                    'min_value_threshold': min_value_threshold
                },
                'analysis_summary': {
                    'total_matches_found': len(upcoming_matches),
                    'matches_analyzed': value_analysis['matches_processed'],
                    'matches_with_value': value_analysis['matches_with_value_bets'],
                    'total_value_opportunities': value_analysis['total_value_bets']
                },
                'value_bets': top_value_bets,
                'summary_stats': value_analysis.get('summary', {})
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Error finding value bets in {country}: {str(e)}',
            'data': None
        } 