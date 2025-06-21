"""
LLM Handler using Groq's LLaMA-4 for all NLP tasks.
Aligned with existing function dispatchers.
"""

import json
import os
from typing import Dict, Any, List, Tuple, Optional
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


class GroqLLM:
    """Wrapper for Groq API calls."""
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "meta-llama/llama-4-scout-17b-16e-instruct"
    
    def call(self, messages: List[Dict[str, str]]) -> Dict:
        """Make a call to Groq API."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model,
            "messages": messages
        }
        
        response = requests.post(self.api_url, headers=headers, json=data)
        return response.json()


class LLMHandler:
    """LLM handler using Groq for all NLP tasks."""
    
    def __init__(self):
        """Initialize the LLM handler."""
        self.llm = GroqLLM()
    
    def _format_conversation_history(self, conversation_memory: Dict[str, Any]) -> str:
        """Format recent conversation history for context."""
        messages = conversation_memory.get("messages", [])
        recent_messages = messages[-6:] if len(messages) > 6 else messages
        
        formatted_history = ""
        for msg in recent_messages:
            role = "User" if msg.get("role") == "user" else "Assistant"
            formatted_history += f"{role}: {msg.get('content')}\n"
        
        return formatted_history.strip()

    def parse_query(self, user_input: str, conversation_memory: Dict[str, Any]) -> Dict[str, Any]:
        """Parse user query using Groq to extract intent and parameters."""
        
        prompt = [
            {
                "role": "system",
                "content": """Your name is Ian. You are a football betting assistant. Your job is to classify user queries into one of these functions and extract the parameters:

1. get_match_prediction
   - home_team (required)
   - away_team (required)

2. get_betting_value
   - home_team (required)
   - away_team (required)

3. get_betting_recommendations
   - home_team (required)
   - away_team (required)

4. get_upcoming_value_bets
   - days_ahead (default: 7)
   - league_query (optional)

5. get_upcoming_predictions
   - days_ahead (default: 7)
   - league_query (optional)
   - nation (optional)
   - max_results (default: 15)

6. get_recent_form
   - team_name (required)
   - last_n_matches (default: 10)
   - competition_name (optional)
   - at_home (optional boolean)

7. get_upcoming_matches
   - days_ahead (default: 7)
   - league_query (optional)
   - nation (optional) If any hint of a nation is mentioned, use this parameter (change from english to england, italian to italy, etc)
   - max_results (default: 15)

When the user refers to "this match" or "that match", use your conversation memory to call the function with the right parameters.


Return ONLY a JSON object with this structure, no other text:
{
    "intent": "function_name",
    "parameters": {
        "param1": "value1",
        "param2": "value2"
    },
    "confidence": 0.9
}

