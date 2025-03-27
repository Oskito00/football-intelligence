import numpy as np

def calculate_elo_rating(conn, match):
    """Calculate and update Elo ratings for home and away teams after a match."""
    cursor = conn.cursor()
    
    # Get current Elo ratings (default to 1500 if new team)
    home_elo = get_or_create_elo(conn, match['home_team_id'], match['home_team_name'])
    away_elo = get_or_create_elo(conn, match['away_team_id'], match['away_team_name'])
    
    # --- ELO FORMULA IMPLEMENTATION ---
    # Home advantage: Add 100 Elo points to home team (common adjustment)
    home_advantage = 0  # Adjust this value based on your sport
    adjusted_home_elo = home_elo + home_advantage
    
    # 1. Calculate expected outcome (E)
    expected_home = 1 / (1 + 10**((away_elo - adjusted_home_elo)/400))
    expected_away = 1 - expected_home
    
    # 2. Determine actual outcome (S)
    if match['home_score'] > match['away_score']:
        actual_home, actual_away = 1, 0  # Home win
    elif match['home_score'] < match['away_score']:
        actual_home, actual_away = 0, 1  # Away win
    else:
        actual_home, actual_away = 0.5, 0.5  # Draw
    
    # 3. Update ratings using Elo formula: R' = R + K*(S - E)
    k_factor = 30  # Common in football; adjust for more/less volatility
    home_elo_new = home_elo + k_factor * (actual_home - expected_home)
    away_elo_new = away_elo + k_factor * (actual_away - expected_away)
    
    # --- Update database ---
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

    #Also add to the elo_history table
    cursor.execute("""
        INSERT INTO elo_history (home_team_id, away_team_id, elo_difference, result)
        VALUES (?, ?, ?, ?)
    """, (match['home_team_id'], match['away_team_id'], home_elo - away_elo, match['home_score'] - match['away_score']))
    conn.commit()
    cursor.close()
    return home_elo, away_elo


# HELPER FUNCTIONS

def get_or_create_elo(conn,team_id, team_name):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO elo_rating (team_id, team_name, elo_rating)
        VALUES (?, ?, 1500)
    """, (team_id, team_name, ))
    cursor.execute("SELECT elo_rating FROM elo_rating WHERE team_id = ?", (team_id,))
    return cursor.fetchone()[0]


def save_elo_history(conn, matches):
    """Save the elo history to the database"""
    
