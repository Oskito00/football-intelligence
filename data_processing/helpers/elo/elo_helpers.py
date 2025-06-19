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

def get_bulk_entity_elos(conn, table_name, id_column, id_values, team_name_map=False):
    """
    Bulk fetch existing ELO ratings for a list of IDs.
    Initializes missing entries in memory with default values.

    Returns:
        dict of {id_value: {elo_column: value, 'team_name': name (optional)}}
    """
    cursor = conn.cursor()

    # 1. Get ELO columns
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s
    """, (table_name,))
    all_columns = [row["column_name"] for row in cursor.fetchall()]
    elo_columns = [col for col in all_columns if "elo" in col.lower()]

    if not elo_columns:
        raise ValueError(f"No ELO columns found in table {table_name}")

    if not id_values:
        return {}

    # 2. Fetch existing ELOs
    placeholders = ', '.join(['%s'] * len(id_values))
    query = f"""    
        SELECT {id_column}, {', '.join(elo_columns)}
        FROM {table_name}
        WHERE {id_column} IN ({placeholders})  -- assuming first column is the unique identifier
    """
    cursor.execute(query, id_values)
    results = cursor.fetchall()

    # 3. Parse results into dict
    elos_by_id = {}
    for row in results:
        entity_id = row[id_column]
        elos_by_id[entity_id] = {col: row[col] for col in elo_columns}

    # 4. Fill in missing IDs with default ELOs and optionally team names
    default_rating = 1500
    default_elo = {col: default_rating for col in elo_columns}

    for i, entity_id in enumerate(id_values):
        if entity_id not in elos_by_id:
            elos_by_id[entity_id] = default_elo.copy()
        if team_name_map:
            elos_by_id[entity_id]["team_name"] = team_name_map[entity_id]
    return elos_by_id
    
def bulk_upsert_entity_elos(conn, table_name, id_column, elos_dict):
    """
    Bulk upsert ELO ratings for entities (clubs, leagues, nations) into the specified table.
    
    Args:
        conn: Database connection
        table_name: Table to update (e.g. 'club_elo_ratings')
        id_column: Identifier column name (e.g. 'team_id')
        elos_dict: Dict mapping id_value -> dict of {column_name: value}
        
    Returns:
        Boolean indicating success
    """
    if not elos_dict:
        return True  # Nothing to do

    cursor = conn.cursor()
    
    # Extract all columns to update (assuming all dicts have the same keys)
    # Add the id_column at the start for the insert columns
    example_elo = next(iter(elos_dict.values()))
    columns = [id_column] + list(example_elo.keys())
    
    # Build the VALUES part as (%s, %s, ..., %s) tuples
    values = []
    for id_value, elo_data in elos_dict.items():
        row = [id_value] + [elo_data[col] for col in example_elo.keys()]
        values.append(row)
    
    # Build the placeholder string e.g. (%s, %s, %s)
    placeholders = "(" + ", ".join(["%s"] * len(columns)) + ")"
    all_placeholders = ", ".join([placeholders] * len(values))
    
    # Flatten the values list for execute
    flat_values = [item for sublist in values for item in sublist]
    
    # Build the ON CONFLICT update set clause (skip id_column)
    set_clause = ", ".join([f"{col} = EXCLUDED.{col}" for col in columns if col != id_column])
    
    query = f"""
        INSERT INTO {table_name} ({", ".join(columns)})
        VALUES {all_placeholders}
        ON CONFLICT ({id_column}) DO UPDATE SET
        {set_clause}
    """ 
    try:
        cursor.execute(query, flat_values)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error bulk upserting ELO ratings in {table_name}: {e}")
        conn.rollback()
        return False

def save_updated_elos_bulk(conn, club_elos, nation_elos, league_elos, continent_elos):
    success_club = bulk_upsert_entity_elos(conn, "club_elo_ratings", "team_id", club_elos)
    if not success_club:
        print("Failed to bulk update club ELOs")

    success_nation = bulk_upsert_entity_elos(conn, "nation_elo_ratings", "nation_name", nation_elos)
    if not success_nation:
        print("Failed to bulk update nation ELOs")

    success_league = bulk_upsert_entity_elos(conn, "league_elo_ratings", "league_id", league_elos)
    if not success_league:
        print("Failed to bulk update league ELOs")
    
    success_continent = bulk_upsert_entity_elos(conn, "continent_elo_ratings", "continent_name", continent_elos)
    if not success_continent:
        print("Failed to bulk update continent ELOs")

    return success_club and success_nation and success_league and success_continent

    
def build_elo_history_record(match_id, start_time, home_team_id, away_team_id, home_team_name, away_team_name,
                              home_club_elos, away_club_elos, 
                              home_nation_elos, away_nation_elos,
                              home_league_elos, away_league_elos,
                              home_continent_elos, away_continent_elos,
                              home_score, away_score,
                              k_draw_parameter, eta_home_advantage):
    """
    Build a dict representing ELO history for a single match.
    To be passed to save_elo_history_bulk().
    """

    data = {
        'match_id': match_id,
        'start_time': start_time,
        'home_team_id': home_team_id,
        'away_team_id': away_team_id,
        'home_team_name': home_team_name,
        'away_team_name': away_team_name,
        'k_draw_parameter': k_draw_parameter,
        'eta_home_advantage': eta_home_advantage,
        'home_team_score': home_score,
        'away_team_score': away_score,
    }

    # Club ELOs
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

    # League ELOs (renamed)
    if home_league_elos:
        for col, val in home_league_elos.items():
            league_col = col.replace('league_', 'team_league_')
            data[f'home_{league_col}'] = val
    if away_league_elos:
        for col, val in away_league_elos.items():
            league_col = col.replace('league_', 'team_league_')
            data[f'away_{league_col}'] = val
    
    # Continent ELOs
    if home_continent_elos:
        for col, val in home_continent_elos.items():
            continent_col = col.replace('continent_', 'team_continent_')
            data[f'home_{continent_col}'] = val
    if away_continent_elos:
        for col, val in away_continent_elos.items():
            continent_col = col.replace('continent_', 'team_continent_')
            data[f'away_{continent_col}'] = val

    return data

def save_elo_history_bulk(conn, elo_history_list):
    """
    Save a list of elo history records to the elo_history table in bulk.
    Each record should be a dict matching the schema, as returned by build_elo_history_record().
    """

    if not elo_history_list:
        return  # nothing to do

    cursor = conn.cursor()

    # Get the table column names in correct order
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'elo_history'
        ORDER BY ordinal_position
    """)
    table_columns = [row["column_name"] for row in cursor.fetchall()]

    # Prepare bulk insert data
    rows_to_insert = []
    for record in elo_history_list:
        row = [record.get(col, 1500) for col in table_columns]  # Default to 1500 if missing
        rows_to_insert.append(row)

    # Build query
    placeholders = ', '.join(['%s'] * len(table_columns))
    columns_str = ', '.join(table_columns)
    insert_query = f"""
        INSERT INTO elo_history ({columns_str}) 
        VALUES ({placeholders})
    """

    # Execute
    cursor.executemany(insert_query, rows_to_insert)
    conn.commit()

