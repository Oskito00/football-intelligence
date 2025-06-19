"""
Betting Recommendations - Main orchestrator for betting analysis

Combines predictions, odds, and value betting calculations.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

from chatbot.functions.match_predictions import get_match_prediction
from chatbot.functions.odds_retrieval import get_best_odds_for_match
from chatbot.functions.value_betting import analyze_betting_opportunity


def get_betting_recommendations(
    match_id: int,
    kelly_fraction: float = 0.5,
    min_value_threshold: float = 0.05
) -> Dict[str, Any]:
    """
    Get complete betting recommendations for a match.
    
    Args:
        match_id: Match ID to analyze
        kelly_fraction: Kelly safety fraction (default: 0.5 = 50% Kelly)
        min_value_threshold: Minimum expected value to recommend bet (default: 5%)
        
    Returns:
        Complete betting analysis with percentage recommendations
    """
    try:
        # Get match prediction
        prediction = get_match_prediction(match_id)
        if not prediction:
            return {
                'success': False,
                'error': f'No prediction found for match {match_id}',
                'data': None
            }
        
        # Get best odds
        best_odds = get_best_odds_for_match(match_id)
        if not best_odds:
            return {
                'success': False,
                'error': f'No odds found for match {match_id}',
                'data': None
            }
        
        # Analyze betting opportunity
        betting_analysis = analyze_betting_opportunity(
            prediction,
            best_odds,
            kelly_fraction,
            min_value_threshold
        )
        
        # Add match and odds context
        betting_analysis.update({
            'match_info': {
                'match_id': match_id,
                'home_team': prediction.get('home_team'),
                'away_team': prediction.get('away_team'),
                'predicted_result': prediction.get('predicted_result'),
                'model_confidence': prediction.get('confidence')
            },
            'odds_info': best_odds,
            'model_predictions': {
                'prob_home_win': prediction.get('prob_home_win'),
                'prob_draw': prediction.get('prob_draw'),
                'prob_away_win': prediction.get('prob_away_win')
            }
        })
        
        return {
            'success': True,
            'error': None,
            'data': betting_analysis
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Error analyzing betting opportunity: {str(e)}',
            'data': None
        }

def get_betting_recommendations_for_match_teams(
    home_team: str,
    away_team: str,
    kelly_fraction: float = 0.5,
    min_value_threshold: float = 0.05,
    days_ahead: int = 30
) -> Dict[str, Any]:
    """
    Get betting recommendations by team names (finds match first).
    
    Args:
        home_team: Home team name
        away_team: Away team name
        kelly_fraction: Kelly safety fraction
        min_value_threshold: Minimum expected value threshold
        days_ahead: Days to look ahead for matches
        
    Returns:
        Complete betting analysis with percentage recommendations
    """
    try:
        # Find the match first
        from chatbot.functions.match_finder import find_matches_by_teams
        
        matches = find_matches_by_teams(home_team, away_team, days_ahead)
        if not matches:
            return {
                'success': False,
                'error': f'No upcoming matches found between {home_team} and {away_team}',
                'data': None
            }
        
        # Use the best match (highest relevance)
        best_match = matches[0]
        match_id = best_match['match_id']
        
        # Get betting recommendations for this match
        recommendations = get_betting_recommendations(
            match_id, kelly_fraction, min_value_threshold
        )
        
        # Add match finder context
        if recommendations['success']:
            recommendations['data']['match_finder_info'] = {
                'search_teams': f"{home_team} vs {away_team}",
                'found_match': f"{best_match['home_team']} vs {best_match['away_team']}",
                'relevance_score': best_match.get('relevance_score'),
                'start_time': best_match.get('start_time'),
                'competition': best_match.get('competition')
            }
        
        return recommendations
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Error getting betting recommendations: {str(e)}',
            'data': None
        }

def get_value_bets_summary(
    match_ids: List[int],
    kelly_fraction: float = 0.5,
    min_value_threshold: float = 0.05
) -> Dict[str, Any]:
    """
    Get a summary of value bets across multiple matches.
    
    Args:
        match_ids: List of match IDs to analyze
        kelly_fraction: Kelly safety fraction
        min_value_threshold: Minimum expected value threshold
        
    Returns:
        Summary of all value betting opportunities with percentages
    """
    all_value_bets = []
    total_recommended_bets = 0
    total_bet_percentage = 0
    total_potential_profit_percentage = 0
    matches_with_value = 0
    
    for match_id in match_ids:
        recommendations = get_betting_recommendations(
            match_id, kelly_fraction, min_value_threshold
        )
        
        if recommendations['success'] and recommendations['data']['has_value_bets']:
            matches_with_value += 1
            value_bets = recommendations['data']['value_bets']
            
            # Add match context to each bet
            for bet in value_bets:
                bet['match_info'] = recommendations['data']['match_info']
                all_value_bets.append(bet)
            
            total_recommended_bets += len(value_bets)
            total_bet_percentage += recommendations['data']['total_bet_percentage']
            total_potential_profit_percentage += recommendations['data']['total_potential_profit_percentage']
    
    return {
        'total_matches_analyzed': len(match_ids),
        'matches_with_value_bets': matches_with_value,
        'total_value_bets': total_recommended_bets,
        'total_bet_percentage': total_bet_percentage,
        'total_potential_profit_percentage': total_potential_profit_percentage,
        'all_value_bets': sorted(all_value_bets, key=lambda x: x['expected_value'], reverse=True),
        'settings': {
            'kelly_fraction': kelly_fraction,
            'min_value_threshold': min_value_threshold
        }
    } 