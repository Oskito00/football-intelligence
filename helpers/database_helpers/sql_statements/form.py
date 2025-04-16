import sqlite3
import json


def get_last_n_matches_for_team(conn, team_id, start_time, n=50):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT json_group_array(
            json_object(
                'goals_scored', goals_scored,
                'goals_conceded', goals_conceded,
                'result', result,
                'is_home', is_home,
                'is_intraleague_match', is_intraleague_match,
                'is_domestic_cup_match', is_domestic_cup_match,
                'is_continental_cup_match', is_continental_cup_match
            )
        )
        FROM (
            SELECT result, goals_scored, goals_conceded, is_home, is_intraleague_match, is_domestic_cup_match, is_continental_cup_match
            FROM TeamMatchHistory
            WHERE team_id = ?
            AND start_time < ?
            ORDER BY start_time DESC
            LIMIT ?
        )
    """, (team_id, start_time, n))
    
    result = cursor.fetchone()
    if result and result[0]:
        return json.loads(result[0])
    return []

def calculate_form_stats_in_last_n_matches(previous_matches, n):
    """Calculate team form statistics from match data with dynamic suffixes"""
    # Initialize counters
    stats = {
        'wins': 0,
        'draws': 0,
        'wins_at_home': 0,
        'draws_at_home': 0,
        'wins_away': 0,
        'draws_away': 0,
        'intraleague_wins': 0,
        'intraleague_draws': 0,
        'domestic_comp_wins': 0,
        'domestic_comp_draws': 0,
        'continental_wins': 0,
        'continental_draws': 0,
        'clean_sheets': 0

        
    }

    calculation_stats ={'total_goals_scored': 0,
        'total_goals_conceded': 0,
        'intraleague_goals_scored': 0,
        'intraleague_goals_conceded': 0,
        'domestic_comp_goals_scored': 0,
        'domestic_comp_goals_conceded': 0,
        'continental_goals_scored': 0,
        'continental_goals_conceded': 0,
        'intraleague_matches': 0,
        'domestic_comp_matches': 0,
        'continental_matches': 0}
    
    # Single pass through matches
    for match in previous_matches:
        # Basic results
        if match['result'] == 'win':
            stats['wins'] += 1
        elif match['result'] == 'draw':
            stats['draws'] += 1
        
        # Location-based
        if match['is_home']:
            if match['result'] == 'win': stats['wins_at_home'] += 1
            if match['result'] == 'draw': stats['draws_at_home'] += 1
        else:
            if match['result'] == 'win': stats['wins_away'] += 1
            if match['result'] == 'draw': stats['draws_away'] += 1
        
        # Competition type
        if match['is_intraleague_match']:
            calculation_stats['intraleague_matches'] += 1
            calculation_stats['intraleague_goals_scored'] += match['goals_scored']
            calculation_stats['intraleague_goals_conceded'] += match['goals_conceded']
            if match['result'] == 'win': stats['intraleague_wins'] += 1
            if match['result'] == 'draw': stats['intraleague_draws'] += 1
        
        if match['is_domestic_cup_match']:
            calculation_stats['domestic_comp_matches'] += 1
            calculation_stats['domestic_comp_goals_scored'] += match['goals_scored']
            calculation_stats['domestic_comp_goals_conceded'] += match['goals_conceded']
            if match['result'] == 'win': stats['domestic_comp_wins'] += 1
            if match['result'] == 'draw': stats['domestic_comp_draws'] += 1
        
        if match['is_continental_cup_match']:
            calculation_stats['continental_matches'] += 1
            calculation_stats['continental_goals_scored'] += match['goals_scored']
            calculation_stats['continental_goals_conceded'] += match['goals_conceded']
            if match['result'] == 'win': stats['continental_wins'] += 1
            if match['result'] == 'draw': stats['continental_draws'] += 1
        
        # General stats
        calculation_stats['total_goals_scored'] += match['goals_scored']
        calculation_stats['total_goals_conceded'] += match['goals_conceded']
        if match['goals_conceded'] == 0:
            stats['clean_sheets'] += 1
    
    # Calculate averages
    stats['ave_goals_scored'] = calculation_stats['total_goals_scored'] / n if n > 0 else 0
    stats['ave_goals_conceded'] = calculation_stats['total_goals_conceded'] / n if n > 0 else 0
    
    # Competition-specific averages
    stats['ave_intraleague_goals_scored'] = safe_divide(
        calculation_stats['intraleague_goals_scored'], calculation_stats['intraleague_matches']
    )
    stats['ave_intraleague_goals_conceded'] = safe_divide(
        calculation_stats['intraleague_goals_conceded'], calculation_stats['intraleague_matches']
    )
    stats['ave_domestic_comp_goals_scored'] = safe_divide(
        calculation_stats['domestic_comp_goals_scored'], calculation_stats['domestic_comp_matches']
    )
    stats['ave_domestic_comp_goals_conceded'] = safe_divide(
        calculation_stats['domestic_comp_goals_conceded'], calculation_stats['domestic_comp_matches']
    )
    stats['ave_continental_goals_scored'] = safe_divide(
        calculation_stats['continental_goals_scored'], calculation_stats['continental_matches']
    )
    stats['ave_continental_goals_conceded'] = safe_divide(
        calculation_stats['continental_goals_conceded'], calculation_stats['continental_matches']
    )
    
    # Add suffix to all keys
    result = {}
    for key, value in stats.items():
        result[f"{key}_in_last_{n}"] = value
    
    return result

def calculate_form_stats_for_multiple_ns(previous_matches, n_lengths=[1, 3, 5, 10, 20, 50]):
    """
    Calculate form statistics across multiple time periods.
    
    Args:
        previous_matches: List of match dictionaries sorted by date (most recent first)
        n_lengths: List of integers representing the different periods to analyze
    
    Returns:
        Combined dictionary with all statistics for all periods
    """
    all_stats = {}
    
    # Process each period length
    for n in n_lengths:
        # Only use matches up to length n (or all if we have fewer)
        matches_to_use = previous_matches[:n] if len(previous_matches) >= n else previous_matches
        
        # Calculate stats for this period
        n_stats = calculate_form_stats_in_last_n_matches(matches_to_use, n)
        
        # Add to combined stats dictionary
        all_stats.update(n_stats)
    
    return all_stats

def safe_divide(numerator, denominator):
    """Handle division by zero gracefully"""
    return numerator / denominator if denominator else 0

if __name__ == "__main__":
    conn = sqlite3.connect("v2db.sqlite")
    print(calculate_form_stats_for_multiple_ns(get_last_n_matches_for_team(conn, 'sr:competitor:3309', '2023-03-31T12:30:00+00:00',50), [1,3,5,10,20,50]))