import pandas as pd
import sqlite3
from datetime import datetime
import unicodedata
import sys
import os

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
sys.path.append(project_root)

# Now we can import the TelegramBot
from sportradar.scripts.bot.send_message import TelegramBot


def analyze_predictions():
    # Initialize Telegram bot
    bot = TelegramBot()
    
    # Read predictions
    predictions_df = pd.read_csv('sportradar/AI/match_predictions.csv')
    
    # Connect to odds database
    conn = sqlite3.connect('odds.db')
    
    website_data = []
    
    for _, row in predictions_df.iterrows():
        odds = get_match_odds(conn, row['home_team'], row['away_team'], row['start_time'])
        
        if odds is None:
            print(f"No odds found for {row['home_team']} vs {row['away_team']}")
            continue
            
        home_odds, draw_odds, away_odds = odds
        
        # Calculate all probabilities and values
        home_bookie_prob = calculate_bookie_probability(home_odds)
        draw_bookie_prob = calculate_bookie_probability(draw_odds)
        away_bookie_prob = calculate_bookie_probability(away_odds)
        
        home_value = calculate_value(row['home_win_prob'], home_odds)
        draw_value = calculate_value(row['draw_prob'], draw_odds)
        away_value = calculate_value(row['away_win_prob'], away_odds)
        
        home_kelly = calculate_kelly(home_odds, row['home_win_prob'])
        draw_kelly = calculate_kelly(draw_odds, row['draw_prob'])
        away_kelly = calculate_kelly(away_odds, row['away_win_prob'])
        
        match_data = {
            'home_team': row['home_team'],
            'away_team': row['away_team'],
            'start_time': row['start_time'],
            'predicted_outcome': row['predicted_outcome'],
            'model_type': row['model_type'],
            'home_win_prob': row['home_win_prob'],
            'draw_prob': row['draw_prob'],
            'away_win_prob': row['away_win_prob'],
            'home_odds': home_odds,
            'draw_odds': draw_odds,
            'away_odds': away_odds,
            'home_bookie_prob': home_bookie_prob,
            'draw_bookie_prob': draw_bookie_prob,
            'away_bookie_prob': away_bookie_prob,
            'home_value': home_value * 100,
            'draw_value': draw_value * 100,
            'away_value': away_value * 100,
            'home_kelly': home_kelly * 100,
            'draw_kelly': draw_kelly * 100,
            'away_kelly': away_kelly * 100
        }
        
        website_data.append(match_data)
    
    
    # Save to CSV for website
    website_df = pd.DataFrame(website_data)
    website_df.to_csv('website/data/prediction_analysis.csv', index=False)
    
    results = []
    
    for _, row in predictions_df.iterrows():
        odds = get_match_odds(conn, row['home_team'], row['away_team'], row['start_time'])
        
        if odds is None:
            print(f"No odds found for {row['home_team']} vs {row['away_team']}")
            continue
            
        home_odds, draw_odds, away_odds = odds
        
        # Calculate values for all outcomes
        outcomes = [
            {
                'type': 'Home Win',
                'predicted_prob': row['home_win_prob'],
                'bookie_odds': home_odds,
                'bookie_prob': calculate_bookie_probability(home_odds),
                'is_predicted': row['predicted_outcome'] == 'Home Win'
            },
            {
                'type': 'Draw',
                'predicted_prob': row['draw_prob'],
                'bookie_odds': draw_odds,
                'bookie_prob': calculate_bookie_probability(draw_odds),
                'is_predicted': row['predicted_outcome'] == 'Draw'
            },
            {
                'type': 'Away Win',
                'predicted_prob': row['away_win_prob'],
                'bookie_odds': away_odds,
                'bookie_prob': calculate_bookie_probability(away_odds),
                'is_predicted': row['predicted_outcome'] == 'Away Win'
            }
        ]
        
        for outcome in outcomes:
            value = calculate_value(outcome['predicted_prob'], outcome['bookie_odds'])
            kelly = calculate_kelly(outcome['bookie_odds'], outcome['predicted_prob'])
            
            # Include all bets, even negative value ones
            results.append({
                'match_time': row['start_time'],
                'home_team': row['home_team'],
                'away_team': row['away_team'],
                'bet_type': outcome['type'],
                'is_predicted': outcome['is_predicted'],
                'our_probability': outcome['predicted_prob'],
                'bookie_probability': outcome['bookie_prob'],
                'bookie_odds': outcome['bookie_odds'],
                'value': value,
                'kelly_stake': kelly
            })
    
    # Convert results to DataFrame and sort by value
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('value', ascending=False)
    
    # Prepare message for Telegram
    message = "<b>🎯 Value Betting Analysis</b>\n\n"
    
    # Group matches to show all probabilities together
    matches = {}
    for _, bet in results_df.iterrows():
        match_key = f"{bet['home_team']} vs {bet['away_team']}_{bet['match_time']}"
        if match_key not in matches:
            matches[match_key] = {
                'home_team': bet['home_team'],
                'away_team': bet['away_team'],
                'match_time': bet['match_time'],
                'outcomes': []
            }
        matches[match_key]['outcomes'].append(bet)
    
    # First show probability breakdown for all matches
    message += "<b>📊 PROBABILITY BREAKDOWN</b>\n\n"
    for match_key, match_data in matches.items():
        message += f"⚽ {match_data['home_team']} vs {match_data['away_team']}\n"
        message += f"🕒 {match_data['match_time']}\n"
        message += "<b>Our Model:</b>\n"
        message += "├ " + "\n├ ".join([
            f"{outcome['bet_type']}: {outcome['our_probability']:.1%}"
            for outcome in match_data['outcomes']
        ]) + "\n"
        message += "<b>Bookmaker:</b>\n"
        message += "├ " + "\n├ ".join([
            f"{outcome['bet_type']}: {outcome['bookie_probability']:.1%} ({outcome['bookie_odds']:.2f})"
            for outcome in match_data['outcomes']
        ]) + "\n"
        message += f"{'—' * 20}\n\n"
    
    # Then show positive value bets
    message += "<b>💰 VALUE BETS</b>\n\n"
    positive_value_bets = False
    for _, bet in results_df[results_df['value'] > 0].iterrows():
        positive_value_bets = True
        value_percentage = bet['value'] * 100
        kelly_percentage = bet['kelly_stake'] * 100
        
        # Determine bet category
        if bet['is_predicted'] and value_percentage > 5:
            category = "🟢 SAFE BET"
        elif value_percentage > 10:
            category = "🟡 RISKY BET (High Value)"
        else:
            category = "🟡 RISKY BET"
        
        message += f"<b>{category}</b>\n"
        message += f"⚽ {bet['home_team']} vs {bet['away_team']}\n"
        message += f"🕒 {bet['match_time']}\n"
        message += f"🎲 Bet: {bet['bet_type']}\n"
        message += f"📊 Our Probability: {bet['our_probability']:.1%}\n"
        message += f"📉 Bookie Probability: {bet['bookie_probability']:.1%}\n"
        message += f"📈 Bookie Odds: {bet['bookie_odds']:.2f}\n"
        message += f"💰 Value: {value_percentage:.1f}%\n"
        message += f"💵 Kelly Stake: {kelly_percentage:.1f}%\n"
        
        if not bet['is_predicted']:
            message += "⚠️ <i>Note: Not our primary predicted outcome</i>\n"
        
        message += f"{'—' * 20}\n\n"
    
    # Then show particularly bad value bets
    message += "<b>🚫 BETS TO AVOID</b>\n\n"
    bad_bets_found = False
    for _, bet in results_df[results_df['value'] < -0.15].iterrows():
        bad_bets_found = True
        value_percentage = bet['value'] * 100
        
        message += f"<b>🔴 NO BET</b>\n"
        message += f"⚽ {bet['home_team']} vs {bet['away_team']}\n"
        message += f"🎲 Bet: {bet['bet_type']}\n"
        message += f"📊 Our Probability: {bet['our_probability']:.1%}\n"
        message += f"📉 Bookie Probability: {bet['bookie_probability']:.1%}\n"
        message += f"📈 Bookie Odds: {bet['bookie_odds']:.2f}\n"
        message += f"⛔️ Negative Value: {value_percentage:.1f}%\n"
        message += f"{'—' * 20}\n\n"
    
    if not positive_value_bets and not bad_bets_found:
        message += "❌ No significant value bets (positive or negative) found for upcoming matches."
    
    # Send message through Telegram
    # bot.send_message(message)
    
    # Also print to console for debugging
    print(message)

    conn.close()


