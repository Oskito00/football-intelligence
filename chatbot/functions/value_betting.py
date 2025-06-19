"""
Value Betting - Calculate value bets and optimal bet sizing

Implements Kelly Criterion and value betting calculations using percentages.
"""

from typing import Dict, Any, List, Optional, Tuple
import math

def calculate_value_bets(
    model_predictions: Dict[str, float], 
    best_odds: Dict[str, Dict[str, Any]],
    min_value_threshold: float = 0.05
) -> List[Dict[str, Any]]:
    """
    Calculate value bets by comparing model predictions to bookmaker odds.
    
    Args:
        model_predictions: Model probabilities {'prob_home_win': 0.48, 'prob_draw': 0.18, 'prob_away_win': 0.34}
        best_odds: Best odds for each outcome from odds_retrieval
        min_value_threshold: Minimum expected value to consider a bet (default 5%)
        
    Returns:
        List of value bet opportunities
    """
    value_bets = []
    
    # Map prediction keys to odds keys
    prediction_mapping = {
        'prob_home_win': 'Home Win',
        'prob_draw': 'Draw', 
        'prob_away_win': 'Away Win'
    }
    
    # Check each outcome for value
    for pred_key, odds_key in prediction_mapping.items():
        if pred_key in model_predictions and odds_key in best_odds:
            model_prob = model_predictions[pred_key]
            odds_info = best_odds[odds_key]
            odds_value = odds_info['odds_value']
            implied_prob = odds_info['implied_probability']
            
            # Calculate expected value: (model_prob * odds) - 1
            expected_value = (model_prob * odds_value) - 1
            
            # Only include if positive value above threshold
            if expected_value > min_value_threshold:
                value_bets.append({
                    'outcome': odds_key,
                    'model_probability': model_prob,
                    'odds_value': odds_value,
                    'implied_probability': implied_prob,
                    'expected_value': expected_value,
                    'value_percentage': expected_value * 100,
                    'bookmaker_name': odds_info['bookmaker_name'],
                    'bookmaker_id': odds_info['bookmaker_id']
                })
    
    # Sort by expected value (highest first)
    value_bets.sort(key=lambda x: x['expected_value'], reverse=True)
    
    return value_bets

def calculate_kelly_bet_size(
    model_probability: float,
    odds_value: float,
    kelly_fraction: float = 0.5,
    max_bet_percentage: float = 0.50
) -> Dict[str, Any]:
    """
    Calculate optimal bet size using Kelly Criterion as percentage of bankroll.
    
    Args:
        model_probability: Our model's win probability (0-1)
        odds_value: Decimal odds from bookmaker
        kelly_fraction: Fraction of full Kelly to use (0.50 = 50% Kelly for safety)
        max_bet_percentage: Maximum percentage of bankroll to bet (0.50 = 50%)
        
    Returns:
        Dictionary with bet sizing percentages
    """
    # Kelly formula: f = (bp - q) / b
    # where: b = odds - 1, p = win probability, q = lose probability
    b = odds_value - 1  # Net odds
    p = model_probability
    q = 1 - p
    
    # Full Kelly percentage
    kelly_full = (b * p - q) / b
    
    # Apply safety fraction
    kelly_fractional = kelly_full * kelly_fraction
    
    # Cap at maximum bet percentage
    recommended_percentage = min(kelly_fractional, max_bet_percentage)
    
    # Ensure positive (should be since we only call this for value bets)
    recommended_percentage = max(recommended_percentage, 0)
    
    return {
        'kelly_full_percentage': kelly_full,
        'kelly_fractional_percentage': kelly_fractional,
        'recommended_percentage': recommended_percentage,
        'kelly_fraction_used': kelly_fraction,
        'max_bet_cap': max_bet_percentage,
        'is_capped': recommended_percentage >= max_bet_percentage
    }

def calculate_bet_percentages(
    value_bets: List[Dict[str, Any]],
    kelly_fraction: float = 0.50,
    max_bet_percentage: float = 0.50
) -> List[Dict[str, Any]]:
    """
    Calculate bet percentages for all value bets.
    
    Args:
        value_bets: List of value bets from calculate_value_bets()
        kelly_fraction: Kelly fraction for safety (0.50 = 50% Kelly)
        max_bet_percentage: Maximum percentage of bankroll per bet
        
    Returns:
        List of value bets with bet sizing percentages added
    """
    bets_with_sizing = []
    
    for bet in value_bets:
        kelly_info = calculate_kelly_bet_size(
            bet['model_probability'],
            bet['odds_value'],
            kelly_fraction,
            max_bet_percentage
        )
        
        bet_percentage = kelly_info['recommended_percentage']
        potential_profit_ratio = bet_percentage * (bet['odds_value'] - 1)
        
        bet_with_sizing = bet.copy()
        bet_with_sizing.update({
            'kelly_info': kelly_info,
            'recommended_bet_percentage': bet_percentage * 100,  # Convert to percentage
            'potential_profit_percentage': potential_profit_ratio * 100,  # Potential profit as % of bankroll
            'risk_reward_ratio': potential_profit_ratio / bet_percentage if bet_percentage > 0 else 0
        })
        
        bets_with_sizing.append(bet_with_sizing)
    
    return bets_with_sizing

