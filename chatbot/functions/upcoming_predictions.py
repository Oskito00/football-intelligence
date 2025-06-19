"""
Upcoming Predictions - Get predictions for upcoming matches with filtering

Reuses existing components to get predictions without value betting calculations.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

from chatbot.functions.league_finder import search_leagues
from chatbot.functions.match_finder import get_upcoming_matches
from chatbot.functions.match_predictions import get_multiple_match_predictions

def get_upcoming_predictions(
    days_ahead: int = 7,
    league_query: str = None,
    max_results: int = 15
) -> Dict[str, Any]:
    """
    Get predictions for upcoming matches with optional league filtering.
    
    Args:
        days_ahead: Number of days to look ahead (default: 7)
        league_query: Optional league/competition to filter by
        max_results: Maximum number of predictions to return
        
    Returns:
        Dictionary with match predictions
    """
    try:
        print("🔍 Searching for upcoming match predictions...")
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
            return {
                'success': False,
                'error': 'No upcoming matches found with the specified criteria',
                'data': None
            }
        
        print(f"   • Found {len(upcoming_matches)} upcoming matches")
        
        # Step 3: Get predictions for all matches
        match_ids = [match['match_id'] for match in upcoming_matches]
        predictions = get_multiple_match_predictions(match_ids)
        
        print(f"   • Found predictions for {len(predictions)} matches")
        
        # Step 4: Combine match info with predictions
        match_predictions = []
        match_lookup = {match['match_id']: match for match in upcoming_matches}
        
        for match_id, prediction in predictions.items():
            if match_id in match_lookup:
                match_info = match_lookup[match_id]
                
                # Combine match and prediction data
                combined = {
                    'match_id': match_id,
                    'home_team': prediction.get('home_team'),
                    'away_team': prediction.get('away_team'),
                    'start_time': match_info['start_time'],
                    'competition': match_info['competition'],
                    'country': match_info['country'],
                    'predicted_result': prediction.get('predicted_result'),
                    'confidence': prediction.get('confidence'),
                    'prob_home_win': prediction.get('prob_home_win'),
                    'prob_draw': prediction.get('prob_draw'),
                    'prob_away_win': prediction.get('prob_away_win'),
                    'model_type': prediction.get('model_type'),
                    'prediction_date': prediction.get('prediction_date')
                }
                
                match_predictions.append(combined)
        
        # Sort by start time
        match_predictions.sort(key=lambda x: x['start_time'] or '')
        
        # Limit results
        top_predictions = match_predictions[:max_results]
        
        print(f"   • Returning {len(top_predictions)} match predictions")
        
        return {
            'success': True,
            'error': None,
            'data': {
                'search_criteria': {
                    'days_ahead': days_ahead,
                    'league_query': league_query,
                    'league_info': league_info,
                    'max_results': max_results
                },
                'summary': {
                    'total_matches_found': len(upcoming_matches),
                    'matches_with_predictions': len(predictions),
                    'predictions_returned': len(top_predictions)
                },
                'predictions': top_predictions
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Error getting upcoming predictions: {str(e)}',
            'data': None
        }

def get_upcoming_predictions_by_country(
    country: str,
    days_ahead: int = 7,
    max_results: int = 15
) -> Dict[str, Any]:
    """
    Get upcoming predictions filtered by country.
    
    Args:
        country: Country name to filter by
        days_ahead: Number of days to look ahead
        max_results: Maximum results to return
        
    Returns:
        Match predictions for specified country
    """
    try:
        # Get upcoming matches filtered by country
        upcoming_matches = get_upcoming_matches(
            days_ahead=days_ahead,
            country=country,
        )
        
        if not upcoming_matches:
            return {
                'success': False,
                'error': f'No upcoming matches found in {country}',
                'data': None
            }
        
        # Get predictions
        match_ids = [match['match_id'] for match in upcoming_matches]
        predictions = get_multiple_match_predictions(match_ids)
        
        # Combine data
        match_predictions = []
        match_lookup = {match['match_id']: match for match in upcoming_matches}
        
        for match_id, prediction in predictions.items():
            if match_id in match_lookup:
                match_info = match_lookup[match_id]
                
                combined = {
                    'match_id': match_id,
                    'home_team': prediction.get('home_team'),
                    'away_team': prediction.get('away_team'),
                    'start_time': match_info['start_time'],
                    'competition': match_info['competition'],
                    'country': match_info['country'],
                    'predicted_result': prediction.get('predicted_result'),
                    'confidence': prediction.get('confidence'),
                    'prob_home_win': prediction.get('prob_home_win'),
                    'prob_draw': prediction.get('prob_draw'),
                    'prob_away_win': prediction.get('prob_away_win'),
                    'model_type': prediction.get('model_type'),
                    'prediction_date': prediction.get('prediction_date')
                }
                
                match_predictions.append(combined)
        
        # Sort and limit
        match_predictions.sort(key=lambda x: x['start_time'] or '')
        top_predictions = match_predictions[:max_results]
        
        return {
            'success': True,
            'error': None,
            'data': {
                'search_criteria': {
                    'country': country,
                    'days_ahead': days_ahead,
                    'max_results': max_results
                },
                'summary': {
                    'total_matches_found': len(upcoming_matches),
                    'matches_with_predictions': len(predictions),
                    'predictions_returned': len(top_predictions)
                },
                'predictions': top_predictions
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Error getting predictions for {country}: {str(e)}',
            'data': None
        } 