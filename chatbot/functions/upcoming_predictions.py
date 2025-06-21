"""
Upcoming Predictions - Get predictions for upcoming matches with filtering

Reuses existing components to get predictions without value betting calculations.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

from chatbot.functions.match_predictions import get_multiple_match_predictions
from chatbot.functions.upcoming_matches import get_upcoming_match_list

def get_upcoming_predictions(
    days_ahead: int = 7,
    league_query: str = None,
    nation: str = None,
    max_results: int = 15
) -> Dict[str, Any]:
    """
    Get predictions for upcoming matches with optional league filtering.
    
    Args:
        days_ahead: Number of days to look ahead (default: 7)
        league_query: Optional league/competition to filter by
        nation: Optional nation to filter by
        max_results: Maximum number of predictions to return
        
    Returns:
        Dictionary with match predictions
    """
    try:
        # Get upcoming matches first
        matches_result = get_upcoming_match_list(days_ahead, league_query, nation, max_results)
        
        if not matches_result['success']:
            return matches_result
            
        upcoming_matches = matches_result['data']['matches']
        
        # Get predictions for all matches
        match_ids = [match['match_id'] for match in upcoming_matches]
        predictions = get_multiple_match_predictions(match_ids)
        
        print(f"   • Found predictions for {len(predictions)} matches")
        
        # Combine match info with predictions
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
        
        return {
            'success': True,
            'error': None,
            'data': {
                'search_criteria': matches_result['data']['search_criteria'],
                'summary': {
                    'total_matches_found': matches_result['data']['summary']['total_matches_found'],
                    'matches_with_predictions': len(predictions),
                    'predictions_returned': len(match_predictions)
                },
                'predictions': match_predictions
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Error getting upcoming predictions: {str(e)}',
            'data': None
        }
