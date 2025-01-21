from datetime import datetime
import sqlite3
import csv


def calculate_team_momentum(matches, weights=[0.35, 0.25, 0.20, 0.12, 0.08]):
    """
    Calculate team momentum based on their last 5 matches.
    Positive momentum means improving form, negative means declining form.
    
    Args:
        matches: List of match dictionaries containing performance stats
        weights: List of weights for each match (most recent first)
    
    Returns:
        float: Momentum score between -1 and 1
    """
    if len(matches) < 2:
        return 0.0

    match_scores = []
    
    # Calculate match scores (most recent first)
    for match in matches:
        # Calculate basic indicators
        basic_indicators = {
            'goals_ratio': (match['goals_scored'] / match['goals_conceded']) 
                          if match['goals_conceded'] > 0 
                          else match['goals_scored'],
            'win': 1 if match['wins'] == 1 else 0,
            'clean_sheet': 1 if match['clean_sheets'] == 1 else 0
        }
        
        # Calculate advanced indicators
        advanced_indicators = {
            'shot_accuracy': match['shots_on_target'] / match['total_shots'] 
                           if match['total_shots'] > 0 else 0,
            'pass_accuracy': match['pass_accuracy']
        }
        
        # Calculate match score with weighted components
        match_score = (
            0.35 * basic_indicators['win'] +
            0.25 * basic_indicators['goals_ratio'] +
            0.15 * basic_indicators['clean_sheet'] +
            0.15 * advanced_indicators['shot_accuracy'] +
            0.10 * advanced_indicators['pass_accuracy']
        )
        
        match_scores.append(match_score)

    # Calculate trends between consecutive matches
    trends = []
    for i in range(1, len(match_scores)):
        trend = match_scores[i-1] - match_scores[i]  # Compare newer to older matches
        trends.append(trend)
    
    # Calculate weighted average of trends
    weighted_trend = sum(t * w for t, w in zip(trends, weights[1:]))
    
    # Clamp between -1 and 1
    momentum = max(-1, min(1, weighted_trend))
    
    return round(momentum, 3)

def calculate_squad_strength(all_key_players, missing_players):
    """
    Calculate squad strength based on weighted importance of available players
    
    Args:
        all_key_players: List of all key players with their scores
        missing_players: List of missing key players
    
    Returns:
        float: Squad strength score between 0 and 1
    """
    #TODO: Would be good to identify an average score across all teams and put that instead of None so we have more data.
    if not all_key_players:
        return None
        
    # Create a set of missing player IDs for quick lookup
    missing_ids = {p['player_id'] for p in missing_players}
    
    # Calculate maximum possible strength (weighted by position in ranking)
    max_strength = 0
    actual_strength = 0
    
    for i, player in enumerate(all_key_players):
        # Weight by position (higher ranked players count more)
        position_weight = 1 / (i + 1)  # 1st = 1.0, 2nd = 0.5, 3rd = 0.33, etc.
        player_weight = position_weight * player['average_score']
        
        max_strength += player_weight
        
        # If player is available (not in missing_ids), add to actual strength
        if player['player_id'] not in missing_ids:
            actual_strength += player_weight
    
    # Return ratio of actual to maximum strength
    return actual_strength / max_strength if max_strength > 0 else 0.0

def get_key_players_count(conn, team_id, start_time):
    """Get count and details of key players for a team"""
    cursor = conn.cursor()
    cursor.execute("""
        WITH latest_stats AS (
            SELECT 
                prs.player_id,
                prs.player_name,
                prs.overall_importance_score,
                prs.form_rating,
                (prs.overall_importance_score * 0.4 + prs.form_rating * 0.6) as average_score,
                ROW_NUMBER() OVER (
                    PARTITION BY prs.player_id 
                    ORDER BY prs.start_time DESC
                ) as rn
            FROM player_running_stats prs
            WHERE team_id = ?
            AND prs.overall_importance_score >= 15
            AND prs.form_rating >= 15
            AND datetime(prs.start_time) >= datetime(?, '-30 days')
        )
        SELECT 
            player_id,
            player_name,
            overall_importance_score as importance,
            form_rating as form,
            average_score
        FROM latest_stats
        WHERE rn = 1
        ORDER BY average_score DESC
    """, (team_id, start_time))
    
    players = [
        {
            'player_id': row[0],
            'player_name': row[1],
            'importance': row[2],
            'form': row[3],
            'average_score': row[4]
        }
        for row in cursor.fetchall()
    ]
    
    return len(players), players

