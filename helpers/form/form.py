import sqlite3
import json

def get_last_n_matches_for_team(conn, team_id, start_time, n=50):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT json_group_array(
            json_object(
                'match_id', match_id,
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
            SELECT match_id, result, goals_scored, goals_conceded, is_home, is_intraleague_match, is_domestic_cup_match, is_continental_cup_match
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

def calculate_elo_based_stats(previous_matches, n):
    """
    Calculate form statistics based on ELO comparisons
    
    Args:
        previous_matches: List of match dictionaries with elo_ratings
        n: Number of matches to consider
        
    Returns:
        Dictionary of ELO-based statistics
    """
    # Find all ELO categories from the data
    elo_categories = set()
    for match in previous_matches:
        if 'elo_ratings' in match:
            for key in match['elo_ratings']:
                if key.startswith('average_') and not key.startswith('opponent_'):
                    elo_type = key[8:]  # Remove 'average_' prefix
                    elo_categories.add(elo_type)
    
    # Initialize statistics dictionary
    stats = {}
    
    # For each ELO category (nation_elo, league_domestic_elo, etc.)
    for elo_type in elo_categories:
        # Initialize counters for better/worse comparisons
        for comparison in ['better', 'worse']:
            stats[f'matches_vs_{comparison}_{elo_type}'] = 0
            stats[f'wins_vs_{comparison}_{elo_type}'] = 0
            stats[f'draws_vs_{comparison}_{elo_type}'] = 0
            stats[f'goals_scored_vs_{comparison}_{elo_type}'] = 0
            stats[f'goals_conceded_vs_{comparison}_{elo_type}'] = 0
    
    # Track ELO changes
    for elo_type in elo_categories:
        stats[f'total_{elo_type}_change'] = 0
    
    # Process matches
    for i, match in enumerate(previous_matches):
        if 'elo_ratings' not in match:
            continue
            
        # For each ELO category
        for elo_type in elo_categories:
            team_key = f'average_{elo_type}'
            opponent_key = f'opponent_{team_key}'
            
            if team_key in match['elo_ratings'] and opponent_key in match['elo_ratings']:
                team_elo = match['elo_ratings'][team_key]
                opponent_elo = match['elo_ratings'][opponent_key]
                
                # Determine if opponent has better or worse ELO
                comparison = 'better' if opponent_elo > team_elo else 'worse'
                
                # Count match
                stats[f'matches_vs_{comparison}_{elo_type}'] += 1
                
                # Track result
                if match['result'] == 'win':
                    stats[f'wins_vs_{comparison}_{elo_type}'] += 1
                elif match['result'] == 'draw':
                    stats[f'draws_vs_{comparison}_{elo_type}'] += 1
                
                # Track goals
                stats[f'goals_scored_vs_{comparison}_{elo_type}'] += match['goals_scored']
                stats[f'goals_conceded_vs_{comparison}_{elo_type}'] += match['goals_conceded']
                
                # Calculate ELO change (if we have next match)
                if i < len(previous_matches)-1 and 'elo_ratings' in previous_matches[i+1]:
                    next_match = previous_matches[i+1]
                    if team_key in next_match['elo_ratings']:
                        next_elo = next_match['elo_ratings'][team_key]
                        elo_change = next_elo - team_elo
                        stats[f'total_{elo_type}_change'] += elo_change
    
    # Calculate derived statistics
    for elo_type in elo_categories:
        for comparison in ['better', 'worse']:
            matches_key = f'matches_vs_{comparison}_{elo_type}'
            
            if stats[matches_key] > 0:
                # Calculate win and draw rates
                stats[f'wins_vs_{comparison}_{elo_type}'] = stats[f'wins_vs_{comparison}_{elo_type}'] / stats[matches_key]
                stats[f'draws_vs_{comparison}_{elo_type}'] = stats[f'draws_vs_{comparison}_{elo_type}'] / stats[matches_key]
                
                # Calculate average goals
                stats[f'ave_goals_scored_vs_{comparison}_{elo_type}'] = stats[f'goals_scored_vs_{comparison}_{elo_type}'] / stats[matches_key]
                stats[f'ave_goals_conceded_vs_{comparison}_{elo_type}'] = stats[f'goals_conceded_vs_{comparison}_{elo_type}'] / stats[matches_key]
                
                # Remove raw totals
                del stats[f'goals_scored_vs_{comparison}_{elo_type}']
                del stats[f'goals_conceded_vs_{comparison}_{elo_type}']
            else:
                # Set defaults for no matches
                stats[f'wins_vs_{comparison}_{elo_type}'] = 0
                stats[f'draws_vs_{comparison}_{elo_type}'] = 0
                stats[f'ave_goals_scored_vs_{comparison}_{elo_type}'] = 0
                stats[f'ave_goals_conceded_vs_{comparison}_{elo_type}'] = 0
                
                # Remove raw totals
                if f'goals_scored_vs_{comparison}_{elo_type}' in stats:
                    del stats[f'goals_scored_vs_{comparison}_{elo_type}']
                if f'goals_conceded_vs_{comparison}_{elo_type}' in stats:
                    del stats[f'goals_conceded_vs_{comparison}_{elo_type}']
    
    # Calculate average ELO change
    for elo_type in elo_categories:
        stats[f'ave_{elo_type}_change'] = stats[f'total_{elo_type}_change'] / (len(previous_matches) - 1) if len(previous_matches) > 1 else 0
        del stats[f'total_{elo_type}_change']
    
    return stats

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
        'clean_sheets': 0,
        'home_match_count': 0,
        'away_match_count': 0,
        'intraleague_match_count': 0,
        'domestic_comp_match_count': 0,
        'continental_match_count': 0
    }

    calculation_stats ={
        'total_goals_scored': 0,
        'total_goals_scored_at_home': 0,
        'total_goals_scored_away': 0,
        'total_goals_conceded': 0,
        'total_goals_conceded_at_home': 0,
        'total_goals_conceded_away': 0,
        'intraleague_goals_scored': 0,
        'intraleague_goals_conceded': 0,
        'domestic_comp_goals_scored': 0,
        'domestic_comp_goals_conceded': 0,
        'continental_goals_scored': 0,
        'continental_goals_conceded': 0
        }
    
    # Single pass through matches
    for match in previous_matches:
        # Basic results
        if match['result'] == 'win':
            stats['wins'] += 1
        elif match['result'] == 'draw':
            stats['draws'] += 1
        
        # Location-based
        if match['is_home']:
            stats['home_match_count'] += 1
            if match['result'] == 'win': stats['wins_at_home'] += 1
            if match['result'] == 'draw': stats['draws_at_home'] += 1
        else:
            stats['away_match_count'] += 1
            if match['result'] == 'win': stats['wins_away'] += 1
            if match['result'] == 'draw': stats['draws_away'] += 1
        
        # Competition type
        if match['is_intraleague_match']:
            stats['intraleague_match_count'] += 1
            calculation_stats['intraleague_goals_scored'] += match['goals_scored']
            calculation_stats['intraleague_goals_conceded'] += match['goals_conceded']
            if match['result'] == 'win': stats['intraleague_wins'] += 1
            if match['result'] == 'draw': stats['intraleague_draws'] += 1
        
        if match['is_domestic_cup_match']:
            stats['domestic_comp_match_count'] += 1
            calculation_stats['domestic_comp_goals_scored'] += match['goals_scored']
            calculation_stats['domestic_comp_goals_conceded'] += match['goals_conceded']
            if match['result'] == 'win': stats['domestic_comp_wins'] += 1
            if match['result'] == 'draw': stats['domestic_comp_draws'] += 1
        
        if match['is_continental_cup_match']:
            stats['continental_match_count'] += 1
            calculation_stats['continental_goals_scored'] += match['goals_scored']
            calculation_stats['continental_goals_conceded'] += match['goals_conceded']
            if match['result'] == 'win': stats['continental_wins'] += 1
            if match['result'] == 'draw': stats['continental_draws'] += 1
        
        # General stats
        calculation_stats['total_goals_scored'] += match['goals_scored']
        calculation_stats['total_goals_conceded'] += match['goals_conceded']
        calculation_stats['total_goals_scored_at_home'] += match['goals_scored'] if match['is_home'] else 0
        calculation_stats['total_goals_conceded_at_home'] += match['goals_conceded'] if match['is_home'] else 0
        calculation_stats['total_goals_scored_away'] += match['goals_scored'] if not match['is_home'] else 0
        calculation_stats['total_goals_conceded_away'] += match['goals_conceded'] if not match['is_home'] else 0
        if match['goals_conceded'] == 0:
            stats['clean_sheets'] += 1
    
    # Calculate averages
    stats['ave_goals_scored'] = calculation_stats['total_goals_scored'] / n if n > 0 else 0
    stats['ave_goals_conceded'] = calculation_stats['total_goals_conceded'] / n if n > 0 else 0

    stats['ave_goals_scored_at_home'] = safe_divide(calculation_stats['total_goals_scored_at_home'], stats['home_match_count'])
    stats['ave_goals_conceded_at_home'] = safe_divide(calculation_stats['total_goals_conceded_at_home'], stats['home_match_count'])
    stats['ave_goals_scored_away'] = safe_divide(calculation_stats['total_goals_scored_away'], stats['away_match_count'])
    stats['ave_goals_conceded_away'] = safe_divide(calculation_stats['total_goals_conceded_away'], stats['away_match_count'])
    
    # Competition-specific averages
    stats['ave_intraleague_goals_scored'] = safe_divide(
        calculation_stats['intraleague_goals_scored'], stats['intraleague_match_count']
    )
    stats['ave_intraleague_goals_conceded'] = safe_divide(
        calculation_stats['intraleague_goals_conceded'], stats['intraleague_match_count']
    )
    stats['ave_domestic_comp_goals_scored'] = safe_divide(
        calculation_stats['domestic_comp_goals_scored'], stats['domestic_comp_match_count']
    )
    stats['ave_domestic_comp_goals_conceded'] = safe_divide(
        calculation_stats['domestic_comp_goals_conceded'], stats['domestic_comp_match_count']
    )
    stats['ave_continental_goals_scored'] = safe_divide(
        calculation_stats['continental_goals_scored'], stats['continental_match_count']
    )
    stats['ave_continental_goals_conceded'] = safe_divide(
        calculation_stats['continental_goals_conceded'], stats['continental_match_count']
    )
    
    # Calculate ELO-based statistics
    elo_stats = calculate_elo_based_stats(previous_matches, n)
    
    # Merge ELO stats into main stats
    stats.update(elo_stats)
    
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

def get_elo_ratings_for_match(conn, match_id, team_id, is_home):
    """
    Retrieve and calculate average ELO ratings for both the team and opponent in a specific match.
    
    Args:
        conn: Database connection
        match_id: The match ID
        team_id: The team ID
        is_home: Boolean indicating if the team is the home team
    
    Returns:
        Dictionary with averaged ELO ratings for both team and opponent
    """
    cursor = conn.cursor()
    
    # Determine team prefix based on home/away status
    team_prefix = "home_team" if is_home else "away_team"
    opponent_prefix = "away_team" if is_home else "home_team"
    
    # Define the categories we want to average
    categories = [
        "nation_elo",
        "league_domestic_elo",
        "league_continental_elo",
        "elo_home_matches",
        "elo_away_matches",
        "elo",
        "elo_domestic",
        "elo_intraleague",
        "elo_international"
    ]
    
    # Define K-factors
    k_factors = [5, 10, 20, 30, 40, 80]
    
    # Query to get all ELO columns for the match
    query = f"""
        SELECT * FROM elo_history 
        WHERE match_id = ?
    """
    
    cursor.execute(query, (match_id,))
    row = cursor.fetchone()
    
    if not row:
        return None
    
    # Get column names from cursor
    column_names = [description[0] for description in cursor.description]
    
    # Create result dictionary
    result = {}
    
    # Calculate averages for each category for team
    for category in categories:
        # Find all columns for this category with different K-factors
        team_category_values = []
        for k in k_factors:
            column_name = f"{team_prefix}_{category}_K{k}"
            if column_name in column_names:
                column_index = column_names.index(column_name)
                value = row[column_index]
                if value is not None:  # Skip NULL values
                    team_category_values.append(value)
        
        # Calculate average if we have values
        if team_category_values:
            average_value = sum(team_category_values) / len(team_category_values)
            result[f"average_{category}"] = average_value
    
    # Calculate averages for each category for opponent
    for category in categories:
        # Find all columns for this category with different K-factors
        opponent_category_values = []
        for k in k_factors:
            column_name = f"{opponent_prefix}_{category}_K{k}"
            if column_name in column_names:
                column_index = column_names.index(column_name)
                value = row[column_index]
                if value is not None:  # Skip NULL values
                    opponent_category_values.append(value)
        
        # Calculate average if we have values
        if opponent_category_values:
            average_value = sum(opponent_category_values) / len(opponent_category_values)
            result[f"opponent_average_{category}"] = average_value
    
    # Also store team and opponent IDs for reference
    team_id_column = f"{team_prefix}_id"
    opponent_id_column = f"{opponent_prefix}_id"
    
    if team_id_column in column_names:
        result["team_id"] = row[column_names.index(team_id_column)]
    
    if opponent_id_column in column_names:
        result["opponent_id"] = row[column_names.index(opponent_id_column)]
    
    cursor.close()
    return result

def get_elo_ratings_for_multiple_matches(conn, matches, team_id):
    results = {}
    for match in matches:
        match_id = match['match_id']
        is_home = match['is_home']
        elo_ratings = get_elo_ratings_for_match(conn, match_id, team_id, is_home)
        results[match_id] = elo_ratings
    return results

def enrich_matches_data_with_elo_ratings(matches, elo_ratings):

    enriched_matches = []
    for match in matches:
        match_id = match['match_id']
        is_home = match['is_home']
        match['elo_ratings'] = elo_ratings[match_id]
        enriched_matches.append(match)
    return enriched_matches



if __name__ == "__main__":
    conn = sqlite3.connect("v2db.sqlite")
    matches = get_last_n_matches_for_team(conn, 'sr:competitor:42', '2024-03-31T12:30:00+00:00',50)
    elo_ratings = get_elo_ratings_for_multiple_matches(conn, matches, 'sr:competitor:42')
    enriched_matches = enrich_matches_data_with_elo_ratings(matches, elo_ratings)
    form_stats = calculate_form_stats_for_multiple_ns(enriched_matches, [1,3,5,10,20,50])
    print(form_stats)