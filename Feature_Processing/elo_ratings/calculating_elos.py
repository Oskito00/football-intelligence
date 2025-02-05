


def calculate_elo_change(elo_diff, result, K=20):

    expected = 1 / (10^[elo_diff / 400] + 1)
    elo_change = K * (result - expected)
    return elo_change


def update_elos(home_elo, away_elo, home_final_score, away_final_score, K):

    elo_diff = abs(home_elo-away_elo)

    result = 0.5 if home_final_score == away_final_score else 1 if home_final_score > away_final_score else 0;

    home_elo_change = calculate_elo_change(elo_diff, result)
    away_elo_change = calculate_elo_change(elo_diff, 1-result)




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
        
        # Calculate advanced indicators if the stats exist (deleted from this version)
        

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