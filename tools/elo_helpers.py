import math
import sqlite3
from datetime import datetime

def elo_davidson_formula(
    conn, home_score, away_score, home_elo, away_elo, 
    k_factor, match_info, k_draw_parameter, eta_home_advantage, sigma=600
):
    """Calculate and update Elo ratings using the Davidson draw model.
    Implementation based on the BrBaLab formulation:
    https://brbalab.com/algorithmes/
    """
    # --- Convert parameters ---
    U = float(k_draw_parameter)       # Draw parameter U
    H = float(eta_home_advantage)     # Home advantage parameter H
    K = float(k_factor)               # K-factor
    Sc = float(sigma)                 # Scale parameter (600 recommended)
    
    # --- Calculate rating difference with home advantage ---
    D = float(home_elo - away_elo)    # Basic rating difference
    D_adjusted = D + H * Sc           # Add home advantage
    
    # --- Calculate expected outcome using Elo-Davidson formula ---
    # Calculate terms for denominator
    term_home = 10 ** (0.5 * D_adjusted / Sc)
    term_away = 10 ** (-0.5 * D_adjusted / Sc)
    
    # Calculate probabilities
    denominator = term_home + term_away + U
    p_home = term_home / denominator
    p_away = term_away / denominator
    p_draw = U / denominator
    
    # --- Determine actual outcome (s) ---
    if home_score > away_score:
        s = 1.0    # Home win
    elif home_score < away_score:
        s = 0.0    # Away win
    else:
        s = 0.5    # Draw
    
    # --- Apply Elo-Davidson update formula ---
    # R'_h = R_h + K [s - F(D)]
    # R'_a = R_a - K [s - F(D)]
    # Where F(D) is the expected outcome for home team = p_home
    rating_change = K * (s - p_home)
    
    # Update ratings
    home_elo_new = home_elo + rating_change
    away_elo_new = away_elo - rating_change
    
    return home_elo_new, away_elo_new

def get_entity_elo(conn, table_name, id_column, id_value, name_column=None, name_value=None):
    """
    Generic function to get ELO ratings for any entity (club, league, nation)
    
    Args:
        conn: Database connection
        table_name: The table containing ELO ratings (e.g., 'club_elo_ratings', 'league_elo_ratings')
        id_column: Column name to identify the entity (e.g., 'team_id', 'league_id', 'nation_name')
        id_value: Value to identify the entity
        name_column: Optional name column for new entries
        name_value: Optional name value for new entries
    
    Returns:
        Dictionary of ELO ratings with column names as keys
    """
    cursor = conn.cursor()
    
    # Get column info from the table
    cursor.execute(f"PRAGMA table_info({table_name})")
    all_columns = cursor.fetchall()
    
    # Filter for only elo columns (any column containing "elo")
    elo_columns = [col[1] for col in all_columns if "elo" in col[1].lower()]
    
    # Build the SELECT query dynamically
    select_columns = ", ".join(elo_columns)
    query = f"SELECT {select_columns} FROM {table_name} WHERE {id_column} = ?"
    
    cursor.execute(query, (id_value,))
    result = cursor.fetchone()
    
    if result:
        # Entity exists, return current ratings as dictionary
        return {col: val for col, val in zip(elo_columns, result)}
    else:
        # Entity doesn't exist, create new entry with default ratings
        default_rating = 1500
        
        # Create dictionary with default values
        elo_dict = {col: default_rating for col in elo_columns}
        
        # Build the INSERT query dynamically
        insert_columns = [id_column]
        values = [id_value]
        
        # Add name column if provided
        if name_column and name_value:
            insert_columns.append(name_column)
            values.append(name_value)
        
        # Add all ELO columns
        for col in elo_columns:
            insert_columns.append(col)
            values.append(default_rating)
        
        # Create and execute the query
        columns_str = ", ".join(insert_columns)
        placeholders = ", ".join(["?"] * len(insert_columns))
        insert_query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
        
        cursor.execute(insert_query, values)
        conn.commit()
        
        return elo_dict

# Wrapper functions to maintain backward compatibility
def get_club_elo(conn, team_id, team_name):
    return get_entity_elo(conn, 'club_elo_ratings', 'team_id', team_id, 'team_name', team_name)

def get_league_elo(conn, league_id):
    return get_entity_elo(conn, 'league_elo_ratings', 'league_id', league_id)

def get_nation_elo(conn, nation_name):
    return get_entity_elo(conn, 'nation_elo_ratings', 'nation_name', nation_name)


