"""
Upcoming Matches - Get list of upcoming matches with filtering options
"""

from typing import Dict, Any, List, Optional
from chatbot.utils.league_finder import search_leagues
from chatbot.utils.match_finder import get_upcoming_matches

def get_upcoming_match_list(
    days_ahead: int = 7,
    league_query: str = None,
    nation: str = None,
    max_results: int = 15
) -> Dict[str, Any]:
    """
    Get list of upcoming matches with optional league and nation filtering.
    
    Args:
        days_ahead: Number of days to look ahead (default: 7)
        league_query: Optional league/competition to filter by
        nation: Optional nation to filter by
        max_results: Maximum number of matches to return
        
    Returns:
        Dictionary with upcoming matches
    """
    try:
        # Convert string inputs to integers
        days_ahead = int(days_ahead)
        max_results = int(max_results)
        
        # Validate inputs
        if days_ahead < 1 or days_ahead > 30:
            return {
                'success': False,
                'error': 'days_ahead must be between 1 and 30',
                'data': None
            }
            
        if max_results < 1:
            return {
                'success': False,
                'error': 'max_results must be greater than 0',
                'data': None
            }
        
        print("🔍 Searching for upcoming matches...")
        print(f"   • Time window: next {days_ahead} days")
        if league_query:
            print(f"   • League filter: {league_query}")
        if nation:
            print(f"   • Nation filter: {nation}")
        
        # Step 1: Resolve league filter if provided
        competition_ids = None
        league_info = None
        
        if league_query is not None and league_query != "None" and league_query != "":
            matching_leagues = search_leagues(league_query, nation)
            
            if not matching_leagues:
                return {
                    'success': False,
                    'error': f'No leagues found matching "{league_query}"' + 
                            (f' in {nation}' if nation else ''),
                    'data': None
                }
            
            # Check if clarification is needed
            best_match = matching_leagues[0]
            if not nation and best_match.get('needs_clarification'):
                nations = best_match['available_nations']
                nations_str = ", ".join(nations)
                return {
                    'success': False,
                    'error': f'Found "{league_query}" in multiple countries ({nations_str}). Please specify which nation you want.',
                    'data': None
                }
            
            # Debug print to see full league information
            print("   • Found leagues:")
            for idx, league in enumerate(matching_leagues, 1):
                print(f"     {idx}. {league['league_name']} ({league['country']['name']}, ID: {league['league_id']})")
            
            # If multiple leagues found, handle nation filtering
            if len(matching_leagues) > 1:
                if not nation:
                    # Create error message with available nations
                    nations = sorted(set(
                        f"{league['league_name']} ({league['country']['name']})" 
                        for league in matching_leagues
                    ))
                    nations_str = "\n- ".join(nations)
                    return {
                        'success': False,
                        'error': f'Found multiple competitions matching "{league_query}":\n- {nations_str}\nPlease specify which nation you want.',
                        'data': None
                    }
                else:
                    # Filter leagues by nation
                    nation_matches = [
                        league for league in matching_leagues 
                        if league['country']['name'].lower() == nation.lower()
                    ]
                    
                    if not nation_matches:
                        # List available nations in error message
                        available_nations = sorted(set(
                            league['country']['name'] 
                            for league in matching_leagues
                        ))
                        nations_str = ", ".join(available_nations)
                        return {
                            'success': False,
                            'error': f'No "{league_query}" found in {nation}. Available nations are: {nations_str}',
                            'data': None
                        }
                    
                    best_league = nation_matches[0]
            else:
                best_league = matching_leagues[0]
            
            competition_ids = [best_league['league_id']]
            league_info = best_league
            print(f"   • Selected league: {best_league['league_name']} ({best_league['country']['name']}, ID: {best_league['league_id']})")
        
        # Step 2: Get upcoming matches
        upcoming_matches = get_upcoming_matches(
            days_ahead=days_ahead,
            competition_ids=competition_ids,
        )
        
        if not upcoming_matches:
            return {
                'success': False,
                'error': (f'No upcoming matches found for {best_league["league_name"]} '
                         f'({best_league["country"]["name"]}) in the next {days_ahead} days. '
                         f'This might be because the league is currently in off-season or between fixtures.'),
                'data': None
            }
        
        # Sort by start time
        upcoming_matches.sort(key=lambda x: x['start_time'] or '')
        
        # Limit results
        top_matches = upcoming_matches[:max_results]
        
        print(f"   • Found {len(upcoming_matches)} upcoming matches")
        print(f"   • Returning {len(top_matches)} matches")
        
        return {
            'success': True,
            'error': None,
            'data': {
                'search_criteria': {
                    'days_ahead': days_ahead,
                    'league_query': league_query,
                    'league_info': league_info,
                    'max_results': max_results,
                    'nation': nation
                },
                'summary': {
                    'total_matches_found': len(upcoming_matches),
                    'matches_returned': len(top_matches)
                },
                'matches': top_matches
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Error getting upcoming matches: {str(e)}',
            'data': None
        } 