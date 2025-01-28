from datetime import datetime, timedelta
import os
import sys
from typing import Tuple, Optional

import sqlite3
import pandas as pd
import numpy as np

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
sys.path.append(project_root)

from sportradar.scripts.constants.constants import DERBIES

def initialize_database(conn):
    """Create necessary tables if they don't exist and clean existing data"""
    cursor = conn.cursor()
    
    # Drop existing tables to ensure we have the correct schema
    cursor.execute("DROP TABLE IF EXISTS team_running_stats")
    cursor.execute("DROP TABLE IF EXISTS season_points")
    cursor.execute("DROP TABLE IF EXISTS elo_rating")
    
    # Create team_running_stats table with added team ID fields
    cursor.execute('''CREATE TABLE team_running_stats (
        team_name TEXT,
        team_id TEXT,
        start_time TEXT,
        season_id TEXT,
        competition_id TEXT,
        match_id TEXT,
        match_status TEXT DEFAULT 'ended',
        qualifier TEXT,  -- Added qualifier field (home/away)
        
        -- Opponent info
        opponent_team_name TEXT,
        opponent_team_id TEXT,
        
        -- Stats for the game
        goals_scored INTEGER,
        goals_conceded INTEGER,
        match_outcome TEXT,
        clean_sheet BOOLEAN,
        
        -- Advanced stats totals
        passes_successful INTEGER,
        passes_total INTEGER,
        shots_on_target INTEGER,
        shots_total INTEGER,
        chances_created INTEGER,
        tackles_successful INTEGER,
        tackles_total INTEGER,
                   
        --Stats check flags
        has_basic_stats BOOLEAN DEFAULT 0,
        has_advanced_stats BOOLEAN DEFAULT 0,
        
        PRIMARY KEY (team_name, start_time)
    )''')

    # Create elo_rating table
    cursor.execute('''CREATE TABLE elo_rating (
        team_id TEXT,
        team_name TEXT,
        elo_rating INTEGER DEFAULT 1500,
        PRIMARY KEY (team_id)
    )''')
    
    # Create season_points table
    cursor.execute('''CREATE TABLE season_points (
        team_name TEXT,
        season_id TEXT,
        competition_id TEXT,
        points INTEGER DEFAULT 0,
        matches_played INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        draws INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        PRIMARY KEY (team_name, season_id, competition_id)
    )''')
    
    conn.commit()
    print("Tables dropped and recreated with new schema")