#********************************************************************************
#HELPER FUNCTIONS
#********************************************************************************

def normalize_text(text):
    """Remove accents and normalize text"""
    # Normalize unicode characters
    normalized = unicodedata.normalize('NFKD', text)
    # Remove diacritics
    normalized = ''.join(c for c in normalized if not unicodedata.combining(c))
    return normalized.lower()

def get_match_odds(conn, home_team, away_team, start_time):
    """Get odds for a specific match from the database with flexible name matching."""
    cursor = conn.cursor()
    
    # Normalize the timestamp by removing +00:00 and replacing with Z
    normalized_time = start_time.replace('+00:00', 'Z')
    
    # Print all potential matches from the database for debugging
    cursor.execute('''
    SELECT home_team, away_team, start_time 
    FROM match_odds 
    WHERE datetime(start_time) BETWEEN datetime(?) AND datetime(?, '+1 hour')
    ''', (normalized_time, normalized_time))
    
    potential_matches = cursor.fetchall()
    print(f"\nLooking for: {home_team} vs {away_team} at {normalized_time}")
    print("Available matches in database for this time (±1 hour):")
    for match in potential_matches:
        print(f"- {match[0]} vs {match[1]} at {match[2]}")
    
    # Special cases where team names need to be preserved
    special_cases = {
        'Inter': 'Internazionale',
        'AC Milan': 'Milan',
        'Real Madrid': 'Madrid',
        'Atletico Madrid': 'Atletico',
        'Real Betis': 'Betis',
        'Real Sociedad': 'Sociedad',
        'Manchester United': 'United',
        'Manchester City': 'City',
        'Inter Miami': 'Miami'
    }
    
    # Common suffixes/prefixes to ignore in team names
    ignore_terms = [
        'FC', 'CFC', 'AFC', 
        'United', 'Utd',
        'City', 
        'Real', 
        'Sporting',
        'Athletic',
        'Atletico',
        'RC',  # Racing Club
        'AC',  # Associazione Calcio
        'AS',  # Associazione Sportiva
        'SSC', # Società Sportiva Calcio
        'CF',  # Club de Fútbol
        'CD',  # Club Deportivo
        'RCD', # Real Club Deportivo
        'SC',  # Sport Club
        'BSC', # Ballspiel-Verein
        'TSG', # Turn- und Sportgemeinschaft
        'VfL', # Verein für Leibesübungen
        'VfB', # Verein für Bewegungsspiele
        'Deportivo'  # Added Deportivo
    ]
    
    # Check if team is a special case first
    def process_team_name(team_name):
        normalized_name = normalize_text(team_name)
        for special_team, replacement in special_cases.items():
            if normalize_text(special_team) in normalized_name:
                return [replacement]
        return [normalize_text(part) for part in team_name.split() if part not in ignore_terms]
    
    home_parts = process_team_name(home_team)
    away_parts = process_team_name(away_team)
    
    # Create SQL conditions for each part of the team names, using normalized text
    home_conditions = ' OR '.join([
        f"lower(replace(replace(replace(home_team, 'é', 'e'), 'á', 'a'), 'í', 'i')) LIKE '%{part}%'" 
        for part in home_parts
    ])
    away_conditions = ' OR '.join([
        f"lower(replace(replace(replace(away_team, 'é', 'e'), 'á', 'a'), 'í', 'i')) LIKE '%{part}%'" 
        for part in away_parts
    ])
    
    query = f'''
    SELECT home_win_odds, draw_odds, away_win_odds, home_team, away_team
    FROM match_odds 
    WHERE ({home_conditions})
    AND ({away_conditions})
    AND start_time = ?
    '''
    
    cursor.execute(query, (normalized_time,))
    result = cursor.fetchone()
    
    if result:
        print(f"Matched '{home_team}' to '{result[3]}' and '{away_team}' to '{result[4]}'")
        return result[:3]  # Return just the odds
    else:
        print(f"No match found for {home_team} vs {away_team}")
        return None

def calculate_value(predicted_prob, bookie_odds):
    """Calculate value using the value betting formula."""
    return (predicted_prob * bookie_odds) - 1

def calculate_kelly(bookie_odds, predicted_prob):
    """Calculate Kelly stake using the Kelly Criterion formula."""
    b = bookie_odds - 1  # Convert odds to b value
    p = predicted_prob
    q = 1 - p
    
    kelly = (b * p - q) / b
    
    # Often people use a fractional Kelly for safety
    fractional_kelly = kelly * 0.5  # Using half Kelly
    
    return max(0, fractional_kelly)  # Don't return negative values

def calculate_bookie_probability(bookie_odds):
    """Calculate bookie probability from bookie odds."""
    return 1 / (bookie_odds + 1)

if __name__ == "__main__":
    analyze_predictions()