def save_elo_history(conn, match_id, home_team_id, away_team_id, 
                     home_club_elos, away_club_elos, 
                     home_nation_elos, away_nation_elos,
                     home_league_elos, away_league_elos,
                     home_score, away_score):
    """
    Save the current ELO ratings to the elo_history table
    
    Args:
        conn: Database connection
        match_id: Match ID
        home_team_id, away_team_id: Team IDs
        home_club_elos, away_club_elos: Dictionaries of club ELO ratings
        home_nation_elos, away_nation_elos: Dictionaries of nation ELO ratings or None
        home_league_elos, away_league_elos: Dictionaries of league ELO ratings or None
        home_score, away_score: Match scores
    """
    cursor = conn.cursor()
    
    # Get all columns from the elo_history table
    cursor.execute("PRAGMA table_info(elo_history)")
    table_columns = [col[1] for col in cursor.fetchall()]
    
    # Initialize data with match details
    data = {
        'match_id': match_id,
        'home_team_id': home_team_id,
        'away_team_id': away_team_id,
        'home_team_score': home_score,
        'away_team_score': away_score
    }
    
    # Add home and away team club ELOs
    for col, val in home_club_elos.items():
        data[f'home_team_{col}'] = val
        
    for col, val in away_club_elos.items():
        data[f'away_team_{col}'] = val
    
    # Add nation ELOs if available
    if home_nation_elos:
        for col, val in home_nation_elos.items():
            data[f'home_team_{col}'] = val
            
    if away_nation_elos:
        for col, val in away_nation_elos.items():
            data[f'away_team_{col}'] = val
    
    # Add league ELOs if available
    if home_league_elos:
        for col, val in home_league_elos.items():
            # Convert league_domestic_elo to home_team_league_domestic_elo
            league_col = col.replace('league_', 'team_league_')
            data[f'home_{league_col}'] = val
            
    if away_league_elos:
        for col, val in away_league_elos.items():
            league_col = col.replace('league_', 'team_league_')
            data[f'away_{league_col}'] = val
    
    # Prepare values in the order of columns in the table
    columns = []
    values = []
    
    for col in table_columns:
        if col in data:
            columns.append(col)
            values.append(data[col])
        else:
            # Use default for any missing columns
            columns.append(col)
            values.append(1500)
    
    # Build and execute query
    placeholders = ', '.join(['?'] * len(columns))
    columns_str = ', '.join(columns)
    
    cursor.execute(f"INSERT INTO elo_history ({columns_str}) VALUES ({placeholders})", values)
    conn.commit()

def update_entity_elo(conn, table_name, id_column, id_value, elo_dict):
    """
    Update ELO ratings for an entity in the database
    
    Args:
        conn: Database connection
        table_name: The table containing ELO ratings (e.g., 'club_elo_ratings', 'league_elo_ratings')
        id_column: Column name to identify the entity (e.g., 'team_id', 'league_id', 'nation_name')
        id_value: Value to identify the entity
        elo_dict: Dictionary of updated ELO ratings with column names as keys
    
    Returns:
        Boolean indicating success
    """
    cursor = conn.cursor()
    
    # Build the SET clause for the UPDATE statement
    set_clause = ", ".join([f"{col} = ?" for col in elo_dict.keys()])
    values = list(elo_dict.values())
    
    # Add the WHERE condition value
    values.append(id_value)
    
    # Build and execute the UPDATE query
    query = f"UPDATE {table_name} SET {set_clause} WHERE {id_column} = ?"
    
    try:
        cursor.execute(query, values)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating ELO ratings in {table_name}: {e}")
        conn.rollback()
        return False

# Wrapper functions for common entity types
def update_club_elo(conn, team_id, elo_dict):
    """Update club ELO ratings in the database"""
    return update_entity_elo(conn, 'club_elo_ratings', 'team_id', team_id, elo_dict)

def update_league_elo(conn, league_id, elo_dict):
    """Update league ELO ratings in the database"""
    return update_entity_elo(conn, 'league_elo_ratings', 'league_id', league_id, elo_dict)

def update_nation_elo(conn, nation_name, elo_dict):
    """Update nation ELO ratings in the database"""
    return update_entity_elo(conn, 'nation_elo_ratings', 'nation_name', nation_name, elo_dict)

