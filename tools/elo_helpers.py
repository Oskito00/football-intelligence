import sqlite3

def calculate_elo_rating(conn, match):
    """Calculate and update Elo ratings for home and away teams after a match."""
    cursor = conn.cursor()
    
    print("Processing match: ", match)
    # Get current Elo ratings (default to 1500 if new team)
    home_elo = get_or_create_elo(conn, match[1], match[2])
    away_elo = get_or_create_elo(conn, match[3], match[4])
    
    # --- ELO FORMULA IMPLEMENTATION ---
    # Home advantage: Add 100 Elo points to home team (common adjustment)
    home_advantage = 14  # Adjust this value based on your sport
    adjusted_home_elo = home_elo + home_advantage
    
    # 1. Calculate expected outcome (E)
    expected_home = 1 / (1 + 10**((away_elo - adjusted_home_elo)/400))
    expected_away = 1 - expected_home
    
    # 2. Determine actual outcome (S)
    if match[5] > match[6]:
        actual_home, actual_away = 1, 0  # Home win
    elif match[5] < match[6]:
        actual_home, actual_away = 0, 1  # Away win
    else:
        actual_home, actual_away = 0.5, 0.5  # Draw
    
    # 3. Update ratings using Elo formula: R' = R + K*(S - E)
    k_factor = 30  # Common in football; adjust for more/less volatility
    home_elo_new = home_elo + k_factor * (actual_home - expected_home)
    away_elo_new = away_elo + k_factor * (actual_away - expected_away)
    
    # --- Update database ---
    cursor.execute("""
        UPDATE elo_ratings 
        SET elo_rating = ? 
        WHERE team_id = ?
    """, (home_elo_new, match[1]))
    
    cursor.execute("""
        UPDATE elo_ratings 
        SET elo_rating = ? 
        WHERE team_id = ?
    """, (away_elo_new, match[3]))

    #Also add to the elo_history table
    save_elo_history(conn, match, home_elo, away_elo)
    conn.commit()
    cursor.close()
    return home_elo, away_elo

def get_or_create_elo(conn, team_id, team_name):
    cursor = conn.cursor()
    
    # First, completely remove all duplicate entries
    cursor.execute("""
        DELETE FROM elo_ratings 
        WHERE team_id = ? AND rowid NOT IN (
            SELECT MAX(rowid) 
            FROM elo_ratings 
            WHERE team_id = ?
        )
    """, (team_id, team_id))
    conn.commit()
    
    # Check if the team exists after cleanup
    cursor.execute("SELECT elo_rating FROM elo_ratings WHERE team_id = ?", (team_id,))
    result = cursor.fetchone()
    
    if result:
        # Team exists, return current rating
        return result[0]
    else:
        # Team doesn't exist, create new entry with default rating
        cursor.execute("""
            INSERT INTO elo_ratings (team_id, team_name, elo_rating)
            VALUES (?, ?, 1500)
        """, (team_id, team_name))
        conn.commit()
        return 1500


def save_elo_history(conn, match, home_elo, away_elo):
    """Save the elo history to the database"""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO elo_history (match_id, home_team_id, away_team_id, elo_difference, result)
        VALUES (?, ?, ?, ?, ?)
    """, (match[0],match[1], match[3], home_elo - away_elo, match[5] - match[6]))
    conn.commit()
    cursor.close()
    return 0

def analyze_elo_differences(conn):
    """
    Analyze the elo_history table to determine average Elo difference for different match outcomes.
    This function was used to determine the home advantage for the elo rating calculations.
    
    Returns:
        dict: A dictionary containing average Elo differences for home wins, draws, and away wins,
              along with counts for each outcome.
    """
    cursor = conn.cursor()
    
    # Get average Elo difference for home wins (result > 0)
    cursor.execute("""
        SELECT AVG(elo_difference), COUNT(*)
        FROM elo_history
        WHERE result > 0
    """)
    home_win_data = cursor.fetchone()
    home_win_avg = home_win_data[0] if home_win_data[0] is not None else 0
    home_win_count = home_win_data[1]
    
    # Get average Elo difference for draws (result = 0)
    cursor.execute("""
        SELECT AVG(elo_difference), COUNT(*)
        FROM elo_history
        WHERE result = 0
    """)
    draw_data = cursor.fetchone()
    draw_avg = draw_data[0] if draw_data[0] is not None else 0
    draw_count = draw_data[1]
    
    # Get average Elo difference for away wins (result < 0)
    cursor.execute("""
        SELECT AVG(elo_difference), COUNT(*)
        FROM elo_history
        WHERE result < 0
    """)
    away_win_data = cursor.fetchone()
    away_win_avg = away_win_data[0] if away_win_data[0] is not None else 0
    away_win_count = away_win_data[1]
    
    results = {
        "home_wins": {
            "avg_elo_difference": round(home_win_avg, 2),
            "count": home_win_count
        },
        "draws": {
            "avg_elo_difference": round(draw_avg, 2),
            "count": draw_count
        },
        "away_wins": {
            "avg_elo_difference": round(away_win_avg, 2),
            "count": away_win_count
        }
    }
    
    cursor.close()
    return results

if __name__ == "__main__":
    pass