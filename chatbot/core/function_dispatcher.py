"""
Function Dispatcher - Routes queries to appropriate analytics functions

Maps intents to specific functions and handles function execution.
"""

import time
from typing import Dict, Any, Callable
import traceback

from chatbot.functions.match_predictions import get_match_prediction
from chatbot.functions.match_finder import find_matches_by_teams
from chatbot.functions.betting_recommendations import (
    get_betting_recommendations_for_match_teams,
    get_betting_recommendations
)
from chatbot.functions.upcoming_value_bets import get_upcoming_value_bets
from chatbot.functions.upcoming_predictions import get_upcoming_predictions

class FunctionDispatcher:
    """Dispatches parsed queries to appropriate analytics functions."""
    
    def __init__(self):
        """Initialize the dispatcher with function mappings."""
        self.function_map = {
            "get_match_prediction": self._handle_match_prediction,
            "get_betting_value": self._handle_betting_value,
            "get_betting_recommendations": self._handle_betting_recommendations,
            "get_upcoming_value_bets": self._handle_upcoming_value_bets,
            "get_upcoming_predictions": self._handle_upcoming_predictions,
            "general_chat": self._handle_general_chat
        }
    
    def dispatch(self, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatch parsed query to appropriate function.
        
        Args:
            parsed_query: Parsed query with intent and parameters
            
        Returns:
            Function execution result
        """
        intent = parsed_query.get("intent", "unknown")
        
        if intent not in self.function_map:
            return {
                "success": False,
                "error": f"Unknown intent: {intent}",
                "data": None
            }
        
        try:
            handler = self.function_map[intent]
            result = handler(parsed_query)
            return result
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Function execution failed: {str(e)}",
                "data": None,
                "traceback": traceback.format_exc()
            }
    
    def _handle_match_prediction(self, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """Handle match prediction requests."""
        parameters = parsed_query.get("parameters", {})
        home_team = parameters.get("home_team")
        away_team = parameters.get("away_team")
        
        if not home_team or not away_team:
            return {
                "success": False,
                "error": "Both home and away teams must be specified for predictions",
                "data": None
            }
        
        # First, try to find the match
        start_time_find_matches = time.time()
        matches = find_matches_by_teams(home_team, away_team)
        end_time_find_matches = time.time()
        print(f"Time taken to find matches: {end_time_find_matches - start_time_find_matches} seconds")
        
        if not matches:
            return {
                "success": False,
                "error": f"No upcoming matches found between {home_team} and {away_team}",
                "data": None
            }
        
        # Use the first (most relevant) match found
        match = matches[0]
        match_id = match["match_id"]
        
        # Get prediction for this match
        start_time_get_prediction = time.time()
        prediction = get_match_prediction(match_id)
        end_time_get_prediction = time.time()
        print(f"Time taken to get prediction: {end_time_get_prediction - start_time_get_prediction} seconds")
        
        if not prediction:
            return {
                "success": False,
                "error": f"No prediction available for match {match_id}",
                "data": None
            }
        
        return {
            "success": True,
            "error": None,
            "data": {
                "match": match,
                "prediction": prediction
            }
        }
    
    def _handle_betting_value(self, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """Handle betting value analysis requests."""
        parameters = parsed_query.get("parameters", {})
        home_team = parameters.get("home_team")
        away_team = parameters.get("away_team")
        
        if home_team and away_team:
            # Get betting recommendations for specific match
            return get_betting_recommendations_for_match_teams(home_team, away_team)
        else:
            return {
                "success": False,
                "error": "Please specify teams for betting value analysis, e.g., 'What are the value bets for Arsenal vs Chelsea?'",
                "data": None
            }
    
    def _handle_betting_recommendations(self, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """Handle betting recommendations requests."""
        parameters = parsed_query.get("parameters", {})
        match_id = parameters.get("match_id")
        home_team = parameters.get("home_team")
        away_team = parameters.get("away_team")
        
        if match_id:
            # Direct match ID provided
            return get_betting_recommendations(match_id)
        elif home_team and away_team:
            # Team names provided
            return get_betting_recommendations_for_match_teams(home_team, away_team)
        else:
            return {
                "success": False,
                "error": "Please specify either match_id or team names for betting recommendations",
                "data": None
            }
    
    def _handle_upcoming_value_bets(self, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """Handle upcoming value bets requests."""
        parameters = parsed_query.get("parameters", {})
        
        days_ahead = parameters.get("days_ahead", 7)
        league_query = parameters.get("league_query")
        max_results = parameters.get("max_results", 10)
        
        return get_upcoming_value_bets(
            days_ahead=days_ahead,
            league_query=league_query,
            max_results=max_results
        )
    
    def _handle_upcoming_predictions(self, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """Handle upcoming predictions requests."""
        parameters = parsed_query.get("parameters", {})
        
        days_ahead = parameters.get("days_ahead", 7)
        league_query = parameters.get("league_query")
        max_results = parameters.get("max_results", 15)
        
        return get_upcoming_predictions(
            days_ahead=days_ahead,
            league_query=league_query,
            max_results=max_results
        )
    
    def _handle_general_chat(self, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general chat requests."""
        return {
            "success": True,
            "error": None,
            "data": {
                "message": "General chat response"
            }
        }
    
    def register_function(self, intent: str, function: Callable) -> None:
        """
        Register a new function for a specific intent.
        
        Args:
            intent: The intent name
            function: The function to handle this intent
        """
        self.function_map[intent] = function
    
    def list_available_intents(self) -> list:
        """Return list of available intents."""
        return list(self.function_map.keys()) 