def calculate_team_fatigue(time_since_last_match, matches_in_last_10_days):
    """
    Calculate team fatigue based on time since last match and matches played in last 10 days.
    
    Args:
        time_since_last_match (int): Days since the team's last match.
        matches_in_last_10_days (int): Number of matches played in the last 10 days.

    Returns:
        float: Fatigue score (0 to 1).
    """
    # Time fatigue: 0 days = 1.0, 7+ days = 0.0
    time_fatigue = max(0, 1 - (time_since_last_match / 7))

    # Match fatigue: 0 matches = 0.0, 5+ matches = 1.0
    match_fatigue = min(1, matches_in_last_10_days / 5)

    # Combine factors equally weighted
    fatigue_score = (time_fatigue + match_fatigue) / 2

    return round(fatigue_score, 3)

def calculate_match_importance(
    is_derby,
    is_cup_match,
    home_position,
    away_position,
    home_points,
    away_points
):
    """
    Calculate the importance of a match based on a simplified set of parameters.
    
    Args:
        is_derby (bool): Whether the match is a derby.
        is_cup_match (bool): Whether the match is a cup match.
        home_position (int): League position of the home team.
        away_position (int): League position of the away team.
        home_points (int): Current points of the home team.
        away_points (int): Current points of the away team.
    
    Returns:
        float: Match importance score.
    """
    # Base importance values
    BASE_LEAGUE_IMPORTANCE = 5.0
    BASE_CUP_IMPORTANCE = 6.0
    DERBY_BONUS = 2.0
    TITLE_RACE_BONUS = 2.5
    RELEGATION_BATTLE_BONUS = 2.0
    POSITION_PROXIMITY_MAX_BONUS = 1.5
    POINTS_PROXIMITY_MAX_BONUS = 1.5

    # Initialize importance
    importance = BASE_CUP_IMPORTANCE if is_cup_match else BASE_LEAGUE_IMPORTANCE

    # Derby bonus
    if is_derby:
        importance += DERBY_BONUS

    # Position proximity bonus
    if home_position is not None and away_position is not None:
        max_position = max(home_position, away_position)
        position_bonus = max(0, POSITION_PROXIMITY_MAX_BONUS * (1 - (max_position / 10)))
        importance += position_bonus

    # Points proximity bonus
    if home_points is not None and away_points is not None:
        points_diff = abs(home_points - away_points)
        points_bonus = max(0, POINTS_PROXIMITY_MAX_BONUS * (1 - (points_diff / 9)))
        importance += points_bonus

    # Title race bonus (if either team is in the top 3)
    if (home_position is not None and home_position <= 3) or (away_position is not None and away_position <= 3):
        importance += TITLE_RACE_BONUS

    # Relegation battle bonus (if either team is in the bottom 3)
    if (home_position is not None and home_position >= 18) or (away_position is not None and away_position >= 18):
        importance += RELEGATION_BATTLE_BONUS

    return round(importance, 2)

