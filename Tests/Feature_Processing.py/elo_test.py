import sqlite3
import sys
import os

# Add the project root directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from Tools.elo_helpers import get_club_elo, get_league_elo, get_nation_elo
from Tools.Database_helpers.create_tables import create_club_elo_rating_table, create_league_elo_table, create_nation_elo_table, create_elo_history_table

def save_elo_history(conn, match_id, home_team_id, away_team_id, 
                     home_club_elos, away_club_elos, 
                     home_nation_elos, away_nation_elos,
                     home_league_elos, away_league_elos,
                     home_score, away_score):
    """
    Save the current ELO ratings to the elo_history table
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
    
    # Print data to debug what's happening
    print("\nData prepared for elo_history:")
    for key in sorted(data.keys()):
        print(f"  {key}: {data[key]}")
    
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
    
    print(f"\nSuccessfully saved ELO history for match {match_id}")
    return True

def setup_test_database():
    """Create an in-memory database with test tables and data"""
    print("Setting up in-memory test database...")
    conn = sqlite3.connect(':memory:')
    
    # Create tables
    create_club_elo_rating_table(conn)
    create_league_elo_table(conn)
    create_nation_elo_table(conn)
    create_elo_history_table(conn)
    
    print("Tables created successfully")
    return conn

def test_elo_dictionary_saving():
    """Test that the ELO helpers return dictionaries and can be saved to elo_history"""
    # Create in-memory test database
    conn = setup_test_database()
    
    try:
        # Test with sample data
        home_team_id = "barca"
        away_team_id = "real"
        home_team_name = "Barcelona"
        away_team_name = "Real Madrid"
        
        # Fetch team ELOs (these will be created with default values)
        print("\nFetching team ELOs...")
        home_club_elos = get_club_elo(conn, home_team_id, home_team_name)
        away_club_elos = get_club_elo(conn, away_team_id, away_team_name)
        
        # Print the dictionaries to verify
        print("\nHome Team ELOs:")
        for key in sorted(home_club_elos.keys()):
            print(f"  {key}: {home_club_elos[key]}")
        
        print("\nAway Team ELOs:")
        for key in sorted(away_club_elos.keys()):
            print(f"  {key}: {away_club_elos[key]}")
        
        # Fetch league and nation ELOs
        home_league_id = "es1"
        away_league_id = "es1"
        home_league_name = "LaLiga"
        away_league_name = "LaLiga"
        home_nation = "Spain"
        away_nation = "Spain"
        
        home_league_elos = get_league_elo(conn, home_league_id, home_league_name)
        away_league_elos = get_league_elo(conn, away_league_id, away_league_name)
        home_nation_elos = get_nation_elo(conn, home_nation)
        away_nation_elos = get_nation_elo(conn, away_nation)
        
        print("\nHome League ELOs:")
        for key in sorted(home_league_elos.keys()):
            print(f"  {key}: {home_league_elos[key]}")
            
        print("\nHome Nation ELOs:")
        for key in sorted(home_nation_elos.keys()):
            print(f"  {key}: {home_nation_elos[key]}")
        
        # Test saving to elo_history
        match_id = "test_match_123"
        home_score = 2
        away_score = 1
        
        print("\nSaving to elo_history...")
        result = save_elo_history(
            conn, match_id, home_team_id, away_team_id,
            home_club_elos, away_club_elos,
            home_nation_elos, away_nation_elos,
            home_league_elos, away_league_elos,
            home_score, away_score
        )
        
        # Verify it was saved
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM elo_history WHERE match_id = ?", (match_id,))
        db_result = cursor.fetchone()
        
        if db_result:
            print("\nSuccessfully verified data was saved to elo_history!")
            print(f"Row has {len(db_result)} columns")
            
            # Count how many non-default values we have
            non_default = sum(1 for val in db_result if val != 1500 and val is not None)
            print(f"Non-default values: {non_default}")
            
            # Print a few sample values
            cursor.execute("PRAGMA table_info(elo_history)")
            columns = [col[1] for col in cursor.fetchall()]
            
            print("\nSample values from saved data:")
            for i, (col, val) in enumerate(zip(columns, db_result)):
                if i < 10 or (val != 1500 and val is not None):  # Print first 10 columns and all non-default values
                    print(f"  {col}: {val}")
                    
            assert result is True
            return True
        else:
            print("\nError: Data not saved correctly to elo_history")
            assert False, "Data not saved to elo_history"
            
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"Test failed with error: {e}"
    finally:
        conn.close()
        print("\nTest completed")

if __name__ == "__main__":
    # You can run this directly with python
    test_elo_dictionary_saving()