def analyze_betting_opportunity(
    model_predictions: Dict[str, float],
    best_odds: Dict[str, Dict[str, Any]],
    kelly_fraction: float = 0.50,
    min_value_threshold: float = 0.05
) -> Dict[str, Any]:
    """
    Complete analysis of betting opportunity for a match.
    
    Args:
        model_predictions: Model probabilities
        best_odds: Best odds for each outcome
        kelly_fraction: Kelly safety fraction
        min_value_threshold: Minimum value to consider
        
    Returns:
        Complete betting analysis with percentages
    """
    # Find value bets
    value_bets = calculate_value_bets(model_predictions, best_odds, min_value_threshold)
    
    # Calculate bet sizing for value bets
    if value_bets:
        bets_with_sizing = calculate_bet_percentages(value_bets, kelly_fraction)
        total_bet_percentage = sum(bet['recommended_bet_percentage'] for bet in bets_with_sizing)
        total_potential_profit_percentage = sum(bet['potential_profit_percentage'] for bet in bets_with_sizing)
    else:
        bets_with_sizing = []
        total_bet_percentage = 0
        total_potential_profit_percentage = 0
    
    return {
        'has_value_bets': len(value_bets) > 0,
        'number_of_value_bets': len(value_bets),
        'value_bets': bets_with_sizing,
        'total_bet_percentage': total_bet_percentage,
        'total_potential_profit_percentage': total_potential_profit_percentage,
        'kelly_fraction_used': kelly_fraction,
        'min_value_threshold': min_value_threshold
    }

def analyze_multiple_matches_for_value(
    match_ids: List[int],
    kelly_fraction: float = 0.50,
    min_value_threshold: float = 0.05
) -> Dict[str, Any]:
    """
    Analyze multiple matches for value betting opportunities.
    
    Args:
        match_ids: List of match IDs to analyze
        kelly_fraction: Kelly safety fraction
        min_value_threshold: Minimum expected value threshold
        
    Returns:
        Comprehensive analysis across all matches
    """
    if not match_ids:
        return {
            'total_matches_analyzed': 0,
            'matches_with_predictions': 0,
            'matches_with_odds': 0,
            'matches_with_value_bets': 0,
            'total_value_bets': 0,
            'all_value_bets': [],
            'error': 'No match IDs provided'
        }
    
    try:
        # Import here to avoid circular imports
        from chatbot.functions.match_predictions import get_multiple_match_predictions
        from chatbot.functions.odds_retrieval import get_best_odds_for_multiple_matches
        
        # Get predictions and odds for all matches
        predictions = get_multiple_match_predictions(match_ids)
        odds = get_best_odds_for_multiple_matches(match_ids)
        
        print(f"📊 Analyzing {len(match_ids)} matches for value bets...")
        print(f"   • Found predictions for {len(predictions)} matches")
        print(f"   • Found odds for {len(odds)} matches")
        
        all_value_bets = []
        matches_with_value = 0
        matches_processed = 0
        
        # Analyze each match that has both predictions and odds
        for match_id in match_ids:
            if match_id in predictions and match_id in odds:
                matches_processed += 1
                prediction = predictions[match_id]
                match_odds = odds[match_id]
                
                # Analyze this match for value
                analysis = analyze_betting_opportunity(
                    prediction,
                    match_odds,
                    kelly_fraction,
                    min_value_threshold
                )
                
                if analysis['has_value_bets']:
                    matches_with_value += 1
                    
                    # Add match context to each bet
                    for bet in analysis['value_bets']:
                        bet_with_context = bet.copy()
                        bet_with_context.update({
                            'match_id': match_id,
                            'home_team': prediction.get('home_team'),
                            'away_team': prediction.get('away_team'),
                            'predicted_result': prediction.get('predicted_result'),
                            'model_confidence': prediction.get('confidence'),
                            'prediction_date': prediction.get('prediction_date')
                        })
                        all_value_bets.append(bet_with_context)
        
        # Sort all value bets by expected value
        all_value_bets.sort(key=lambda x: x['expected_value'], reverse=True)
        
        # Calculate summary statistics
        total_bet_percentage = sum(bet['recommended_bet_percentage'] for bet in all_value_bets)
        total_potential_profit = sum(bet['potential_profit_percentage'] for bet in all_value_bets)
        
        return {
            'total_matches_analyzed': len(match_ids),
            'matches_with_predictions': len(predictions),
            'matches_with_odds': len(odds),
            'matches_processed': matches_processed,
            'matches_with_value_bets': matches_with_value,
            'total_value_bets': len(all_value_bets),
            'all_value_bets': all_value_bets,
            'summary': {
                'total_bet_percentage': total_bet_percentage,
                'total_potential_profit_percentage': total_potential_profit,
                'average_expected_value': sum(bet['expected_value'] for bet in all_value_bets) / len(all_value_bets) if all_value_bets else 0,
                'kelly_fraction': kelly_fraction,
                'min_value_threshold': min_value_threshold
            }
        }
        
    except Exception as e:
        return {
            'total_matches_analyzed': len(match_ids),
            'matches_with_predictions': 0,
            'matches_with_odds': 0,
            'matches_with_value_bets': 0,
            'total_value_bets': 0,
            'all_value_bets': [],
            'error': f'Error analyzing matches: {str(e)}'
        } 