#**************************************
#MAIN FUNCTION
#**************************************
def calculate_form_stats(conn, match):
    """Calculate the form of each team based on their previous 5 match stats."""

    # Get team names 
    home_team = match.get('home_team')
    print(f"Home team: {home_team}")
    away_team = match.get('away_team')
    print(f"Away team: {away_team}")
    start_time = match.get('start_time')
    print(f"Start time: {start_time}")
    if not all([home_team, away_team, start_time]):
        raise ValueError(f"Missing required fields for form calculation. Match data: {match}")

    # Get previous matches for both teams
    home_previous_5_matches = get_previous_matches(conn, home_team, start_time)
    print(f"Home previous 5 matches: {home_previous_5_matches}")
    away_previous_5_matches = get_previous_matches(conn, away_team, start_time)
    print(f"Away previous 5 matches: {away_previous_5_matches}")

    # Calculate the teams' fatigue
    home_fatigue = calculate_team_fatigue(home_previous_5_matches, start_time)
    away_fatigue = calculate_team_fatigue(away_previous_5_matches, start_time)

    # Define and initialise the stats counter for each team, we will add each matches stats to these counters
    # and then divide by the number of matches to get the average, hence why we have a sum and a divisor
    # Divisor increments by 1 for each match processed
    # If a stat is not present in a match we wont add anything to the sum and we won't increment the divisor
    team_stats = {
        'goals_scored': {'sum': 0, 'divisor': 0},
        'goals_conceded': {'sum': 0, 'divisor': 0},
        'wins': {'sum': 0, 'divisor': 0},
        'draws': {'sum': 0, 'divisor': 0},
        'clean_sheets': {'sum': 0, 'divisor': 0},
        'passes_successful': {'sum': 0, 'divisor': 0},
        'passes_total': {'sum': 0, 'divisor': 0},
        'shots_on_target': {'sum': 0, 'divisor': 0},
        'shots_total': {'sum': 0, 'divisor': 0},
        'tackles_successful': {'sum': 0, 'divisor': 0},
        'tackles_total': {'sum': 0, 'divisor': 0},
        'chances_created': {'sum': 0, 'divisor': 0},
    }

    # Initialize stats for both teams
    home_stats = {stat: dict(values) for stat, values in team_stats.items()}
    away_stats = {stat: dict(values) for stat, values in team_stats.items()}

    # Process home team stats
    for prev_match in home_previous_5_matches:
        home_team_elo = get_elo_rating(conn, prev_match.get('team_id'))
        opponent_team_elo = get_elo_rating(conn, prev_match.get('opponent_team_id'))
        qualifier = prev_match.get('qualifier')
        
        # Add home advantage to ELO calculation
        home_advantage = 40
        adjusted_team_elo = home_team_elo + (home_advantage if qualifier == 'home' else -home_advantage)
        
        # Calculate expected performance (P) based on ELO ranking difference
        # If a team is ranked higher than the opponent, they are expected to perform better
        # Example: If a team beats a team ranked above them this should boost their stats more than if they beat a team ranked below them
        elo_diff = adjusted_team_elo - opponent_team_elo
        expected_performance = 1 / (1 + 10 ** (-elo_diff / 400))
        
        # Calculate goal margin multiplier (G)
        # This is a multiplier based on the goal difference, it takes into consideration the ELO ranking of the team and the opponent
        goal_diff = abs(prev_match.get('goals_scored', 0) - prev_match.get('goals_conceded', 0))
        goal_multiplier = np.log(goal_diff + 1) * (2.2 / ((adjusted_team_elo - opponent_team_elo) * 0.001 + 2.2))
        
        # Performance multiplier based on whether team is favorite or underdog
        # If the team is ranked higher than the opponent, they are expected to perform better
        performance_multiplier = 1/expected_performance if elo_diff < 0 else expected_performance
        
        #For each stat, apply the appropriate weighting based on the stat type
        for stat in home_stats:
            # If the stat we are dealing with is wins we need to apply a weighting based not only on the match outcome but also the ELO ranking difference
            # This ensures that a win over a higher ranked team is worth more than a win over a lower ranked team
            if stat == 'wins':
                base_value = 1 if prev_match.get('match_outcome') == 'win' else 0
                value = base_value * performance_multiplier + (goal_multiplier if base_value == 1 else 0)
            
            # Similarly, we do the same for draws
            elif stat == 'draws':
                base_value = 1 if prev_match.get('match_outcome') == 'draw' else 0
                if base_value == 1:
                    # Softer weighting for draws (square root of performance multiplier)
                    draw_weight = np.sqrt(performance_multiplier)
                    # Add small bonus for drawing against much stronger teams
                    if elo_diff < -100:  # If opponent is significantly stronger
                        draw_weight *= 1.2
                    value = base_value * draw_weight
                else:
                    value = 0

            # And the same for clean sheets
            elif stat == 'clean_sheets':
                base_value = 1 if prev_match.get('goals_conceded', 0) == 0 else 0
                value = base_value * performance_multiplier
            
            # For all other stats, we can just apply the performance multiplier
            elif stat in ['goals_scored', 'goals_conceded', 'chances_created', 
                         'passes_successful', 'tackles_successful']:
                base_value = prev_match.get(stat)
                value = base_value * performance_multiplier if base_value is not None else None
            
            # For all other stats, we can just apply the performance multiplier
            elif stat in ['passes_total', 'shots_on_target', 'shots_total', 'tackles_total']:
                value = prev_match.get(stat)
                
            else:
                base_value = prev_match.get(stat)
                value = base_value * performance_multiplier if base_value is not None else None
            
            # Add the value for that match to the overall stats for that team
            # We increment the divisor by 1 to keep track of how many matches we have processed
            # This allows us to calculate the average value for each stat
            if value is not None:
                home_stats[stat]['sum'] += value
                home_stats[stat]['divisor'] += 1
            
    # Exactly the same for the away team
    for prev_match in away_previous_5_matches:
        away_team_elo = get_elo_rating(conn, prev_match.get('team_id'))
        opponent_team_elo = get_elo_rating(conn, prev_match.get('opponent_team_id'))
        qualifier = prev_match.get('qualifier')
        
        home_advantage = 40
        adjusted_team_elo = away_team_elo + (home_advantage if qualifier == 'home' else -home_advantage)
        
        elo_diff = adjusted_team_elo - opponent_team_elo
        expected_performance = 1 / (1 + 10 ** (-elo_diff / 400))
        
        # Calculate goal margin multiplier (G)
        goal_diff = abs(prev_match.get('goals_scored', 0) - prev_match.get('goals_conceded', 0))
        goal_multiplier = np.log(goal_diff + 1) * (2.2 / ((adjusted_team_elo - opponent_team_elo) * 0.001 + 2.2))
        
        # Performance multiplier based on whether team is favorite or underdog
        performance_multiplier = 1/expected_performance if elo_diff < 0 else expected_performance
        
        for stat in away_stats:
            # Apply appropriate weighting based on stat type
            if stat == 'wins':
                base_value = 1 if prev_match.get('match_outcome') == 'win' else 0
                value = base_value * performance_multiplier + (goal_multiplier if base_value == 1 else 0)

            elif stat == 'draws':
                base_value = 1 if prev_match.get('match_outcome') == 'draw' else 0
                if base_value == 1:
                    draw_weight = np.sqrt(performance_multiplier)
                    if elo_diff < -100:
                        draw_weight *= 1.2
                    value = base_value * draw_weight
                else:
                    value = 0
                
            elif stat == 'clean_sheets':
                base_value = 1 if prev_match.get('goals_conceded', 0) == 0 else 0
                value = base_value * performance_multiplier
                
            elif stat in ['goals_scored', 'goals_conceded', 'chances_created', 
                         'passes_successful', 'tackles_successful']:
                base_value = prev_match.get(stat)
                value = base_value * performance_multiplier if base_value is not None else None
                
            elif stat in ['passes_total', 'shots_on_target', 'shots_total', 'tackles_total']:
                value = prev_match.get(stat)
                
            else:
                base_value = prev_match.get(stat)
                value = base_value * performance_multiplier if base_value is not None else None
            
            if value is not None:
                away_stats[stat]['sum'] += value
                away_stats[stat]['divisor'] += 1
            
    # Set has_advanced_stats flag
    home_stats['has_advanced_stats'] = 1 if has_enough_advanced_stats(home_stats) else 0
    away_stats['has_advanced_stats'] = 1 if has_enough_advanced_stats(away_stats) else 0

    # Calculate momentum
    home_momentum = calculate_momentum(conn, home_previous_5_matches, home_team)
    away_momentum = calculate_momentum(conn, away_previous_5_matches, away_team)

    # Add momentum to stats
    home_stats['momentum'] = home_momentum
    away_stats['momentum'] = away_momentum

    home_stats['fatigue'] = home_fatigue
    away_stats['fatigue'] = away_fatigue
    
    # Calculate final metrics
    home_metrics = calculate_metrics(home_stats)
    away_metrics = calculate_metrics(away_stats)

    return home_metrics, away_metrics
    
#************************************************************************************
#HELPER FUNCTIONS
#************************************************************************************