def calculate_metrics(
    last_5_matches,
    h2h_matches
):
    """
    Calculates football performance metrics based on the provided input data.
    
    Args:
    - last_5_matches (list of dicts): Each dictionary contains data for the last 5 matches with keys:
        'goals_scored', 'goals_conceded', 'wins', 'clean_sheets', 
        'total_passes', 'passes_successful', 'total_shots', 'shots_on_target', 'goals_scored_in_match',
        'tackles_successful', 'tackles_total'
    - h2h_matches (list of dicts): Each dictionary contains data for head-to-head matches with keys:
        'h2h_goals_scored', 'h2h_clean_sheets', 'h2h_points'

    Returns:
    - dict: A dictionary with calculated metrics.
    """
    # Helper function to calculate averages
    def calculate_average(values):
        return sum(values) / len(values) if values else 0

    # Last 5 matches data
    goals_scored = [match['goals_scored'] for match in last_5_matches]
    goals_conceded = [match['goals_conceded'] for match in last_5_matches]
    wins = [match['wins'] for match in last_5_matches]
    clean_sheets = [match['clean_sheets'] for match in last_5_matches]
    pass_accuracy = [match['pass_accuracy'] for match in last_5_matches]
    total_shots = [match['total_shots'] for match in last_5_matches]
    shots_on_target = [match['shots_on_target'] for match in last_5_matches]
    tackles_successful = [match['tackles_successful'] for match in last_5_matches]
    tackles_total = [match['tackles_total'] for match in last_5_matches]

    # H2H matches data
    h2h_goals_scored = [match['h2h_goals_scored'] for match in h2h_matches]
    h2h_clean_sheets = [match['h2h_clean_sheets'] for match in h2h_matches]
    h2h_points = [match['h2h_points'] for match in h2h_matches]

    # Calculated metrics
    metrics = {
        # Last 5 matches
        'average_goals_scored': calculate_average(goals_scored),
        'average_goals_conceded': calculate_average(goals_conceded),
        'average_win_rate': sum(wins) / len(last_5_matches) if last_5_matches else 0,
        'average_clean_sheets': sum(clean_sheets) / len(last_5_matches) if last_5_matches else 0,

        # H2H matches
        'h2h_average_goals': calculate_average(h2h_goals_scored),
        'h2h_average_clean_sheets': calculate_average(h2h_clean_sheets),
        'h2h_average_points': calculate_average(h2h_points),

        # Advanced stats
        'pass_effectivness': sum(pass_accuracy) / len(last_5_matches),
        'shot_accuracy': sum(shots_on_target) / sum(total_shots) if sum(total_shots) > 0 else 0,
        'conversion_rate': sum(goals_scored) / sum(shots_on_target) if sum(shots_on_target) > 0 else 0,
        'defensive_success':sum(tackles_successful) / sum(tackles_total) if sum(tackles_total) > 0 else 0.845
    }

    return metrics

