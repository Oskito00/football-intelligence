"""
Match Predictions - Get predictions for specific matches

Retrieves predictions for matches by match_id from the database only.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

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

def get_match_prediction(match_id: int) -> Optional[Dict[str, Any]]:
    """
    Get prediction for a specific match from the database.
    
    Args:
        match_id: The match ID to get predictions for
        
    Returns:
        Prediction data dictionary or None if not found
    """
    if not DB_AVAILABLE:
        return None
    
    try:
        return _get_prediction_from_db(match_id)
    except Exception as e:
        print(f"Error getting prediction for match {match_id}: {str(e)}")
        return None

def get_multiple_match_predictions(match_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """
    Get predictions for multiple matches efficiently.
    
    Args:
        match_ids: List of match IDs to get predictions for
        
    Returns:
        Dictionary mapping match_id to prediction data
        Only includes matches that have predictions available
    """
    if not DB_AVAILABLE:
        return {}
    
    if not match_ids:
        return {}
    
    predictions = {}
    
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
        
        # Get predictions for all match_ids in one query
        placeholders = ','.join(['%s'] * len(match_ids))
        prediction_query = f"""
        SELECT 
            match_id,
            predicted_result,
            home_team_name,
            away_team_name,
            prob_home_win,
            prob_draw,
            prob_away_win,
            model_type,
            prediction_timestamp
        FROM match_result_predictions 
        WHERE match_id IN ({placeholders})
        ORDER BY match_id, prediction_timestamp DESC
        """
        
        cursor.execute(prediction_query, match_ids)
        prediction_rows = cursor.fetchall()
        
        # Process predictions (take most recent for each match)
        processed_matches = set()
        for row in prediction_rows:
            match_id = row['match_id']
            
            # Skip if we already processed this match (since we ordered by timestamp DESC)
            if match_id in processed_matches:
                continue
            
            processed_matches.add(match_id)
            
            # Map predicted_result integer to string
            result_mapping = {2: "Home Win", 1: "Draw", 0: "Away Win"}
            predicted_result = result_mapping.get(row['predicted_result'], "Unknown")
            
            # Calculate confidence (use the highest probability)
            probs = [
                row.get('prob_home_win', 0) or 0,
                row.get('prob_draw', 0) or 0, 
                row.get('prob_away_win', 0) or 0
            ]
            confidence = max(probs) if any(probs) else 0.5
            
            predictions[match_id] = {
                "match_id": match_id,
                "home_team": row['home_team_name'],
                "away_team": row['away_team_name'],
                "predicted_result": predicted_result,
                "confidence": confidence,
                "prob_home_win": row.get('prob_home_win', 0) or 0,
                "prob_draw": row.get('prob_draw', 0) or 0,
                "prob_away_win": row.get('prob_away_win', 0) or 0,
                "model_type": row.get('model_type', 'unknown'),
                "prediction_date": row.get('prediction_timestamp')
            }
        
        cursor.close()
        conn.close()
        
        return predictions
        
    except Exception as e:
        print(f"Error getting multiple predictions: {str(e)}")
        return {}

def _get_prediction_from_db(match_id: int) -> Optional[Dict[str, Any]]:
    """
    Get prediction from database for a single match.
    
    Args:
        match_id: Match ID
        
    Returns:
        Prediction data or None
    """
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
        
        # Get prediction from match_result_predictions table
        prediction_query = """
        SELECT 
            match_id,
            predicted_result,
            home_team_name,
            away_team_name,
            prob_home_win,
            prob_draw,
            prob_away_win,
            model_type,
            prediction_timestamp
        FROM match_result_predictions 
        WHERE match_id = %s
        ORDER BY prediction_timestamp DESC
        LIMIT 1
        """
        
        cursor.execute(prediction_query, (match_id,))
        prediction_row = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if prediction_row:
            # Map predicted_result integer to string
            result_mapping = {2: "Home Win", 1: "Draw", 0: "Away Win"}
            predicted_result = result_mapping.get(prediction_row['predicted_result'], "Unknown")
            
            # Calculate confidence (use the highest probability)
            probs = [
                prediction_row.get('prob_home_win', 0) or 0,
                prediction_row.get('prob_draw', 0) or 0, 
                prediction_row.get('prob_away_win', 0) or 0
            ]
            confidence = max(probs) if any(probs) else 0.5
            
            return {
                "match_id": match_id,
                "home_team": prediction_row['home_team_name'],
                "away_team": prediction_row['away_team_name'],
                "predicted_result": predicted_result,
                "confidence": confidence,
                "prob_home_win": prediction_row.get('prob_home_win', 0) or 0,
                "prob_draw": prediction_row.get('prob_draw', 0) or 0,
                "prob_away_win": prediction_row.get('prob_away_win', 0) or 0,
                "model_type": prediction_row.get('model_type', 'unknown'),
                "prediction_date": prediction_row.get('prediction_timestamp')
            }
        
        return None
        
    except Exception as e:
        print(f"Database error getting prediction for match {match_id}: {str(e)}")
        return None

def get_predictions_by_team(team_name: str, days_ahead: int = 14) -> List[Dict[str, Any]]:
    """
    Get all predictions for a specific team's upcoming matches.
    
    Args:
        team_name: Name of the team
        days_ahead: Number of days to look ahead
        
    Returns:
        List of predictions for team's matches
    """
    from chatbot.functions.match_finder import search_team_matches
    
    # Get team's upcoming matches
    team_matches = search_team_matches(team_name, days_ahead)
    
    if not team_matches:
        return []
    
    # Extract match IDs
    match_ids = [match['match_id'] for match in team_matches]
    
    # Get predictions for all matches
    predictions_dict = get_multiple_match_predictions(match_ids)
    
    # Convert to list and add match context
    predictions = []
    for match in team_matches:
        match_id = match['match_id']
        if match_id in predictions_dict:
            prediction = predictions_dict[match_id].copy()
            # Add match context to prediction
            prediction.update({
                "start_time": match['start_time'],
                "competition": match['competition'],
                "country": match['country']
            })
            predictions.append(prediction)
    
    return predictions 