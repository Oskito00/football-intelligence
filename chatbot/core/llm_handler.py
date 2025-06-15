"""
LLM Handler - Manages interaction with language models

Handles query parsing and response generation using Claude/GPT.
"""

import json
import re
from typing import Dict, Any, List

class LLMHandler:
    """Handles all LLM interactions for query parsing and response generation."""
    
    def __init__(self):
        """Initialize the LLM handler."""
        # For now, we'll use rule-based parsing instead of actual LLM calls
        # You can later replace this with actual Claude/GPT API calls
        pass
    
    def parse_query(self, user_input: str, conversation_memory: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse user query to extract intent and parameters.
        
        Args:
            user_input: Raw user input
            conversation_memory: Current conversation context
            
        Returns:
            Parsed query with intent and parameters
        """
        user_input_lower = user_input.lower()
        
        # Intent detection patterns - ORDER MATTERS! More specific patterns first
        
        # 1. Check for upcoming value bets FIRST (most specific)
        if (any(word in user_input_lower for word in ['upcoming', 'next', 'future']) and 
            any(word in user_input_lower for word in ['value', 'bet', 'opportunities'])) or \
           (any(phrase in user_input_lower for phrase in ['value bets in', 'best value bets', 'value bets for', 'upcoming value']) and
            not any(phrase in user_input_lower for phrase in [' vs ', ' v ', ' against '])):  # Exclude specific team matchups
            
            intent = "get_upcoming_value_bets"
            
            # Extract time parameters
            days_ahead = 7  # default
            time_patterns = [
                (r'next (\d+) days?', lambda m: int(m.group(1))),
                (r'(\d+) days?', lambda m: int(m.group(1))),
                (r'this week', lambda m: 7),
                (r'next week', lambda m: 7),
                (r'weekend', lambda m: 3),
                (r'today', lambda m: 1),
                (r'tomorrow', lambda m: 2)
            ]
            
            for pattern, extractor in time_patterns:
                match = re.search(pattern, user_input_lower)
                if match:
                    days_ahead = extractor(match)
                    break
            
            # Extract league/competition
            league_query = None
            league_patterns = [
                r'(?:value bets|best value|opportunities)\s+(?:in|for)\s+(?:the\s+)?(.*?)(?:\s*\?|$)',
                r'in\s+(?:the\s+)?(.*?)(?:\s*\?|$)',
                r'for\s+(?:the\s+)?(.*?)(?:\s*\?|$)',
            ]
            
            for pattern in league_patterns:
                match = re.search(pattern, user_input_lower)
                if match:
                    potential_league = match.group(1).strip()
                    # Remove common trailing words but keep league names intact
                    potential_league = re.sub(r'\s+(today|tomorrow|this week|next week|\d+ days?)$', '', potential_league)
                    
                    # Filter out queries that are just common words
                    exclude_phrases = ['next', 'days', 'value', 'bets', 'upcoming', 'best', 'what', 'are', 'the', 'opportunities']
                    if potential_league and potential_league not in exclude_phrases and len(potential_league) > 2:
                        league_query = potential_league.strip()
                        break
            
            return {
                "intent": intent,
                "parameters": {
                    "days_ahead": days_ahead,
                    "league_query": league_query,
                    "max_results": 10
                },
                "confidence": 0.9
            }
        
        # 2. Check for upcoming predictions (before general predictions)
        elif (any(word in user_input_lower for word in ['upcoming', 'next', 'future']) and 
              any(word in user_input_lower for word in ['prediction', 'predict', 'forecast']) and
              not any(word in user_input_lower for word in ['value', 'bet', 'betting'])):
            
            intent = "get_upcoming_predictions"
            
            # Extract time parameters (same logic as value bets)
            days_ahead = 7  # default
            time_patterns = [
                (r'next (\d+) days?', lambda m: int(m.group(1))),
                (r'(\d+) days?', lambda m: int(m.group(1))),
                (r'this week', lambda m: 7),
                (r'next week', lambda m: 7),
                (r'weekend', lambda m: 3),
                (r'today', lambda m: 1),
                (r'tomorrow', lambda m: 2)
            ]
            
            for pattern, extractor in time_patterns:
                match = re.search(pattern, user_input_lower)
                if match:
                    days_ahead = extractor(match)
                    break
            
            # Extract league/competition (same logic as value bets)
            league_query = None
            league_patterns = [
                r'(?:predictions?|forecast)\s+(?:for|in)\s+(?:the\s+)?(.*?)(?:\s*\?|$)',
                r'in\s+(?:the\s+)?(.*?)(?:\s*\?|$)',
                r'for\s+(?:the\s+)?(.*?)(?:\s*\?|$)',
            ]
            
            for pattern in league_patterns:
                match = re.search(pattern, user_input_lower)
                if match:
                    potential_league = match.group(1).strip()
                    # Remove common trailing words but keep league names intact
                    potential_league = re.sub(r'\s+(today|tomorrow|this week|next week|\d+ days?)$', '', potential_league)
                    
                    # Filter out queries that are just common words
                    exclude_phrases = ['next', 'days', 'predictions', 'upcoming', 'what', 'are', 'the']
                    if potential_league and potential_league not in exclude_phrases and len(potential_league) > 2:
                        league_query = potential_league.strip()
                        break
            
            return {
                "intent": intent,
                "parameters": {
                    "days_ahead": days_ahead,
                    "league_query": league_query,
                    "max_results": 15
                },
                "confidence": 0.9
            }
        
        # 3. Check for specific team predictions
        elif any(word in user_input_lower for word in ['prediction', 'predict', 'forecast']):
            intent = "get_match_prediction"
            
            # Extract team names using improved patterns
            team_patterns = [
                # Direct team vs team patterns
                r'\b([A-Za-z]+(?:\s+[A-Za-z]+){0,2})\s+(?:vs|v|against)\s+([A-Za-z]+(?:\s+[A-Za-z]+){0,2})\b',
                # "predictions for team vs team" pattern
                r'predictions?\s+for\s+([A-Za-z]+(?:\s+[A-Za-z]+){0,2})\s+(?:vs|v|against)\s+([A-Za-z]+(?:\s+[A-Za-z]+){0,2})',
                # "team playing team" pattern
                r'\b([A-Za-z]+(?:\s+[A-Za-z]+){0,2})\s+(?:playing|versus)\s+([A-Za-z]+(?:\s+[A-Za-z]+){0,2})\b',
                # "between team and team" pattern
                r'between\s+([A-Za-z]+(?:\s+[A-Za-z]+){0,2})\s+and\s+([A-Za-z]+(?:\s+[A-Za-z]+){0,2})'
            ]
            
            home_team = None
            away_team = None
            
            for pattern in team_patterns:
                match = re.search(pattern, user_input_lower)
                if match:
                    home_team = match.group(1).strip().title()
                    away_team = match.group(2).strip().title()
                    break
            
            return {
                "intent": intent,
                "parameters": {
                    "home_team": home_team,
                    "away_team": away_team
                },
                "confidence": 0.8 if home_team and away_team else 0.4
            }
        
        # 4. Check for specific team betting value (requires team names)
        elif (any(word in user_input_lower for word in ['value', 'bet', 'odds', 'betting', 'kelly', 'bankroll', 'recommend']) and
              any(phrase in user_input_lower for phrase in [' vs ', ' v ', ' against ', ' playing '])):
            
            intent = "get_betting_value"
            
            # Extract team names for betting queries
            team_patterns = [
                r'\b([A-Za-z]+(?:\s+[A-Za-z]+){0,2})\s+(?:vs|v|against)\s+([A-Za-z]+(?:\s+[A-Za-z]+){0,2})\b',
                r'(?:value|bet|odds).*?for\s+([A-Za-z]+(?:\s+[A-Za-z]+){0,2})\s+(?:vs|v|against)\s+([A-Za-z]+(?:\s+[A-Za-z]+){0,2})',
                r'between\s+([A-Za-z]+(?:\s+[A-Za-z]+){0,2})\s+and\s+([A-Za-z]+(?:\s+[A-Za-z]+){0,2})'
            ]
            
            home_team = None
            away_team = None
            
            for pattern in team_patterns:
                match = re.search(pattern, user_input_lower)
                if match:
                    home_team = match.group(1).strip().title()
                    away_team = match.group(2).strip().title()
                    break
            
            # Extract bankroll if mentioned
            bankroll_match = re.search(r'bankroll\s+(\d+)', user_input_lower)
            bankroll = int(bankroll_match.group(1)) if bankroll_match else 1000
            
            return {
                "intent": intent,
                "parameters": {
                    "home_team": home_team,
                    "away_team": away_team,
                    "bankroll": bankroll
                },
                "confidence": 0.8 if home_team and away_team else 0.6
            }
        
        else:
            return {
                "intent": "general_chat",
                "parameters": {},
                "confidence": 0.3
            }
    
    def generate_response(
        self, 
        user_input: str,
        parsed_query: Dict[str, Any],
        function_result: Dict[str, Any],
        conversation_memory: Dict[str, Any]
    ) -> str:
        """
        Generate natural language response based on function results.
        
        Args:
            user_input: Original user input
            parsed_query: Parsed query with intent and parameters
            function_result: Result from function dispatch
            conversation_memory: Current conversation context
            
        Returns:
            Natural language response
        """
        intent = parsed_query.get("intent", "unknown")
        
        if function_result.get("error"):
            return f"I'm sorry, but I encountered an issue: {function_result['error']}"
        
        if intent == "get_match_prediction":
            if function_result.get("success") and function_result.get("data"):
                data = function_result["data"]
                prediction = data.get("prediction")
                
                if prediction:
                    home_team = prediction.get("home_team", "Home Team")
                    away_team = prediction.get("away_team", "Away Team")
                    predicted_result = prediction.get("predicted_result")
                    confidence = prediction.get("confidence", 0)
                    
                    # Generate natural response
                    if predicted_result == "Home Win":
                        response = f"Based on my analysis, **{home_team}** is likely to beat {away_team}."
                    elif predicted_result == "Away Win":
                        response = f"Based on my analysis, **{away_team}** is likely to beat {home_team}."
                    else:
                        response = f"Based on my analysis, {home_team} vs {away_team} is likely to end in a **draw**."
                    
                    response += f" My confidence in this prediction is {confidence:.1%}."
                    
                    # Add additional details if available
                    if prediction.get("prob_home_win"):
                        response += "\n\nDetailed probabilities:"
                        response += f"\n• {home_team} win: {prediction['prob_home_win']:.1%}"
                        response += f"\n• Draw: {prediction['prob_draw']:.1%}"
                        response += f"\n• {away_team} win: {prediction['prob_away_win']:.1%}"
                    
                    return response
            
            # Fallback if no specific prediction found
            home_team = parsed_query["parameters"].get("home_team", "the teams")
            away_team = parsed_query["parameters"].get("away_team", "")
            team_text = f"{home_team} vs {away_team}" if away_team else home_team
            
            return f"I couldn't find a specific prediction for {team_text}. This might be because the match isn't scheduled soon, or I don't have data for these teams."
        
        elif intent == "get_betting_value":
            if function_result.get("success") and function_result.get("data"):
                data = function_result["data"]
                
                if data.get("has_value_bets"):
                    match_info = data.get("match_info", {})
                    model_predictions = data.get("model_predictions", {})
                    home_team = match_info.get("home_team", "Home Team")
                    away_team = match_info.get("away_team", "Away Team")
                    
                    response = f"📊 **Betting Analysis for {home_team} vs {away_team}**\n\n"
                    
                    # Show model's predictions first
                    response += "🤖 **Model Predictions:**\n"
                    response += f"   • {home_team} win: {model_predictions.get('prob_home_win', 0):.1%}\n"
                    response += f"   • Draw: {model_predictions.get('prob_draw', 0):.1%}\n"
                    response += f"   • {away_team} win: {model_predictions.get('prob_away_win', 0):.1%}\n\n"
                    
                    # Find most probable outcome
                    probs = {
                        'Home Win': model_predictions.get('prob_home_win', 0),
                        'Draw': model_predictions.get('prob_draw', 0),
                        'Away Win': model_predictions.get('prob_away_win', 0)
                    }
                    most_probable_outcome = max(probs, key=probs.get)
                    
                    # Show value bets
                    value_bets = data.get("value_bets", [])
                    if value_bets:
                        response += f"💰 **Found {len(value_bets)} Value Bet(s):**\n\n"
                        
                        for i, bet in enumerate(value_bets, 1):  # Show top 3
                            outcome = bet['outcome']
                            model_prob = bet['model_probability']
                            is_most_probable = outcome == most_probable_outcome
                            
                            # Choose emoji and risk description based on outcome and probability
                            if outcome == "Home Win":
                                outcome_emoji = "🏠"
                            elif outcome == "Draw":
                                outcome_emoji = "🤝"
                            else:  # Away Win
                                outcome_emoji = "✈️"
                            
                            # Risk level and color
                            if is_most_probable:
                                risk_emoji = "🟢"
                                risk_text = "**Safe Value Bet**"
                            else:
                                risk_emoji = "🟡" if model_prob > 0.25 else "🔶"
                                risk_text = "**Risky Value Bet**"
                            
                            response += f"{risk_emoji} **{i}. {outcome_emoji} {outcome}** @ {bet['odds_value']:.2f} ({bet['bookmaker_name']})\n"
                            response += f"   • **Model Probability:** {model_prob:.1%}\n"
                            response += f"   • **Expected Value:** {bet['value_percentage']:.1f}%\n"
                            response += f"   • **Recommended:** {bet['recommended_bet_percentage']:.1f}% of bankroll\n"
                            response += f"   • **Risk Level:** {risk_text}\n\n"
                        
                        # Summary
                        stats = data.get('summary_stats', {})
                        response += f"💰 **Total Recommended:** {stats.get('total_bet_percentage', 0):.1f}% of bankroll\n"
                        response += f"📈 **Total Potential Profit:** {stats.get('total_potential_profit_percentage', 0):.1f}% of bankroll"
                    
                    return response
                else:
                    match_info = data.get("match_info", {})
                    home_team = match_info.get("home_team", "the teams")
                    away_team = match_info.get("away_team", "")
                    team_text = f"{home_team} vs {away_team}" if away_team else home_team
                    
                    return f"🔍 I analyzed the betting odds for {team_text} but didn't find any value bets that meet the minimum threshold. The bookmaker odds seem fairly priced compared to my model's predictions."
            
            return "I can help with betting value analysis! Please specify which match you'd like me to analyze, e.g., 'What are the value bets for Arsenal vs Chelsea?'"
        
        elif intent == "get_upcoming_value_bets":
            if function_result.get("success") and function_result.get("data"):
                data = function_result["data"]
                criteria = data.get("search_criteria", {})
                summary = data.get("analysis_summary", {})
                value_bets = data.get("value_bets", [])
                
                # Build response header
                response = "🎯 **Upcoming Value Betting Opportunities**\n\n"
                
                # Add search criteria
                response += f"📅 **Search Period:** Next {criteria.get('days_ahead', 7)} days\n"
                if criteria.get('league_info'):
                    league_info = criteria['league_info']
                    response += f"🏆 **Competition:** {league_info['league_name']}\n"
                response += f"📊 **Kelly Fraction:** {criteria.get('kelly_fraction', 0.50)*100:.0f}% of optimal\n\n"
                
                # Summary stats
                response += "📈 **Analysis Summary:**\n"
                response += f"   • Matches found: {summary.get('total_matches_found', 0)}\n"
                response += f"   • Matches analyzed: {summary.get('matches_analyzed', 0)}\n"
                response += f"   • Value opportunities: {summary.get('total_value_opportunities', 0)}\n\n"
                
                if value_bets:
                    response += f"💰 **Top Value Bets (showing all {len(value_bets)}):**\n\n"
                    
                    for i, bet in enumerate(value_bets, 1):
                        # Get match info  
                        home_team = bet.get('home_team', 'Unknown')
                        away_team = bet.get('away_team', 'Unknown')
                        outcome = bet.get('outcome', 'Unknown')
                        predicted_result = bet.get('predicted_result', 'Unknown')
                        
                        # Probability info
                        model_prob_pct = bet.get('model_probability', 0) * 100
                        odds_value = bet.get('odds_value', 0)
                        expected_value_pct = bet.get('value_percentage', 0)
                        
                        # Betting recommendation
                        bet_pct = bet.get('recommended_bet_percentage', 0)
                        
                        # Risk assessment with emojis
                        is_favorite = outcome == predicted_result
                        if is_favorite and model_prob_pct >= 40:
                            risk_emoji = "💚"  # Safe bet
                            risk_text = "**Favorite Pick**"
                        elif is_favorite and model_prob_pct >= 30:
                            risk_emoji = "💛"  # Medium risk
                            risk_text = "**Likely Pick**"
                        else:
                            risk_emoji = "🔥"  # Risky but valuable
                            risk_text = "**Risky but Valuable**"
                        
                        response += f"{risk_emoji} **{i}. {home_team} vs {away_team}**\n"
                        response += f"   📍 **Bet:** {outcome} @ {odds_value:.2f} odds\n"
                        response += f"   🎯 **Model Probability:** {model_prob_pct:.1f}% ({risk_text})\n"
                        response += f"   💎 **Expected Value:** +{expected_value_pct:.1f}%\n"
                        response += f"   💰 **Recommend:** {bet_pct:.1f}% of bankroll\n"
                        response += f"   📅 **Match:** {bet.get('start_time', 'TBD')}\n\n"
                        
                else:
                    response += "❌ **No value bets found** meeting the criteria.\n"
                    response += "Try adjusting the time period or competition filter.\n"
                    
                # Add total risk summary
                if value_bets:
                    total_bet_pct = sum(bet.get('recommended_bet_percentage', 0) for bet in value_bets)
                    response += f"⚠️ **Total Portfolio Risk:** {total_bet_pct:.1f}% of bankroll\n"
                    response += "💡 **Note:** These are independent bets - consider your total risk exposure!"
                    
                return response
            else:
                return "I couldn't find any upcoming matches to analyze for value bets. Try specifying a different time period or competition."
        
        elif intent == "get_upcoming_predictions":
            if function_result.get("success") and function_result.get("data"):
                data = function_result["data"]
                criteria = data.get("search_criteria", {})
                predictions = data.get("predictions", [])
                
                response = "🔮 **Upcoming Match Predictions**\n\n"
                
                # Add search criteria
                response += f"📅 **Period:** Next {criteria.get('days_ahead', 7)} days\n"
                if criteria.get('league_info'):
                    league_info = criteria['league_info']
                    response += f"🏆 **Competition:** {league_info['league_name']}\n"
                response += f"📊 **Found {len(predictions)} predictions**\n\n"
                
                if predictions:
                    for i, pred in enumerate(predictions, 1):  # Show top 10
                        # Access data directly from pred (not nested)
                        home_team = pred.get("home_team", "Unknown")
                        away_team = pred.get("away_team", "Unknown") 
                        predicted_result = pred.get("predicted_result", "Unknown")
                        confidence = pred.get("confidence", 0)
                        start_time = pred.get("start_time", "TBD")
                        competition = pred.get("competition", "Unknown")
                        
                        # Confidence emoji
                        if confidence >= 0.7:
                            conf_emoji = "🟢"
                        elif confidence >= 0.5:
                            conf_emoji = "🟡"
                        else:
                            conf_emoji = "🔴"
                        
                        response += f"{conf_emoji} **{i}. {home_team} vs {away_team}**\n"
                        response += f"   🎯 **Prediction:** {predicted_result}\n"
                        response += f"   📊 **Confidence:** {confidence:.1%}\n"
                        
                        # Add probabilities if available
                        prob_home = pred.get("prob_home_win")
                        prob_draw = pred.get("prob_draw") 
                        prob_away = pred.get("prob_away_win")
                        
                        if prob_home and prob_draw and prob_away:
                            response += f"   📈 **Probabilities:** {home_team} {prob_home:.1%} | "
                            response += f"Draw {prob_draw:.1%} | {away_team} {prob_away:.1%}\n"
                        
                        response += f"   🏆 **Competition:** {competition}\n"
                        response += f"   📅 **Match:** {start_time}\n\n"
                        
                else:
                    response += "❌ **No predictions found** for the specified criteria.\n"
                    
                return response
            else:
                return "I couldn't find any upcoming matches to predict. Try specifying a different time period or competition."
        
        elif intent == "general_chat":
            return "I'm here to help with football predictions and betting analytics! Try asking me about predictions for specific matches, or value betting opportunities like 'What are the value bets for Manchester United vs Liverpool?'"
        
        else:
            return "I'm not sure how to help with that. I specialize in football predictions and betting analytics. Try asking about match predictions or betting advice!" 