def get_previous_matches(conn, team_name, before_match_date):
    """Get the previous 5 matches for a team before a certain date"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            team_name,
            team_id,
            start_time,
            season_id,
            competition_id,
            match_id,
            match_status,
            qualifier,
            opponent_team_name,
            opponent_team_id,
            goals_scored,
            goals_conceded,
            match_outcome,
            clean_sheet,
            passes_successful,
            passes_total,
            shots_on_target,
            shots_total,
            chances_created,
            tackles_successful,
            tackles_total,
            has_basic_stats,
            has_advanced_stats
        FROM team_running_stats 
        WHERE team_name = ?
        AND start_time < ?
        AND has_basic_stats = 1
        AND match_status = 'ended'
        ORDER BY start_time DESC
        LIMIT 5
    """, (team_name, before_match_date))
    
    # Convert tuple results to dictionaries with named fields
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def calculate_team_fatigue(recent_matches, reference_date):
    """
    Calculate team fatigue based on:
    1. Days since last match
    2. Number of matches in last 10 days
    
    Args:
        recent_matches: List of match dictionaries with 'start_time'
        reference_date: The date to calculate fatigue relative to (usually upcoming match date)
        
    Returns:
        float: Fatigue score between 0-1 (1 being most fatigued)
    """
    if not recent_matches:
        return 0.0
        
    # Convert reference_date to datetime if it's a string
    if isinstance(reference_date, str):
        reference_date = datetime.fromisoformat(reference_date.replace('Z', '+00:00'))
    
    # Convert all dates to datetime objects
    match_dates = [datetime.fromisoformat(match['start_time'].replace('Z', '+00:00')) 
                  for match in recent_matches]
    match_dates.sort(reverse=True)  # Most recent first
    
    # Calculate days since last match
    if match_dates:
        days_since_last_match = (reference_date - match_dates[0]).total_seconds() / (24 * 3600)
    else:
        return 0.0
    
    # Calculate matches in last 10 days
    ten_days_ago = reference_date - timedelta(days=10)
    matches_in_ten_days = sum(1 for date in match_dates if date >= ten_days_ago)
    
    # Calculate fatigue components
    # Days since last match: 0 days = 1.0, 7+ days = 0.0
    time_fatigue = max(0, 1 - (days_since_last_match / 7))
    
    # Matches in 10 days: 0 matches = 0.0, 5+ matches = 1.0
    match_fatigue = min(1, matches_in_ten_days / 5)
    
    # Combine factors (equal weighting)
    fatigue_score = (time_fatigue + match_fatigue) / 2
    
    return round(fatigue_score, 3)

def calculate_momentum(conn,matches, team_name, weights=[0.35, 0.25, 0.20, 0.12, 0.08]):
    """
    Calculate team momentum based on their last 5 matches.
    Positive momentum means improving form, negative means declining form.
    Uses raw match stats without averaging and weights based on opponent strength.
    """
    if len(matches) < 2:
        print(f"Not enough matches for {team_name}: {len(matches)}")
        print("Returning 0.0")
        return 0.0

    match_scores = []
    
    print(f"\nCalculating momentum for {team_name}")
    print(f"Number of matches: {len(matches)}")
    
    # Calculate match scores (most recent first)
    for match in matches:
        print(f"\nProcessing match from {match.get('start_time')}")
        
        # Calculate ELO-based performance multiplier
        team_elo = get_elo_rating(conn, match.get('team_id'))
        opponent_elo = get_elo_rating(conn, match.get('opponent_team_id'))
        qualifier = match.get('qualifier')
        
        # Add home advantage to ELO calculation
        home_advantage = 100
        adjusted_team_elo = team_elo + (home_advantage if qualifier == 'home' else -home_advantage)
        
        # Calculate expected performance (P)
        elo_diff = adjusted_team_elo - opponent_elo
        expected_performance = 1 / (1 + 10 ** (-elo_diff / 400))
        
        # Performance multiplier based on whether team is favorite or underdog
        performance_multiplier = 1/expected_performance if elo_diff < 0 else expected_performance
        
        # Calculate basic indicators first
        basic_indicators = {
            'goals_ratio': (match.get('goals_scored', 0) / match.get('goals_conceded', 1)) 
                          if match.get('goals_conceded', 0) > 0 
                          else match.get('goals_scored', 0),
            'win': 1 if match.get('match_outcome') == 'win' else 0,
            'clean_sheet': 1 if match.get('goals_conceded', 1) == 0 else 0
        }
        
        # Weight the basic indicators
        weighted_indicators = {
            'goals_ratio': basic_indicators['goals_ratio'] * performance_multiplier,
            'win': basic_indicators['win'] * performance_multiplier,
            'clean_sheet': basic_indicators['clean_sheet'] * performance_multiplier
        }
        
        # Initialize match_score with weighted basic indicators
        match_score = (
            0.50 * weighted_indicators['win'] +
            0.30 * weighted_indicators['goals_ratio'] +
            0.20 * weighted_indicators['clean_sheet']
        )
        
        # Calculate advanced indicators if the stats exist
        if all(match.get(stat) is not None for stat in ['shots_on_target', 'shots_total', 
                                                       'passes_successful', 'passes_total',
                                                       'tackles_successful', 'tackles_total']):
            advanced_indicators = {
                'shot_accuracy': safe_ratio(match, 'shots_on_target', 'shots_total'),
                'pass_accuracy': safe_ratio(match, 'passes_successful', 'passes_total'),
                'chance_creation': safe_ratio(match, 'shots_on_target', 'goals_scored', default=0.0),
                'tackle_success': safe_ratio(match, 'tackles_successful', 'tackles_total'),
            }
            
            # Weight only chance_creation as it's a direct performance metric
            advanced_indicators['chance_creation'] *= performance_multiplier
            
            # Update match_score with advanced indicators
            match_score = (
                0.35 * weighted_indicators['win'] +
                0.20 * weighted_indicators['goals_ratio'] +
                0.15 * weighted_indicators['clean_sheet'] +
                0.08 * advanced_indicators['shot_accuracy'] +
                0.08 * advanced_indicators['pass_accuracy'] +
                0.07 * advanced_indicators['chance_creation'] +
                0.07 * advanced_indicators['tackle_success']
            )
        
        print(f"Match score: {match_score}")
        print(f"Performance multiplier: {performance_multiplier}")
        match_scores.append(match_score)

    # Rest of the function remains the same
    print(f"\nAll match scores: {match_scores}")
    
    trends = []
    for i in range(1, len(match_scores)):
        trend = match_scores[i-1] - match_scores[i]
        trends.append(trend)
    
    print(f"Trends: {trends}")
    
    weighted_trend = sum(t * w for t, w in zip(trends, weights[1:]))
    print(f"Weighted trend: {weighted_trend}")
    
    momentum = max(-1, min(1, weighted_trend))
    print(f"Final momentum: {momentum}")

    return round(momentum, 3)

