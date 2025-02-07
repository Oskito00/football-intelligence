


def calculate_elo_change(elo_diff, result, K=20):

    expected = 1 / (10^[elo_diff / 400] + 1)
    elo_change = K * (result - expected)
    return elo_change


def update_elos(home_elo, away_elo, home_final_score, away_final_score, K):

    elo_diff = abs(home_elo-away_elo)

    result = 0.5 if home_final_score == away_final_score else 1 if home_final_score > away_final_score else 0;

    home_elo_change = calculate_elo_change(elo_diff, result)
    away_elo_change = calculate_elo_change(elo_diff, 1-result)



### Oscar's advanced elo function
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
    

print("hi" in {"hi": 20, "hello": 30});