def calculate_and_write_metrics(
    start_time,
    home_team,
    away_team,
    competition_id,
    home_last_5_matches,
    away_last_5_matches,
    home_h2h_matches,
    away_h2h_matches,
    match_details,
    home_fatigue_details,
    away_fatigue_details,
    output_file='sportradar/future_matches/simple_implementation/match_metrics.csv'
):
    # Calculate basic metrics
    home_metrics = calculate_metrics(home_last_5_matches, home_h2h_matches)
    away_metrics = calculate_metrics(away_last_5_matches, away_h2h_matches)
    
    # Calculate match importance, fatigue and momentum
    match_importance = calculate_match_importance(
        match_details['is_derby'],
        match_details['is_cup_match'],
        match_details['home_position'],
        match_details['away_position'],
        match_details['home_points'],
        match_details['away_points']
    )
    home_fatigue = calculate_team_fatigue(*home_fatigue_details)
    away_fatigue = calculate_team_fatigue(*away_fatigue_details)
    home_momentum = calculate_team_momentum(home_last_5_matches)
    away_momentum = calculate_team_momentum(away_last_5_matches)
    
    # Calculate squad strength
    conn = sqlite3.connect('football_data.db')
    _, home_players = get_key_players_count(conn, 'sr:competitor:2696', datetime(2024, 12, 12))
    _, away_players = get_key_players_count(conn, 'sr:competitor:2687', datetime(2024, 12, 12))
    
    
    # home_squad_strength = calculate_squad_strength(home_players, [])  # Add missing players if needed
    # away_squad_strength = calculate_squad_strength(away_players, [{'player_id': 'sr:player:2409691', 'player_name': 'Gaspar, Kialonda', 'importance': 29.30347207527007, 'form': 30.303322259136213, 'average_score': 29.903382185589756}, {'player_id': 'sr:player:1570104', 'player_name': 'Gallo, Antonino', 'importance': 28.324337707852067, 'form': 21.8716457960644, 'average_score': 24.452722560779467}, {'player_id': 'sr:player:1118041', 'player_name': 'Pelmard, Andy', 'importance': 30.57774490624174, 'form': 18.988421052631576, 'average_score': 23.624150594075644}])  # Add missing players if needed
    # print(home_squad_strength)
    # print(away_squad_strength)
    #CALCULATE THIS MYSELF
    home_squad_strength = 0.58
    away_squad_strength = 0.85


    # Create ordered metrics list
    ordered_metrics = [
        start_time,
        home_team,
        away_team,
        competition_id,
        match_importance,
        home_metrics['average_goals_scored'],
        home_metrics['average_goals_conceded'],
        home_metrics['average_win_rate'],
        home_metrics['average_clean_sheets'],
        home_fatigue,
        home_momentum,
        away_metrics['average_goals_scored'],
        away_metrics['average_goals_conceded'],
        away_metrics['average_win_rate'],
        away_metrics['average_clean_sheets'],
        away_fatigue,
        away_momentum,
        home_metrics['h2h_average_goals'],
        home_metrics['h2h_average_clean_sheets'],
        home_metrics['h2h_average_points'],
        away_metrics['h2h_average_goals'],
        away_metrics['h2h_average_clean_sheets'],
        away_metrics['h2h_average_points'],
        home_metrics['pass_effectivness'],
        home_metrics['shot_accuracy'],
        home_metrics['conversion_rate'],
        home_metrics['defensive_success'],
        away_metrics['pass_effectivness'],
        away_metrics['shot_accuracy'],
        away_metrics['conversion_rate'],
        away_metrics['defensive_success'],
        home_squad_strength,
        away_squad_strength
    ]
    
    # Define headers
    headers = [
        'start_time',
        'home_team',
        'away_team',
        'competition_id',
        'match_importance',
        'average_home_goals_scored',
        'average_home_goals_conceded',
        'average_home_win_rate',
        'average_home_clean_sheets',
        'home_fatigue',
        'home_momentum',
        'average_away_goals_scored',
        'average_away_goals_conceded',
        'average_away_win_rate',
        'average_away_clean_sheets',
        'away_fatigue',
        'away_momentum',
        'home_h2h_avg_goals',
        'home_h2h_avg_clean_sheets',
        'home_h2h_avg_points',
        'away_h2h_avg_goals',
        'away_h2h_avg_clean_sheets',
        'away_h2h_avg_points',
        'home_pass_effectiveness',
        'home_shot_accuracy',
        'home_conversion_rate',
        'home_defensive_success',
        'away_pass_effectiveness',
        'away_shot_accuracy',
        'away_conversion_rate',
        'away_defensive_success',
        'home_squad_strength',
        'away_squad_strength'
    ]
    
    # Write to CSV
    with open(output_file, 'a', newline='') as f:
        writer = csv.writer(f)
        # Only write headers if file is empty
        if f.tell() == 0:
            writer.writerow(headers)
        writer.writerow(ordered_metrics)
    
    conn.close()
    return ordered_metrics


conn = sqlite3.connect('football_data.db')
home_players = get_key_players_count(conn, 'sr:competitor:2696', datetime(2024, 12, 12))
away_players = get_key_players_count(conn, 'sr:competitor:2687', datetime(2024, 12, 12))

print(home_players)
print(away_players)


#MATCH DETAILS

match_details = {
    'is_derby': True,
    'is_cup_match': False,
    'home_position': 3,
    'away_position': 13,
    'home_points': 40,
    'away_points': 24
}
#HOME STATS

