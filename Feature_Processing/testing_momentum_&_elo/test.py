from Data_Migration.db_connection import conn;

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
        FROM match_statistics 
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



def calculate_momentum(conn, matches, team_name, weights=[0.35, 0.25, 0.20, 0.12, 0.08]):
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