If you are unsure about the intent, return exactly:
{
    "intent": "general_chat",
    "parameters": {},
    "confidence": 0.3
}"""
            },
            {
                "role": "user",
                "content": user_input
            }
        ]
        
        response = self.llm.call(prompt)
        
        try:
            content = response['choices'][0]['message']['content']
            # Remove any markdown formatting
            content = content.replace('```json', '').replace('```', '').strip()
            
            # Find the first occurrence of '{' and the last occurrence of '}'
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx + 1]
                result = json.loads(json_str)
                return result
            
            raise json.JSONDecodeError("No valid JSON found", content, 0)
            
        except (KeyError, json.JSONDecodeError) as e:
            print(f"Failed to parse LLM response: {str(e)}\nResponse: {response}")
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
        """Generate natural language response using Groq."""
        
        conversation_history = self._format_conversation_history(conversation_memory)
        
        # Custom JSON encoder to handle datetime objects
        def datetime_handler(obj):
            if isinstance(obj, (datetime, timedelta)):
                return obj.isoformat()
            return str(obj)
        
        prompt = [
            {
                "role": "system",
                "content": """You are a football betting assistant that generates natural language responses.
                Given the conversation history, query details, and function results, generate a helpful yet very concise response.
                
                Response Guidelines:
                1. Use markdown formatting:
                   - Bold for important info (**text**)
                   - Lists for multiple items
                   - Tables for structured data
                
                2. Use appropriate emojis:
                   - ⚽ for matches
                   - 📈 for predictions
                   - 💰 for betting
                   - ✅ for wins
                   - ❌ for losses
                   - 🤝 for draws
                   - 🏠 for home games
                   - ✈️ for away games
                
                3. Structure responses clearly:
                   - Start with a summary
                   - Group related information
                   - Be confident in your responses
                
                4. Maintain conversation context
                5. Be very concise
                """
            },
            {
                "role": "user",
                "content": f"""Recent conversation history:
                {conversation_history}
                
                Current User Query: {user_input}
                
                Parsed Intent: {parsed_query['intent']}
                Parameters: {json.dumps(parsed_query['parameters'], default=datetime_handler, indent=2)}
                
                Function Result: {json.dumps(function_result, default=datetime_handler, indent=2)}
                
                Generate a natural language response:"""
            }
        ]
        
        response = self.llm.call(prompt)
        
        try:
            return response['choices'][0]['message']['content']
        except KeyError:
            return "I apologize, but I encountered an issue generating a response. Please try again."

    def manual_response(self, user_input, parsed_query, function_result, conversation_memory) -> str:
        """Generate a response for predictions and matches."""
        if parsed_query['intent'] == 'get_match_prediction':
            data = function_result.get('data', {})
            if not data:
                return "❌ No prediction data available."
            
            match = data['match']
            prediction = data['prediction']
            
            # Convert probabilities to percentages and round
            home_prob = round(prediction['prob_home_win'] * 100, 1)
            draw_prob = round(prediction['prob_draw'] * 100, 1)
            away_prob = round(prediction['prob_away_win'] * 100, 1)
            confidence = round(prediction['confidence'] * 100, 1)
            
            # Get prediction emoji
            pred_emoji = "✅" if prediction['predicted_result'] == "Home Win" else "🤝" if prediction['predicted_result'] == "Draw" else "✈️"
            
            # Format response
            response = [
                f"⚽ **{match['home_team']}** 🏠 vs **{match['away_team']}** ✈️",
                f"📅 {match['start_time']}",
                f"🏆 {match['competition']}",
                "",
                "📈 **Prediction Probabilities:**",
                f"- Home Win: **{home_prob}%**",
                f"- Draw: **{draw_prob}%**",
                f"- Away Win: **{away_prob}%**",
                "",
                f"{pred_emoji} **Predicted Outcome:** {prediction['predicted_result']} (Confidence: **{confidence}%**)"
            ]
            
            return "\n".join(response)
            
        elif parsed_query['intent'] == 'get_upcoming_predictions':
            data = function_result.get('data', {})
            if not data.get('predictions'):
                return "❌ No predictions available for the specified criteria."
            
            predictions = data['predictions']
            response_parts = []
            
            # Add header
            response_parts.append("🔮 Match Predictions:")
            
            # Group by date
            current_date = None
            for pred in predictions:
                match_date = pred['start_time'].split('T')[0]
                match_time = pred['start_time'].split('T')[1][:5]
                
                if match_date != current_date:
                    current_date = match_date
                    response_parts.append(f"\n📅 {match_date}")
                
                # Format prediction with probabilities
                home_prob = round(pred['prob_home_win'] * 100, 1)
                draw_prob = round(pred['prob_draw'] * 100, 1)
                away_prob = round(pred['prob_away_win'] * 100, 1)
                
                response_parts.append(
                    f"⏰ {match_time} - {pred['home_team']} vs {pred['away_team']} ({pred['competition']})\n"
                    f"   Prediction: {pred['predicted_result']} (Confidence: {round(pred['confidence'] * 100, 1)}%)\n"
                    f"   Home: {home_prob}% | Draw: {draw_prob}% | Away: {away_prob}%"
                )
            
            return "\n".join(response_parts)
            
        elif parsed_query['intent'] == 'get_upcoming_matches':
            data = function_result.get('data', {})
            if not data.get('matches'):
                return "❌ No upcoming matches found for the specified criteria."
            
            matches = data['matches']
            summary = data['summary']
            
            # Build response
            response_parts = []
            
            # Add header
            response_parts.append("📅 Upcoming Matches:")
            
            # Group by date and competition
            current_date = None
            current_competition = None
            
            for match in matches:
                match_date = match['start_time'].split('T')[0]
                match_time = match['start_time'].split('T')[1][:5]
                
                if match_date != current_date:
                    current_date = match_date
                    current_competition = None
                    response_parts.append(f"\n🗓️ {match_date}")
                
                if match['competition'] != current_competition:
                    current_competition = match['competition']
                    response_parts.append(f"\n🏆 {match['competition']} ({match['country']})")
                
                response_parts.append(
                    f"⏰ {match_time} - {match['home_team']} vs {match['away_team']}"
                )
            
            # Add summary footer
            response_parts.append(f"\n\nFound {summary['total_matches_found']} matches in total.")
            
            return "\n".join(response_parts)
            
        elif parsed_query['intent'] == 'get_betting_recommendations' or parsed_query['intent'] == 'get_betting_value':
            data = function_result.get('data', {})
            if not data.get('has_value_bets'):
                return "❌ No value bets found for this match."
            
            match_info = data['match_info']
            value_bets = data['value_bets']
            match_finder = data['match_finder_info']
            
            # Format response
            response = [
                f"⚽ **{match_info['home_team']}** 🏠 vs **{match_info['away_team']}** ✈️",
                f"📅 {match_finder['start_time']}",
                f"🏆 {match_finder['competition']}",
                "",
                "📈 **Model Predictions:**"
            ]
            
            # Add model predictions
            model_preds = data['model_predictions']
            response.extend([
                f"- Home Win: **{round(model_preds['prob_home_win'] * 100, 1)}%**",
                f"- Draw: **{round(model_preds['prob_draw'] * 100, 1)}%**",
                f"- Away Win: **{round(model_preds['prob_away_win'] * 100, 1)}%**",
                "",
                "💰 **Recommended Bets:**"
            ])
            
            # Sort value bets by value percentage
            sorted_bets = sorted(value_bets, key=lambda x: x['value_percentage'], reverse=True)
            
            # Add each value bet
            for bet in sorted_bets:
                value = round(bet['value_percentage'], 1)
                odds = bet['odds_value']
                stake = round(bet['recommended_bet_percentage'], 2)
                profit = round(bet['potential_profit_percentage'], 1)
                
                response.append(
                    f"- **{bet['outcome']}** ({bet['bookmaker_name']})\n"
                    f"  • Odds: **{odds}** (Value: **{value}%**)\n"
                    f"  • Stake: **{stake}%** → Potential Profit: **{profit}%**"
                )
            
            # Add summary
            total_stake = round(data['total_bet_percentage'], 2)
            total_profit = round(data['total_potential_profit_percentage'], 1)
            
            response.extend([
                "",
                f"📊 **Summary:**",
                f"- Total Stake: **{total_stake}%**",
                f"- Max Potential Profit: **{total_profit}%**"
            ])
            
            return "\n".join(response)
            
        elif parsed_query['intent'] == 'get_upcoming_value_bets':
            data = function_result.get('data', {})
            if not data.get('value_bets'):
                return "❌ No value bets found for the specified criteria."
            
            # Get summary stats
            analysis = data['analysis_summary']
            
            # Start with summary
            response = [
                "📊 **Value Bets Found:**",
                f"Found **{analysis['matches_with_value']}** matches with value from {analysis['matches_analyzed']} analyzed",
                "",
                "💰 **Top Value Bets:**"
            ]
            
            # Sort bets by start time
            sorted_bets = sorted(data['value_bets'], key=lambda x: x['start_time'])
            
            # Add each value bet
            for bet in sorted_bets:
                value = round(bet['value_percentage'], 1)
                odds = bet['odds_value']
                stake = round(bet['recommended_bet_percentage'], 2)
                model_prob = round(bet['model_probability'] * 100, 1)
                
                response.append(
                    f"\n⚽ **{bet['home_team']}** vs **{bet['away_team']}**\n"
                    f"🏆 {bet['competition']} • 📅 {bet['start_time']}\n"
                    f"- BET ON **{bet['outcome']}** @ {odds} ({bet['bookmaker_name']})\n"
                    f"- Model Probability: {model_prob}%\n"
                    f"- Stake {stake}% of bankroll"
                )
            
            return "\n".join(response)
        
        elif parsed_query['intent'] == 'general_chat':
            return "Let's chat about football :) Ask me about predictions, upcoming matches, best matches to bet on, and team recent form, and I will do my best to help you."
            
        else:
            return "general chat response here"