home_last_5_matches = [
    {'goals_scored': 1, 'goals_conceded': 1, 'wins': 0, 'clean_sheets': 0,
    'pass_accuracy': 0.87, 'total_shots': 26, 'shots_on_target': 7, 
     'tackles_successful': 0, 'tackles_total': 0},
    {'goals_scored': 0, 'goals_conceded': 2, 'wins': 0, 'clean_sheets': 0,
     'pass_accuracy': 0.87, 'total_shots': 23, 'shots_on_target': 3, 
     'tackles_successful': 0, 'tackles_total': 0},
    {'goals_scored': 1, 'goals_conceded': 1, 'wins': 0, 'clean_sheets': 0,
     'pass_accuracy': 0.87, 'total_shots': 9, 'shots_on_target': 3  , 
     'tackles_successful': 0, 'tackles_total': 0},
    {'goals_scored': 3, 'goals_conceded': 1, 'wins': 1, 'clean_sheets': 0,
     'pass_accuracy': 0.83, 'total_shots': 14, 'shots_on_target': 5, 
     'tackles_successful': 0, 'tackles_total': 0},
    {'goals_scored': 1, 'goals_conceded': 0, 'wins': 1, 'clean_sheets': 1,
     'pass_accuracy': 0.90, 'total_shots': 13, 'shots_on_target': 5, 
     'tackles_successful': 0, 'tackles_total': 0}
]

# Example H2H matches data
home_h2h_matches = [
    {'h2h_goals_scored': 1, 'h2h_clean_sheets': 1, 'h2h_points': 3},
    {'h2h_goals_scored': 3, 'h2h_clean_sheets': 0, 'h2h_points': 3},
    {'h2h_goals_scored': 2, 'h2h_clean_sheets': 0, 'h2h_points': 1},
    {'h2h_goals_scored': 2, 'h2h_clean_sheets': 1, 'h2h_points': 3}
]

home_fatigue_details = (3, 2)  # time since last match, matches in 10 days


#AWAY STATS

away_last_5_matches = [
    {'goals_scored': 3, 'goals_conceded': 0, 'wins': 1, 'clean_sheets': 1,
    'pass_accuracy': 0.85, 'total_shots': 17, 'shots_on_target': 7, 
     'tackles_successful': 0, 'tackles_total': 0},
    {'goals_scored': 1, 'goals_conceded': 0, 'wins': 1, 'clean_sheets': 1,
     'pass_accuracy': 0.78, 'total_shots': 9, 'shots_on_target': 4, 
     'tackles_successful': 0, 'tackles_total': 0},
    {'goals_scored': 1, 'goals_conceded': 2, 'wins': 0, 'clean_sheets': 0,
     'pass_accuracy': 0.80, 'total_shots': 13, 'shots_on_target': 4  , 
     'tackles_successful': 0, 'tackles_total': 0},
    {'goals_scored': 2, 'goals_conceded': 2, 'wins': 0, 'clean_sheets': 0,
     'pass_accuracy': 0.77, 'total_shots': 13, 'shots_on_target': 3, 
     'tackles_successful': 0, 'tackles_total': 0},
    {'goals_scored': 0, 'goals_conceded': 1, 'wins': 0, 'clean_sheets': 0,
     'pass_accuracy': 0.87, 'total_shots': 13, 'shots_on_target': 4, 
     'tackles_successful': 0, 'tackles_total': 0}
]

# Example H2H matches data
away_h2h_matches = [
    {'h2h_goals_scored': 0, 'h2h_clean_sheets': 0, 'h2h_points': 0},
    {'h2h_goals_scored': 2, 'h2h_clean_sheets': 0, 'h2h_points': 0},
    {'h2h_goals_scored': 2, 'h2h_clean_sheets': 0, 'h2h_points': 1},
    {'h2h_goals_scored': 0, 'h2h_clean_sheets': 0, 'h2h_points': 0}
]

away_fatigue_details = (3, 2)  # time since last match, matches in 10 days


metrics = calculate_and_write_metrics(
    '2024-12-15',          # start_time
    'Arsenal',              # home_team
    'Tottenham',            # away_team
    0,                   # competition_id (Premier League)
    home_last_5_matches,
    away_last_5_matches,
    home_h2h_matches,
    away_h2h_matches,
    match_details,
    home_fatigue_details,
    away_fatigue_details,
    'sportradar/future_matches/simple_implementation/match_metrics.csv'
)