from datetime import datetime

def calculate_elo_ratings(conn, home_score, away_score, home_elos, away_elos, 
                       column_pattern, k_values, match_info,
                       k_draw_parameter, eta_home_advantage):
    """
    Helper function to setup the infrastructure for the elo_davidson_formula
    Performs calculations for every k value in k_values
    
    Args:
        conn: Database connection
        home_score: Home team score
        away_score: Away team score
        home_elos: Dictionary of home ELO values
        away_elos: Dictionary of away ELO values
        column_pattern: Pattern to match in column names (e.g., 'nation_elo_K')
        k_values: List of K-values to use
        match_info: Match information for logging
        k_draw_parameter: Draw parameter κ
        eta_home_advantage: Home advantage parameter η
    Returns:
        Tuple of (updated_home_elos, updated_away_elos)
    """
    home_elo_updates = home_elos.copy()
    away_elo_updates = away_elos.copy()



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
        else:
            print(f"Column {column_name} not found in both home and away elos")

    return home_elo_updates, away_elo_updates

def elo_davidson_formula(
    conn, home_score, away_score, home_elo, away_elo, 
    k_factor, match_info, k_draw_parameter, eta_home_advantage, sigma=400
):
    """Python implementation of the elo_davidson_formula from the paper "Understanding draws in the Elo Rating Algorithm
    Authored by Leszek Szczecinski and Aymen Djebbi

    Uses k_draw_parameter (prior on draw probability based on competition)
    Uses eta_home_advantage (Dynamically calculated home advantage based on specific competition)
    """
    # --- Parameters ---
    kappa = float(k_draw_parameter)   # Draw parameter κ
    z = float(home_elo - away_elo)    # Base rating difference
    
    # Apply home advantage adjustment if needed
    if eta_home_advantage:
        z += float(eta_home_advantage) * sigma
    
    # --- Determine actual outcome (s_i) ---
    if home_score > away_score:       # Home win
        s_home = 1.0
        s_away = 0.0
    elif home_score < away_score:     # Away win
        s_home = 0.0
        s_away = 1.0
    else:                             # Draw
        s_home = 0.5
        s_away = 0.5
    
    # --- Calculate G(z; κ) from equation (33) ---
    # G(z; κ) = (10^(0.5z/σ) + (1/2)κ) / (10^(0.5z/σ) + 10^(-0.5z/σ) + κ)
    home_strength = 10 ** (0.5 * z / sigma)
    away_strength = 10 ** (-0.5 * z / sigma)
    
    # Calculate G for home team
    G_home = (home_strength + 0.5 * kappa) / (home_strength + away_strength + kappa)
    
    # Calculate G for away team (using -z)
    G_away = (away_strength + 0.5 * kappa) / (home_strength + away_strength + kappa)
    
    # --- Apply the Elo-Davidson update rule from equation (34) ---
    home_elo_new = home_elo + k_factor * (s_home - G_home)
    away_elo_new = away_elo + k_factor * (s_away - G_away)
    
    return home_elo_new, away_elo_new

def get_entity_elo(conn, table_name, id_column, id_value, name_column=None, name_value=None):
    """
    Retrieve or initialize ELO ratings for a given entity (club, league, or nation).
    Compatible with PostgreSQL.
    """
    cursor = conn.cursor()

    # Get column info from information_schema
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s
    """, (table_name,))
    all_columns = [row[0] for row in cursor.fetchall()]

    # Filter for ELO columns
    elo_columns = [col for col in all_columns if "elo" in col.lower()]
    if not elo_columns:
        raise ValueError(f"No ELO columns found in table {table_name}")

    # Build the SELECT query
    select_columns = ", ".join(elo_columns)
    query = f"SELECT {select_columns} FROM {table_name} WHERE {id_column} = %s"
    cursor.execute(query, (id_value,))
    result = cursor.fetchone()

    if result:
        # Entity exists, return ELOs as a dictionary
        return {col: val for col, val in zip(elo_columns, result)}
    else:
        # Entity doesn't exist, create it with default ratings
        default_rating = 1500
        elo_dict = {col: default_rating for col in elo_columns}

        # Build insert components
        insert_columns = [id_column]
        values = [id_value]

        if name_column and name_value:
            insert_columns.append(name_column)
            values.append(name_value)

        insert_columns.extend(elo_columns)
        values.extend([default_rating] * len(elo_columns))

        # Build and run INSERT query
        columns_str = ", ".join(insert_columns)
        placeholders = ", ".join(["%s"] * len(values))
        insert_query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
        cursor.execute(insert_query, values)
        conn.commit()

        return elo_dict
    
def update_entity_elo(conn, table_name, id_column, id_value, elo_dict):
    """
    SET function to update the elos for a particular entity (can be club, league or nation)
    Similar to the function above
    
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
    set_clause = ", ".join([f"{col} = %s" for col in elo_dict.keys()])
    values = list(elo_dict.values())
    
    # Add the WHERE condition value
    values.append(id_value)
    
    # Build and execute the UPDATE query
    query = f"UPDATE {table_name} SET {set_clause} WHERE {id_column} = %s"
    
    try:
        cursor.execute(query, values)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating ELO ratings in {table_name}: {e}")
        conn.rollback()
        return False