def save_elo_future_bulk(conn, elo_history_list):
    """
    Save a list of elo history records to the elo_history table in bulk.
    Each record should be a dict matching the schema, as returned by build_elo_history_record().
    """

    if not elo_history_list:
        return  # nothing to do

    cursor = conn.cursor()

    # Get the table column names in correct order
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'elo_future'
        ORDER BY ordinal_position
    """)
    table_columns = [row["column_name"] for row in cursor.fetchall()]

    # Prepare bulk insert data
    rows_to_insert = []
    for record in elo_history_list:
        row = [record.get(col, 1500) for col in table_columns]  # Default to 1500 if missing
        rows_to_insert.append(row)

    # Build query
    placeholders = ', '.join(['%s'] * len(table_columns))
    columns_str = ', '.join(table_columns)
    insert_query = f"""
        INSERT INTO elo_future ({columns_str}) 
        VALUES ({placeholders})
    """

    # Execute
    cursor.executemany(insert_query, rows_to_insert)
    conn.commit()

def save_updated_counts(conn, counts_dict, decay_lambda=0.99):
    """
    Bulk upsert counts into counter_table applying a decay factor to old values before adding new.
    
    Args:
        conn: Database connection
        counts_dict: Dict mapping competition_id -> {'home_wins': int, 'draw_wins': int, 'away_wins': int, 'count': int}
        decay_lambda: Float between 0 and 1 to discount old counts (1.0 means no decay)
    
    Returns:
        Boolean indicating success
    """
    if not counts_dict:
        return True  # Nothing to do
    
    cursor = conn.cursor()
    
    columns = ['competition_id', 'home_wins', 'draw_wins', 'away_wins', 'count']
    
    values = []
    for comp_id, data in counts_dict.items():
        values.append([
            comp_id,
            data.get('home_wins', 0),
            data.get('draw_wins', 0),
            data.get('away_wins', 0),
            data.get('count', 0),
        ])
    
    placeholders = "(" + ", ".join(["%s"] * len(columns)) + ")"
    all_placeholders = ", ".join([placeholders] * len(values))
    flat_values = [item for sublist in values for item in sublist]
    
    set_clause = ", ".join(
        f"{col} = EXCLUDED.{col}"
        for col in columns if col != 'competition_id'
    )
    
    query = f"""
        INSERT INTO counter_table ({", ".join(columns)})
        VALUES {all_placeholders}
        ON CONFLICT (competition_id) DO UPDATE SET
        {set_clause}
    """
    
    try:
        cursor.execute(query, flat_values)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error bulk upserting counts with decay in counter_table: {e}")
        conn.rollback()
        return False

def get_counts(conn, league_ids, get_nation=False, decay_lambda=0.99):
    """
    Return match result counts for each league_id in league_ids,
    plus a special 'combined_leagues' entry.
    Missing leagues or combined_leagues get zeroed counts (in memory only).
    Applies a decay factor to all counts when reading from the database.

    Args:
        conn: Database connection (with RealDictCursor)
        league_ids: List of competition IDs (str or int)
        get_nation: Placeholder for future logic (unused)
        decay_lambda: Float between 0 and 1 to discount counts (default: 0.99)

    Returns:
        dict: {league_id: {'home_wins': int, 'draw_wins': int, 'away_wins': int, 'count': int}, ..., 'combined_leagues': {...}}
    """
    cursor = conn.cursor()

    # Normalize league_ids to strings for querying and dict keys
    league_ids_str = [str(lid) for lid in league_ids]

    # Build placeholders for SQL IN clause
    placeholders = ', '.join(['%s'] * len(league_ids_str))
    # Apply decay to all count columns in the SELECT statement
    query = f"""
        SELECT 
            competition_id, 
            home_wins * {decay_lambda} as home_wins, 
            draw_wins * {decay_lambda} as draw_wins, 
            away_wins * {decay_lambda} as away_wins, 
            count * {decay_lambda} as count
        FROM counter_table
        WHERE competition_id IN ({placeholders})
    """
    cursor.execute(query, league_ids_str)
    results = cursor.fetchall()

    # Build dict with string keys (str of competition_id)
    counts_by_league = {
        str(row['competition_id']): {
            'home_wins': row['home_wins'],
            'draw_wins': row['draw_wins'],
            'away_wins': row['away_wins'],
            'count': row['count']
        }
        for row in results
    }

    # Fill missing leagues with zeros using string keys
    for league_id in league_ids_str:
        if league_id not in counts_by_league:
            counts_by_league[league_id] = {
                'home_wins': 0,
                'draw_wins': 0,
                'away_wins': 0,
                'count': 0
            }

    # Fetch combined_leagues counts separately (key is always string)
    # Apply decay to combined leagues counts as well
    cursor.execute(f"""
        SELECT 
            competition_id, 
            home_wins * {decay_lambda} as home_wins, 
            draw_wins * {decay_lambda} as draw_wins, 
            away_wins * {decay_lambda} as away_wins, 
            count * {decay_lambda} as count
        FROM counter_table
        WHERE competition_id = 'combined_leagues'
    """)
    combined_row = cursor.fetchone()

    if combined_row:
        counts_by_league['combined_leagues'] = {
            'home_wins': combined_row['home_wins'],
            'draw_wins': combined_row['draw_wins'],
            'away_wins': combined_row['away_wins'],
            'count': combined_row['count']
        }
    else:
        counts_by_league['combined_leagues'] = {
            'home_wins': 1,
            'draw_wins': 1,
            'away_wins': 1,
            'count': 3
        }

    return counts_by_league