def calculate_elo_ratings(conn, home_score, away_score, home_elos, away_elos, 
                       column_pattern, k_values, match_info, league_counts,
                       ):
    """
    Update ELO ratings for specific column pattern
    
    Args:
        conn: Database connection
        home_score: Home team score
        away_score: Away team score
        home_elos: Dictionary of home ELO values
        away_elos: Dictionary of away ELO values
        column_pattern: Pattern to match in column names (e.g., 'nation_elo_K')
        k_values: List of K-values to use
        match_info: Match information for logging
        league_counts: Dictionary of league counts
    Returns:
        Tuple of (updated_home_elos, updated_away_elos)
    """
    home_elo_updates = home_elos.copy()
    away_elo_updates = away_elos.copy()

    home_wins, draw_wins, away_wins, count = league_counts

    probability_home_win = home_wins / (home_wins + draw_wins + away_wins)
    probability_away_win = away_wins / (home_wins + draw_wins + away_wins)
    probability_draw = draw_wins / (home_wins + draw_wins + away_wins)

    k_draw_parameter = probability_draw / math.sqrt(probability_home_win * probability_away_win)
    eta_home_advantage = math.log10(probability_home_win / probability_away_win)

    print(f"k_draw_parameter: {k_draw_parameter}, eta_home_advantage: {eta_home_advantage}")

    for k in k_values:
        column_name = f'{column_pattern}{k}'
        
        # Check if the column exists in both dictionaries
        if column_name in home_elos and column_name in away_elos:
            # Get new ELOs
            home_elo_new, away_elo_new = elo_davidson_formula(
                conn, 
                home_score, 
                away_score, 
                home_elos[column_name], 
                away_elos[column_name], 
                k, 
                match_info,
                k_draw_parameter,
                eta_home_advantage
            )
            
            # Update the dictionaries
            home_elo_updates[column_name] = home_elo_new
            away_elo_updates[column_name] = away_elo_new
    
    return home_elo_updates, away_elo_updates



# This function was used in the setup to determine the home advantage bias, but is no longer necessary (after we have established the home advantage is +14 elo points)
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


def update_counter_table(conn, competition_id, result, lambda_val=0.99):
    """Update counters with nation information and exponential decay."""
    cursor = conn.cursor()
    result = result.lower()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Upsert for specific competition
    cursor.execute("""
        INSERT INTO counter_table (competition_id, home_wins, draw_wins, away_wins, count, last_updated)
        VALUES (?, 0, 0, 0, 0, ?)
        ON CONFLICT(competition_id) DO UPDATE SET
            home_wins = home_wins * ? + CASE WHEN ? = 'home' THEN 1 ELSE 0 END,
            draw_wins = draw_wins * ? + CASE WHEN ? = 'draw' THEN 1 ELSE 0 END,
            away_wins = away_wins * ? + CASE WHEN ? = 'away' THEN 1 ELSE 0 END,
            count = count + 1,
            last_updated = excluded.last_updated
    """, (competition_id, now,
          lambda_val, result,
          lambda_val, result,
          lambda_val, result))

    # Update combined leagues (without nation)
    cursor.execute("""
        INSERT INTO counter_table (competition_id, home_wins, draw_wins, away_wins, count, last_updated)
        VALUES ('combined_leagues', 0, 0, 0, 0, ?)
        ON CONFLICT(competition_id) DO UPDATE SET
            home_wins = home_wins * ? + CASE WHEN ? = 'home' THEN 1 ELSE 0 END,
            draw_wins = draw_wins * ? + CASE WHEN ? = 'draw' THEN 1 ELSE 0 END,
            away_wins = away_wins * ? + CASE WHEN ? = 'away' THEN 1 ELSE 0 END,
            count = count + 1,
            last_updated = excluded.last_updated
    """, (now,
          lambda_val, result,
          lambda_val, result,
          lambda_val, result))

    conn.commit()
    cursor.close()

def get_counts(conn, index, get_nation=False):
    """Get aggregated counts for a competition or nation."""
    cursor = conn.cursor()
    
    # Direct competition lookup
    cursor.execute("""
            SELECT home_wins, draw_wins, away_wins, count 
            FROM counter_table 
            WHERE competition_id = ?
    """, (index,))
        
    result = cursor.fetchone()
    if result and result[3] > 200:  # Check count > 0
        return result
    else:
        cursor.execute("""
                SELECT home_wins, draw_wins, away_wins, count 
                FROM counter_table 
                WHERE competition_id = 'combined_leagues'
            """)
        return cursor.fetchone()

if __name__ == "__main__":
    pass