def get_elo_rating(conn, team_id):
    """Get the current Elo rating for a team"""
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT elo_rating 
            FROM elo_rating 
            WHERE team_id = ?
        """, (team_id,))
        
        result = cursor.fetchone()
        
        if result is None:
            raise ValueError(f"Team ID {team_id} not found in elo_rating table")
        
        return result[0]
        
    except Exception as e:
        print(f"Error getting Elo rating for team {team_id}: {str(e)}")
        raise  # Re-raise the exception to be handled by the caller

def safe_ratio(match, numerator, denominator, default=0.0):
    """
    Safely calculate ratio between two match statistics.
    
    Args:
        match: Dictionary containing match statistics
        numerator: Key for numerator statistic
        denominator: Key for denominator statistic
        default: Default value to return in case of division by zero
    
    Returns:
        float: Calculated ratio or default value
    """
    num = match.get(numerator, 0)
    den = match.get(denominator, 1)
    if den == 0:
        return default
    return num / max(1, den)

# Advanced stats check
def has_enough_advanced_stats(stats):
    advanced_stat_requirements = {
            'pass_effectiveness': ['passes_successful', 'passes_total'],
            'shot_accuracy': ['shots_on_target', 'shots_total'],
            'defensive_success': ['tackles_successful', 'tackles_total']
        }
        
    all_required_stats = set()
    for stats_pair in advanced_stat_requirements.values():
        all_required_stats.update(stats_pair)
    all_required_stats.update(['goals_scored', 'shots_on_target'])
        
    for stat in all_required_stats:
        if stats[stat]['divisor'] < 2:
            return False
        
    for metric, required_stats in advanced_stat_requirements.items():
        stat1, stat2 = required_stats
        if stats[stat1]['divisor'] != stats[stat2]['divisor']:
            return False
        
    return True

def calculate_metrics(stats):
    """Calculate the metrics/ averages for a team for their 
    last 5 matches based on their stats of the last 5 matches"""
    if stats['has_advanced_stats'] == 1:
        return {
            # Basic metrics
            'average_goals_scored': stats['goals_scored']['sum'] / max(stats['goals_scored']['divisor'], 1),
            'average_goals_conceded': stats['goals_conceded']['sum'] / max(stats['goals_conceded']['divisor'], 1),
            'average_win_rate': stats['wins']['sum'] / max(stats['wins']['divisor'], 1),
            'average_draw_rate': stats['draws']['sum'] / max(stats['draws']['divisor'], 1),
            'average_clean_sheets': stats['clean_sheets']['sum'] / max(stats['clean_sheets']['divisor'], 1),
            
            # Advanced metrics
            'pass_effectiveness': stats['passes_successful']['sum'] / max(stats['passes_total']['sum'], 1),
            'shot_accuracy': stats['shots_on_target']['sum'] / max(stats['shots_total']['sum'], 1),
            'conversion_rate': (stats['goals_scored']['sum'] / max(stats['goals_scored']['divisor'], 1)) / 
                             (stats['shots_on_target']['sum'] / max(stats['shots_on_target']['divisor'], 1)),
            'defensive_success': stats['tackles_successful']['sum'] / max(stats['tackles_total']['sum'], 1),
            'fatigue': stats.get('fatigue'),
            'momentum': stats.get('momentum'),
            'has_advanced_stats': 1
        }
    else:
        return {
            # Basic metrics only
            'average_goals_scored': stats['goals_scored']['sum'] / max(stats['goals_scored']['divisor'], 1),
            'average_goals_conceded': stats['goals_conceded']['sum'] / max(stats['goals_conceded']['divisor'], 1),
            'average_win_rate': stats['wins']['sum'] / max(stats['wins']['divisor'], 1),
            'average_draw_rate': stats['draws']['sum'] / max(stats['draws']['divisor'], 1),
            'average_clean_sheets': stats['clean_sheets']['sum'] / max(stats['clean_sheets']['divisor'], 1),
            'fatigue': stats.get('fatigue'),
            'momentum': stats.get('momentum'),
            'has_advanced_stats': 0
        }


# Function to check if basic stats are present
def has_basic_stats(stats):
    basic_fields = ['team_name', 'team_id', 'start_time', 'season_id', 'competition_id', 
                    'match_id', 'goals_scored', 'goals_conceded']
    return all(stats.get(field) is not None and not (isinstance(stats.get(field), float) and np.isnan(stats.get(field))) for field in basic_fields)

# Function to check if advanced stats are present
def has_advanced_stats(stats):
    advanced_fields = ['passes_successful', 'passes_total', 'shots_on_target',
                             'shots_total', 'chances_created', 'tackles_successful', 
                             'tackles_total']
    return all(stats.get(field) is not None and not (isinstance(stats.get(field), float) and np.isnan(stats.get(field))) for field in advanced_fields)

def insert_team_stats(cursor, conn, home_stats, away_stats):
    """
    Insert team statistics into the database for both home and away teams.
    
    Args:
        cursor: SQLite cursor object
        conn: SQLite connection object
        home_stats (dict): Statistics for the home team
        away_stats (dict): Statistics for the away team
    """
    insert_query = """
        INSERT INTO team_running_stats (
            team_name, team_id, start_time, season_id, competition_id, match_id,
            match_status, qualifier, opponent_team_name, opponent_team_id,
            goals_scored, goals_conceded, match_outcome, clean_sheet,
            passes_successful, passes_total, shots_on_target, shots_total,
            chances_created, tackles_successful, tackles_total,
            has_basic_stats, has_advanced_stats
        ) VALUES (
            :team_name, :team_id, :start_time, :season_id, :competition_id, :match_id,
            :match_status, :qualifier, :opponent_team_name, :opponent_team_id,
            :goals_scored, :goals_conceded, :match_outcome, :clean_sheet,
            :passes_successful, :passes_total, :shots_on_target, :shots_total,
            :chances_created, :tackles_successful, :tackles_total,
            :has_basic_stats, :has_advanced_stats
        )
    """
    
    try:
        cursor.execute(insert_query, home_stats)
        cursor.execute(insert_query, away_stats)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise Exception(f"Error inserting team stats: {str(e)}")
    
#TODO: Implement more features
def calculate_match_importance(conn, match):
    """Calculate the importance of a match based on various factors"""
    
    BASE_LEAGUE_IMPORTANCE = 5.0
    BASE_CUP_IMPORTANCE = 5.5
    DERBY_BONUS = 2.0
    TITLE_RACE_BONUS = 2.5
    RELEGATION_BATTLE_BONUS = 2.0
    POSITION_PROXIMITY_MAX_BONUS = 1.5
    POINTS_PROXIMITY_MAX_BONUS = 1.5

    CUP_IMPORTANCE = {
    'UEFA Champions League': 6.0,
    'UEFA Europa League': 5.5,
    'UEFA Conference League': 5.5,
    'FA Cup': 6.0,
    'EFL Cup': 5.5,
    'Coppa Italia': 5.5,
    'Coupe de France': 5.5,
    'Copa del Rey': 5.5,
}
    
    importance = 0.0
    
    # Get current league positions and points
    home_points, away_points = get_team_points(conn, match)
    positions = get_league_positions(conn, match)
    home_pos = positions['home']['position']
    away_pos = positions['away']['position']

    matches_played = max(positions['home']['matches_played'], 
                        positions['away']['matches_played'])
    
    is_cup_match = match['competition_type'] == 'cup'

    
    if is_cup_match:
        importance = BASE_CUP_IMPORTANCE
        
        cup_name = match['competition_name']
        if cup_name in CUP_IMPORTANCE:
            importance = CUP_IMPORTANCE[cup_name]
        
        cup_stage = match['round_display']
        # Try to extract a number from the cup stage first
        try:
            round_num = int(''.join(filter(str.isdigit, str(cup_stage))))
            round_weight = round_num * 0.5
        except ValueError:
            # If no number found, check for specific round names
            stage_lower = str(cup_stage).lower()
            if 'round_of_16' in stage_lower or 'last_16' in stage_lower:
                round_weight = 3.0
            elif 'quarterfinal' in stage_lower or 'quarter' in stage_lower:
                round_weight = 4.0
            elif 'semifinal' in stage_lower or 'semi' in stage_lower:
                round_weight = 5.0
            elif 'final' in stage_lower:
                round_weight = 6.0
            else:
                round_weight = 0.5  # Default weight for unrecognized rounds

        importance += round_weight
        
    else:  # League match
        importance = BASE_LEAGUE_IMPORTANCE
        
        # Check if it's a derby by looking up teams directly
        home_team = match['home_team']
        away_team = match['away_team']
        
        # Check both orderings of teams across all competitions
        is_derby = False
        for derby_list in DERBIES.values():
            for team1, team2 in derby_list:
                if (home_team == team1 and away_team == team2) or \
                   (home_team == team2 and away_team == team1):
                    is_derby = True
                    break
            if is_derby:
                break
        
        if is_derby:
            importance += DERBY_BONUS
        
        # Position proximity bonus (closer positions = more important)
        if home_pos and away_pos and (home_pos <= 6 or away_pos <= 6):
            position_bonus = max(0, POSITION_PROXIMITY_MAX_BONUS * (1 - (max(home_pos, away_pos) / 10)))
            position_bonus *= 1.25  # 25% bonus for matches between top teams
            importance += position_bonus
        
        # Points proximity bonus
        if home_points is not None and away_points is not None:
            points_diff = abs(home_points - away_points)
            points_bonus = max(0, POINTS_PROXIMITY_MAX_BONUS * (1 - (points_diff / 9)))
            importance += points_bonus
        # Check if it's late in the season (more than 70% complete)
        TOTAL_SEASON_MATCHES = 38
        is_late_season = matches_played > (TOTAL_SEASON_MATCHES * 0.7)
        if is_late_season:
            # Title race check (teams near top of table)
            if (home_pos and home_pos <= 3) or (away_pos and away_pos <= 3):
                importance += TITLE_RACE_BONUS
            # Relegation battle check (teams near bottom)
            #TODO: Make this dynamic
            TEAMS_IN_LEAGUE = 20
            relegation_zone = TEAMS_IN_LEAGUE - 3
            if (home_pos and home_pos >= relegation_zone) or (away_pos and away_pos >= relegation_zone):
                importance += RELEGATION_BATTLE_BONUS
        # Late season importance multipliers
        if matches_played > (TOTAL_SEASON_MATCHES * 0.9):  # Final stretch
            TITLE_RACE_BONUS *= 1.5
            RELEGATION_BATTLE_BONUS *= 1.5
        elif matches_played > (TOTAL_SEASON_MATCHES * 0.8):  # Very late
            TITLE_RACE_BONUS *= 1.25
            RELEGATION_BATTLE_BONUS *= 1.25
    
    return (round(importance, 2))

def get_team_points(conn, match):
    """Get current points for both teams in the match for their current season"""
    cursor = conn.cursor()
    
    try:
        # Query points for both teams in one go
        cursor.execute("""
            SELECT team_name, points, matches_played
            FROM season_points
            WHERE team_name IN (?, ?)
            AND season_id = ?
            AND competition_id = ?
        """, (
            match['home_team'],
            match['away_team'],
            match['season_id'],
            match['competition_id']
        ))
        
        results = cursor.fetchall()
        
        # Initialize default values
        home_points = 0
        away_points = 0
        
        # Process results
        for team, points, matches in results:
            if team == match['home_team']:
                home_points = points
            elif team == match['away_team']:
                away_points = points
                
        return home_points, away_points

    except Exception as e:
        print(f"Error getting team points: {str(e)}")
        return 0, 0  # Return default values if there's an error

def get_league_positions(conn, match):
    """Get current league positions for both teams in the match"""
    cursor = conn.cursor()
    
    # Query that ranks teams by points (and goal difference if we had it)
    cursor.execute("""
        WITH ranked_teams AS (
            SELECT 
                team_name,
                points,
                matches_played,
                wins,
                ROW_NUMBER() OVER (
                    ORDER BY 
                        points DESC,
                        wins DESC,
                        matches_played ASC
                ) as position
            FROM season_points
            WHERE season_id = ? 
            AND competition_id = ?
        )
        SELECT 
            team_name,
            position,
            points,
            matches_played
        FROM ranked_teams
        WHERE team_name IN (?, ?)
        ORDER BY position ASC
    """, (
        match['season_id'],
        match['competition_id'],
        match['home_team'],
        match['away_team']
    ))
    
    results = cursor.fetchall()
    positions = {}
    
    for team, pos, pts, matches in results:
        positions[team] = {
            'position': pos,
            'points': pts,
            'matches_played': matches
        }
    
    return {
        'home': positions.get(match['home_team'], {'position': None, 'points': 0, 'matches_played': 0}),
        'away': positions.get(match['away_team'], {'position': None, 'points': 0, 'matches_played': 0})
    }

def add_points_for_team(conn, match):
    """Update season points for both teams based on match outcome"""
    cursor = conn.cursor()
    
    try:
        # Determine points for each team
        if match['home_goals'] > match['away_goals']:
            home_points = 3
            away_points = 0
        elif match['home_goals'] < match['away_goals']:
            home_points = 0
            away_points = 3
        else:
            home_points = 1
            away_points = 1

        # Update home team points
        cursor.execute("""
            INSERT INTO season_points (
                team_name, season_id, competition_id, 
                points, matches_played, wins, draws, losses
            ) VALUES (
                ?, ?, ?,
                ?, 1,
                CASE WHEN ? = 3 THEN 1 ELSE 0 END,
                CASE WHEN ? = 1 THEN 1 ELSE 0 END,
                CASE WHEN ? = 0 THEN 1 ELSE 0 END
            )
            ON CONFLICT(team_name, season_id, competition_id) DO UPDATE SET
                points = points + ?,
                matches_played = matches_played + 1,
                wins = wins + CASE WHEN ? = 3 THEN 1 ELSE 0 END,
                draws = draws + CASE WHEN ? = 1 THEN 1 ELSE 0 END,
                losses = losses + CASE WHEN ? = 0 THEN 1 ELSE 0 END
        """, (
            match['home_team'], match['season_id'], match['competition_id'],
            home_points,  # Initial points
            home_points, home_points, home_points,  # For CASE statements in INSERT
            home_points,  # For points addition in UPDATE
            home_points, home_points, home_points   # For CASE statements in UPDATE
        ))

        # Update away team points
        cursor.execute("""
            INSERT INTO season_points (
                team_name, season_id, competition_id,
                points, matches_played, wins, draws, losses
            ) VALUES (
                ?, ?, ?,
                ?, 1,
                CASE WHEN ? = 3 THEN 1 ELSE 0 END,
                CASE WHEN ? = 1 THEN 1 ELSE 0 END,
                CASE WHEN ? = 0 THEN 1 ELSE 0 END
            )
            ON CONFLICT(team_name, season_id, competition_id) DO UPDATE SET
                points = points + ?,
                matches_played = matches_played + 1,
                wins = wins + CASE WHEN ? = 3 THEN 1 ELSE 0 END,
                draws = draws + CASE WHEN ? = 1 THEN 1 ELSE 0 END,
                losses = losses + CASE WHEN ? = 0 THEN 1 ELSE 0 END
        """, (
            match['away_team'], match['season_id'], match['competition_id'],
            away_points,  # Initial points
            away_points, away_points, away_points,  # For CASE statements in INSERT
            away_points,  # For points addition in UPDATE
            away_points, away_points, away_points   # For CASE statements in UPDATE
        ))

        conn.commit()

    except Exception as e:
        print(f"Error updating points: {str(e)}")
        conn.rollback()
        raise

def getH2h_stats(conn, team1_id, team2_id, current_match_time):
    """Calculate head-to-head statistics between two teams before a given match time."""
    
    # Input validation
    if not team1_id or not team2_id:
        raise ValueError("Both team IDs must be provided")
    
    if team1_id == team2_id:
        raise ValueError("Team IDs must be different")

    # Verify that the teams exist in the overall matches database
    team_check_query = "SELECT COUNT(*) FROM matches WHERE home_team_id = ? OR away_team_id = ?"
    for team_id in [team1_id, team2_id]:
        count = conn.execute(team_check_query, (team_id, team_id)).fetchone()[0]
        if count == 0:
            raise ValueError(f"Team ID {team_id} not found in database")

    # First try getting h2h matches from the main matches table
    matches_query = """
    SELECT
        home_team_id,
        away_team_id,
        home_score,
        away_score,
        start_time
    FROM matches 
    WHERE match_status = 'ended'
        AND start_time < ?
        AND ((home_team_id = ? AND away_team_id = ?)
        OR (home_team_id = ? AND away_team_id = ?))
    ORDER BY start_time DESC
    """
    
    # If there are matches save them in a list, if not then we will check the h2h_matches table (which is populated by API calls from sportradar)
    matches = list(conn.execute(matches_query, (current_match_time, team1_id, team2_id, team2_id, team1_id)))
    if not matches or len(matches) < 1:
        print(f"Insufficient matches in main database ({len(matches) if matches else 0}), checking h2h_matches...")
        
        # Try h2h_matches table
        h2h_query = """
        SELECT
            home_team_id,
            away_team_id,
            home_score,
            away_score,
            start_time
        FROM h2h_matches 
        WHERE match_status = 'ended'
            AND start_time < ?
            AND ((home_team_id = ? AND away_team_id = ?)
            OR (home_team_id = ? AND away_team_id = ?))
        ORDER BY start_time DESC
        """
        
        # If there are matches in h2h table save them in a list
        matches = list(conn.execute(h2h_query, (current_match_time, team1_id, team2_id, team2_id, team1_id)))
    
    # If there are no matches in either table then return None
    if not matches:
        print(f"No H2H matches found in matches or h2h_matches table for teams {team1_id} and {team2_id}")
        return None

    #TODO: Think about changing this to a minimum of 3 matches, we need to check if this is a good number
    if len(matches) < 1:
        print(f"Insufficient H2H history between teams {team1_id} and {team2_id}. Only {len(matches)} matches found.")
        return None
    
    stats = get_h2h_averages(matches, team1_id, team2_id)

    return stats

def get_h2h_averages(matches, team1_id, team2_id):
    """
    Process match statistics and calculate averages for two teams.
    
    Args:
        matches (list): List of tuples containing (home_id, away_id, home_score, away_score, match_time)
        team1_id (str): ID of first team
        team2_id (str): ID of second team
        
    Returns:
        dict: Dictionary containing processed statistics for both teams
    """
    try:
        # Initialize statistics dictionary
        stats = {
            team1_id: {"games": 0, "goals": 0, "clean_sheets": 0, "points": 0, "draws": 0},
            team2_id: {"games": 0, "goals": 0, "clean_sheets": 0, "points": 0, "draws": 0}
        }
        
        # Process each match
        for home_id, away_id, home_score, away_score, match_time in matches:
            # Skip matches with missing scores
            if home_score is None or away_score is None:
                continue
            
            # Process goals
            if home_id == team1_id:
                stats[team1_id]["goals"] += home_score
                stats[team2_id]["goals"] += away_score
            else:
                stats[team1_id]["goals"] += away_score 
                stats[team2_id]["goals"] += home_score

            # Process clean sheets
            if home_id == team1_id:
                if away_score == 0:
                    stats[team1_id]["clean_sheets"] += 1
                if home_score == 0:
                    stats[team2_id]["clean_sheets"] += 1
            else:
                if home_score == 0:
                    stats[team1_id]["clean_sheets"] += 1
                if away_score == 0:
                    stats[team2_id]["clean_sheets"] += 1

            # Process points and draws
            if home_score > away_score:
                stats[home_id]["points"] += 3
            elif home_score < away_score:
                stats[away_id]["points"] += 3
            else:
                stats[home_id]["points"] += 1
                stats[away_id]["points"] += 1
                stats[home_id]["draws"] += 1
                stats[away_id]["draws"] += 1

            # Increment games played
            stats[team1_id]["games"] += 1
            stats[team2_id]["games"] += 1

        # Calculate averages for both teams
        for team_id in stats:
            games = stats[team_id]["games"]
            if games > 0:
                stats[team_id]["avg_goals"] = round(stats[team_id]["goals"] / games, 2)
                stats[team_id]["avg_clean_sheets"] = round(stats[team_id]["clean_sheets"] / games, 2)
                stats[team_id]["avg_points"] = round(stats[team_id]["points"] / games, 2)
                stats[team_id]["avg_draw_rate"] = round(stats[team_id]["draws"] / games, 2)
            
            # Remove working statistics
            del stats[team_id]["goals"]
            del stats[team_id]["clean_sheets"]
            del stats[team_id]["points"]
            del stats[team_id]["draws"]
            
        return stats

    except Exception as e:
        print(f"Error processing match statistics: {str(e)}")
        return None
    
#********************************************************************************
# Functions not directly used in this file but used in other files
#********************************************************************************

#This function is used in create_training_data.py
def refined_categorize_formation(formation):
    """
    Categorize a football formation as very defensive, defensive, balanced, offensive, or very offensive,
    and encode them as numerical values. Handles formations with varying lengths (e.g., "4-4-2" or "4-1-4-1").
    """
    try:
        # Split formation into parts (e.g., "4-4-2" -> [4, 4, 2], "4-1-4-1" -> [4, 1, 4, 1])
        parts = list(map(int, formation.split('-')))
        num_parts = len(parts)

        # If the formation has less than 3 parts, it's invalid
        if num_parts < 3:
            return -1  # Unknown category

        # Define defenders, midfielders, and attackers based on formation length
        if num_parts == 3:
            # Standard format (e.g., "4-4-2")
            num_defenders, num_midfielders, num_attackers = parts
        elif num_parts == 4:
            # Extended format (e.g., "4-1-4-1")
            num_defenders = parts[0]
            num_midfielders = parts[1] + parts[2]  # Combine central and attacking midfielders
            num_attackers = parts[3]
        else:
            return -1  # Unsupported or unusual formation

        # Define rules for categorization and return numerical encoding
        if num_defenders >= 5:
            if num_midfielders >= 4:
                return 0  # Very Defensive
            else:
                return 1  # Defensive
        elif num_defenders == 4:
            if num_midfielders >= 5:
                return 1  # Defensive
            elif num_attackers >= 3:
                return 2  # Balanced
            else:
                return 2  # Balanced
        elif num_defenders <= 3:
            if num_attackers >= 4:
                return 4  # Very Offensive
            else:
                return 3  # Offensive
        else:
            return -1  # Unknown
    except Exception as e:
        print(f"Error processing formation '{formation}': {e}")
        return -1  # Unknown

def get_match_formations(match_id: str, db_file: str = 'football_data.db') -> Tuple[Optional[str], Optional[str]]:
    """This function uses the team_lineups database that we 
    have to get the formations of each team in a match"""

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    print(f"\nLooking for match_id: {match_id}")  # Debug print
    
    cursor.execute('''
        SELECT 
            home_formation,
            away_formation,
            home_team_name,  -- Added these for debugging
            away_team_name   -- Added these for debugging
        FROM team_lineups
        WHERE match_id = ?
    ''', (match_id,))
    
    result = cursor.fetchone()
    
    if result:
        print(f"Found match: {result}")
        return result[0], result[1]
    else:
        print(f"No match found for ID: {match_id}")
    
    conn.close()
    return None, None

def calculate_elo_rating(conn, match, match_importance):
    """Calculate the Elo rating for home and away team"""
    cursor = conn.cursor()
    
    # Get or create Elo ratings for both teams
    def get_or_create_elo(team_id, team_name):
        cursor.execute("""
            INSERT OR IGNORE INTO elo_rating (team_id, team_name, elo_rating)
            VALUES (?, ?, 1500)
        """, (team_id, team_name, ))
        cursor.execute("SELECT elo_rating FROM elo_rating WHERE team_id = ?", (team_id,))
        return cursor.fetchone()[0]
    
    # Get current Elo ratings
    home_elo = get_or_create_elo(match['home_team_id'], match['home_team'])
    away_elo = get_or_create_elo(match['away_team_id'], match['away_team'])
    
    # Calculate expected scores
    elo_diff = home_elo - away_elo + 100  # +100 for home advantage
    expected_home = 1 / (1 + 10 ** (-elo_diff / 400))
    expected_away = 1 - expected_home
    
    # Calculate actual scores based on goals
    if 'home_goals' in match and 'away_goals' in match:
        goal_diff = abs(match['home_goals'] - match['away_goals'])
        
        if match['home_goals'] > match['away_goals']:
            actual_home = 1
            actual_away = 0
            # Goal margin multiplier for winner (home)
            goal_multiplier = np.log(goal_diff + 1) * (2.2 / ((home_elo - away_elo) * 0.001 + 2.2))
        elif match['home_goals'] < match['away_goals']:
            actual_home = 0
            actual_away = 1
            # Goal margin multiplier for winner (away)
            goal_multiplier = np.log(goal_diff + 1) * (2.2 / ((away_elo - home_elo) * 0.001 + 2.2))
        else:
            actual_home = 0.5
            actual_away = 0.5
            goal_multiplier = 1.0
            
        # Calculate K-factor (importance multiplier)
        # Scale match_importance to reasonable K-factor range (20-40)
        base_k = 30  # Base K-factor
        k_factor = base_k * (match_importance / 10.0) * goal_multiplier
        
        # Calculate new Elo ratings
        home_elo_new = home_elo + k_factor * (actual_home - expected_home)
        away_elo_new = away_elo + k_factor * (actual_away - expected_away)
        
        # Update database with new ratings
        cursor.execute("""
            UPDATE elo_rating 
            SET elo_rating = ? 
            WHERE team_id = ?
        """, (home_elo_new, match['home_team_id']))
        
        cursor.execute("""
            UPDATE elo_rating 
            SET elo_rating = ? 
            WHERE team_id = ?
        """, (away_elo_new, match['away_team_id']))
        
        conn.commit()
        
    return home_elo, away_elo

def add_team_stats(conn, match):
    """Add the teams' stats for a match to the team_running_stats table"""
    cursor = conn.cursor()
    
    try:
        # Convert pandas Series to dict if the match is a pandas Series
        if isinstance(match, pd.Series):
            # Convert the pandas Series to a dictionary and handle NaN values
            match_dict = {}
            for key, value in match.items():
                if pd.isna(value):
                    match_dict[key] = None
                else:
                    match_dict[key] = value
            match = match_dict

        # Check that the required fields are present
        required_fields = [
            'home_team', 'away_team',
            'home_team_id', 'away_team_id',
            'start_time', 'season_id',
            'competition_id', 'fixture_id',
            'home_goals', 'away_goals'
        ]
        missing_fields = [field for field in required_fields if field not in match or match[field] is None]
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields} for match ID: {match.get('fixture_id', 'unknown')}")

        home_stats = {
            'team_name': match['home_team'],
            'team_id': match['home_team_id'],
            'start_time': match['start_time'],
            'season_id': match['season_id'],
            'competition_id': match['competition_id'],
            'match_id': match['fixture_id'],
            'match_status': 'ended',
            'qualifier': 'home',
            'opponent_team_name': match['away_team'],
            'opponent_team_id': match['away_team_id'],
            'goals_scored': match['home_goals'],
            'goals_conceded': match['away_goals'],
            'match_outcome': 'win' if match['home_goals'] > match['away_goals'] else 'loss' if match['home_goals'] < match['away_goals'] else 'draw',
            'clean_sheet': match['away_goals'] == 0,
            'passes_successful': match.get('home_passes_successful'),
            'passes_total': match.get('home_passes_total'),
            'shots_on_target': match.get('home_shots_on_target'),
            'shots_total': match.get('home_shots_total'),
            'chances_created': match.get('home_chances_created'),
            'tackles_successful': match.get('home_tackles_successful'),
            'tackles_total': match.get('home_tackles_total')
        }

        # Checks if the home team has basic and advanced stats, basic stats are goals and clean sheets etc. Advanced stats are like passes successfull shots on target etc.
        home_stats['has_basic_stats'] = has_basic_stats(home_stats)
        home_stats['has_advanced_stats'] = has_advanced_stats(home_stats)

        away_stats = {
            'team_name': match['away_team'],
            'team_id': match['away_team_id'],
            'start_time': match['start_time'],
            'season_id': match['season_id'],
            'competition_id': match['competition_id'],
            'match_id': match['fixture_id'],
            'match_status': 'ended',
            'qualifier': 'away',
            'opponent_team_name': match['home_team'],
            'opponent_team_id': match['home_team_id'],
            'goals_scored': match['away_goals'],
            'goals_conceded': match['home_goals'],
            'match_outcome': 'win' if match['away_goals'] > match['home_goals'] else 'loss' if match['away_goals'] < match['home_goals'] else 'draw',
            'clean_sheet': match['home_goals'] == 0,
            'passes_successful': match.get('away_passes_successful'),
            'passes_total': match.get('away_passes_total'),
            'shots_on_target': match.get('away_shots_on_target'),
            'shots_total': match.get('away_shots_total'),
            'chances_created': match.get('away_chances_created'),
            'tackles_successful': match.get('away_tackles_successful'),
            'tackles_total': match.get('away_tackles_total')
        }

        away_stats['has_basic_stats'] = has_basic_stats(away_stats)
        away_stats['has_advanced_stats'] = has_advanced_stats(away_stats)

        # Inser team stats into team_running_stats table
        insert_team_stats(cursor, conn, home_stats, away_stats)

    except Exception as e:
        print(f"Error adding match: {str(e)}")
        conn.rollback()
        raise

    return 0