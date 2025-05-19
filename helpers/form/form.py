import sqlite3
import json

def get_last_n_matches_for_team(conn, team_id, start_time, n=50):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT json_group_array(
            json_object(
                'match_id', match_id,
                'start_time', start_time,
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
            SELECT match_id, start_time, result, goals_scored, goals_conceded, is_home, is_intraleague_match, is_domestic_cup_match, is_continental_cup_match
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

def calculate_elo_based_stats(previous_matches):
    """
    Calculate form statistics based on ELO comparisons
    
    Args:
        previous_matches: List of match dictionaries with elo_ratings
        n: Number of matches to consider
        
    Returns:
        Dictionary of ELO-based statistics
    """

    predefined_elo_categories = [
        'nation_elo',
        'league_domestic_elo',
        'league_continental_elo',
        'elo_home_matches',
        'elo_away_matches',
        'elo',
        'elo_domestic',
        'elo_intraleague',
        'elo_international'
    ]

    # Initialize statistics dictionary
    stats = {}

    # Find all ELO categories from the data
    # Initialize all possible stats to 0
    
    # For each ELO category (nation_elo, league_domestic_elo, etc.)
    for elo_type in predefined_elo_categories:
        # Initialize counters for better/worse comparisons
        for comparison in ['better', 'worse', 'similar']:
            stats[f'matches_vs_{comparison}_{elo_type}'] = 0
            stats[f'wins_vs_{comparison}_{elo_type}'] = 0
            stats[f'draws_vs_{comparison}_{elo_type}'] = 0
            stats[f'goals_scored_vs_{comparison}_{elo_type}'] = 0
            stats[f'goals_conceded_vs_{comparison}_{elo_type}'] = 0
    
    # Track ELO changes
    for elo_type in predefined_elo_categories:
        stats[f'total_{elo_type}_change'] = 0
    
    # Process matches
    for i, match in enumerate(previous_matches):
        if 'elo_ratings' not in match:
            continue
            
        # For each ELO category
        for elo_type in predefined_elo_categories:
            team_key = f'average_{elo_type}'
            opponent_key = f'opponent_{team_key}'
            
            if team_key in match['elo_ratings'] and opponent_key in match['elo_ratings']:
                team_elo = match['elo_ratings'][team_key]
                opponent_elo = match['elo_ratings'][opponent_key]
                
                # Determine if opponent has better or worse ELO
                elo_difference = opponent_elo - team_elo
                epsilon = 2
                if abs(elo_difference) < epsilon:  # Considered similar if difference less than 3
                    comparison = 'similar'
                elif elo_difference > epsilon:
                    comparison = 'better'
                elif elo_difference < -epsilon:
                    comparison = 'worse'
                
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
    for elo_type in predefined_elo_categories:
        for comparison in ['better', 'worse', 'similar']:
            matches_key = f'matches_vs_{comparison}_{elo_type}'
            
            if stats[matches_key] > 0:
                # Calculate win and draw rates
                stats[f'wins_vs_{comparison}_{elo_type}'] = stats[f'wins_vs_{comparison}_{elo_type}']
                stats[f'draws_vs_{comparison}_{elo_type}'] = stats[f'draws_vs_{comparison}_{elo_type}']
                stats[f'ave_goals_scored_vs_{comparison}_{elo_type}'] = stats[f'goals_scored_vs_{comparison}_{elo_type}']/stats[f'matches_vs_{comparison}_{elo_type}']
                stats[f'ave_goals_conceded_vs_{comparison}_{elo_type}'] = stats[f'goals_conceded_vs_{comparison}_{elo_type}']/stats[f'matches_vs_{comparison}_{elo_type}']
            else:
                # Set defaults for no matches
                stats[f'wins_vs_{comparison}_{elo_type}'] = 0
                stats[f'draws_vs_{comparison}_{elo_type}'] = 0
                stats[f'ave_goals_scored_vs_{comparison}_{elo_type}'] = 0
                stats[f'ave_goals_conceded_vs_{comparison}_{elo_type}'] = 0
            
            del stats[f'goals_scored_vs_{comparison}_{elo_type}']
            del stats[f'goals_conceded_vs_{comparison}_{elo_type}']
    

    
    # Calculate average ELO change
    for elo_type in predefined_elo_categories:
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
        'continental_match_count': 0,
        'ave_goals_scored': 0,
        'ave_goals_conceded': 0,
        'ave_goals_scored_at_home': 0,
        'ave_goals_conceded_at_home': 0,
        'ave_goals_scored_away': 0,
        'ave_goals_conceded_away': 0,
        'ave_intraleague_goals_scored': 0,
        'ave_intraleague_goals_conceded': 0,
        'ave_domestic_comp_goals_scored': 0,
        'ave_domestic_comp_goals_conceded': 0,
        'ave_continental_goals_scored': 0,
        'ave_continental_goals_conceded': 0
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
    
    if not previous_matches:
        elo_stats = calculate_elo_based_stats(previous_matches)
    
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
    elo_stats = calculate_elo_based_stats(previous_matches)
    
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

def get_elo_ratings_for_multiple_matches(conn, matches, team_id):
    if not matches:
        return {}

    # Get all match IDs
    match_ids = [str(m['match_id']) for m in matches]
    placeholders = ','.join(['?'] * len(match_ids))

    # Batch query
    query = f"""
        SELECT * FROM elo_history
        WHERE match_id IN ({placeholders})
    """
    
    # Execute batch query
    cursor = conn.cursor()
    cursor.execute(query, match_ids)
    rows = cursor.fetchall()
    column_names = [desc[0] for desc in cursor.description]
    
    # Create lookup dictionary
    elo_data = {row[column_names.index('match_id')]: row for row in rows}
    
    # Process all matches
    results = {}
    for match in matches:
        match_id = match['match_id']
        is_home = match['is_home']
        
        if match_id not in elo_data:
            results[match_id] = {}
            continue
            
        row = elo_data[match_id]
        results[match_id] = get_elo_ratings_for_match(row, column_names, team_id, is_home)
    
    cursor.close()
    return results

def get_elo_ratings_for_match(row, column_names, team_id, is_home):
    """Process a single ELO row into averaged values"""
    team_prefix = "home_team" if is_home else "away_team"
    opponent_prefix = "away_team" if is_home else "home_team"
    
    categories = [
        "nation_elo", "league_domestic_elo", "league_continental_elo",
        "elo_home_matches", "elo_away_matches", "elo", "elo_domestic",
        "elo_intraleague", "elo_international"
    ]
    k_factors = [5, 10, 20, 30, 40, 80]
    
    result = {}
    
    for category in categories:
        # Team processing
        team_values = []
        for k in k_factors:
            col_name = f"{team_prefix}_{category}_K{k}"
            if col_name in column_names:
                val = row[column_names.index(col_name)]
                if val is not None:
                    team_values.append(val)
        if team_values:
            result[f"average_{category}"] = sum(team_values)/len(team_values)
        
        # Opponent processing
        opponent_values = []
        for k in k_factors:
            col_name = f"{opponent_prefix}_{category}_K{k}"
            if col_name in column_names:
                val = row[column_names.index(col_name)]
                if val is not None:
                    opponent_values.append(val)
        if opponent_values:
            result[f"opponent_average_{category}"] = sum(opponent_values)/len(opponent_values)
    
    # Add IDs
    team_id_col = f"{team_prefix}_id"
    if team_id_col in column_names:
        result["team_id"] = row[column_names.index(team_id_col)] or team_id
    
    opponent_id_col = f"{opponent_prefix}_id"
    if opponent_id_col in column_names:
        result["opponent_id"] = row[column_names.index(opponent_id_col)]
    
    return result

def enrich_matches_data_with_elo_ratings(matches, elo_ratings):
    enriched_matches = []
    for match in matches:
        match_id = match['match_id']
        is_home = match['is_home']
        match['elo_ratings'] = elo_ratings[match_id]
        enriched_matches.append(match)
    return enriched_matches


# if __name__ == "__main__":
#     conn = sqlite3.connect("v2db.sqlite")
#     matches = get_last_n_matches_for_team(conn, 'sr:competitor:42', '2023-04-22T14:00:00+00:00',10)
#     elo_ratings = get_elo_ratings_for_multiple_matches(conn, matches, 'sr:competitor:42')
#     enriched_matches = enrich_matches_data_with_elo_ratings(matches, elo_ratings)
#     form_stats = calculate_form_stats_for_multiple_ns(enriched_matches, [3])
#     form_stats = {f'home_{key}': value for key, value in form_stats.items()}
#     print(form_stats)