def save_elo_history(conn, match_id, home_team_id, away_team_id, 
                     home_club_elos, away_club_elos, 
                     home_nation_elos, away_nation_elos,
                     home_league_elos, away_league_elos,
                     home_score, away_score,
                     k_draw_parameter, eta_home_advantage):
    """
    Save the current elo ratings for a match to the elo_history table.
    """

    cursor = conn.cursor()

    # Use PostgreSQL's information_schema to get column names
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'elo_history'
        ORDER BY ordinal_position
    """)
    table_columns = [row[0] for row in cursor.fetchall()]

    # Base data
    data = {
        'match_id': match_id,
        'home_team_id': home_team_id,
        'away_team_id': away_team_id,
        'k_draw_parameter': k_draw_parameter,
        'eta_home_advantage': eta_home_advantage,
        'home_team_score': home_score,
        'away_team_score': away_score,
    }

    # Add home/away club ELOs
    for col, val in home_club_elos.items():
        data[f'home_team_{col}'] = val
    for col, val in away_club_elos.items():
        data[f'away_team_{col}'] = val

    # Nation ELOs
    if home_nation_elos:
        for col, val in home_nation_elos.items():
            data[f'home_team_{col}'] = val
    if away_nation_elos:
        for col, val in away_nation_elos.items():
            data[f'away_team_{col}'] = val

    # League ELOs
    if home_league_elos:
        for col, val in home_league_elos.items():
            league_col = col.replace('league_', 'team_league_')
            data[f'home_{league_col}'] = val
    if away_league_elos:
        for col, val in away_league_elos.items():
            league_col = col.replace('league_', 'team_league_')
            data[f'away_{league_col}'] = val

    # Build insert data matching column order
    columns = []
    values = []

    for col in table_columns:
        columns.append(col)
        values.append(data.get(col, 1500))  # default to 1500

    placeholders = ', '.join(['%s'] * len(columns))
    columns_str = ', '.join(columns)

    cursor.execute(
        f"INSERT INTO elo_history ({columns_str}) VALUES ({placeholders})",
        values
    )
    conn.commit()

def update_counter_table(conn, competition_id, result, lambda_val=0.99):
    cursor = conn.cursor()
    result = result.lower()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    home_increment_count = 1 if result == 'home' else 0
    draw_increment_count = 1 if result == 'draw' else 0
    away_increment_count = 1 if result == 'away' else 0

    # Insert initial counts based on this match, count=1
    cursor.execute("""
        INSERT INTO counter_table (competition_id, home_wins, draw_wins, away_wins, count, last_updated)
        VALUES (%s, %s, %s, %s, 1, %s)
        ON CONFLICT (competition_id) DO UPDATE SET
            home_wins = counter_table.home_wins * %s + CASE WHEN %s = 'home' THEN 1 ELSE 0 END,
            draw_wins = counter_table.draw_wins * %s + CASE WHEN %s = 'draw' THEN 1 ELSE 0 END,
            away_wins = counter_table.away_wins * %s + CASE WHEN %s = 'away' THEN 1 ELSE 0 END,
            count = counter_table.count + 1,
            last_updated = EXCLUDED.last_updated
    """, (
        competition_id, 
        home_increment_count,
        draw_increment_count,
        away_increment_count,
        now,
        lambda_val, result,
        lambda_val, result,
        lambda_val, result
    ))

    # Same for combined_leagues (initial insert counts set to increments, count=1)
    cursor.execute("""
        INSERT INTO counter_table (competition_id, home_wins, draw_wins, away_wins, count, last_updated)
        VALUES ('combined_leagues', %s, %s, %s, 1, %s)
        ON CONFLICT (competition_id) DO UPDATE SET
            home_wins = counter_table.home_wins * %s + CASE WHEN %s = 'home' THEN 1 ELSE 0 END,
            draw_wins = counter_table.draw_wins * %s + CASE WHEN %s = 'draw' THEN 1 ELSE 0 END,
            away_wins = counter_table.away_wins * %s + CASE WHEN %s = 'away' THEN 1 ELSE 0 END,
            count = counter_table.count + 1,
            last_updated = EXCLUDED.last_updated
    """, (
        home_increment_count,
        draw_increment_count,
        away_increment_count,
        now,
        lambda_val, result,
        lambda_val, result,
        lambda_val, result
    ))

    conn.commit()
    cursor.close()

def get_counts(conn, index, get_nation=False):
    """Function to get the match result counts for a competition or nation
    
    Args:
        conn: Database connection
        index: Competition ID or nation name
        get_nation: Boolean to get nation counts
    """
    cursor = conn.cursor()
    
    # Direct competition lookup
    cursor.execute("""
            SELECT home_wins, draw_wins, away_wins, count 
            FROM counter_table 
            WHERE competition_id = %s
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
        combined_result = cursor.fetchone()
        return combined_result if combined_result else (1, 1, 1, 3)
