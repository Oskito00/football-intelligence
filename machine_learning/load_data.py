import pandas as pd
import numpy as np

def load_csv_data(file_path):
    """Load CSV data into a pandas DataFrame.
    
    Args:
        file_path (str): Path to CSV file
        
    Returns:
        pd.DataFrame: Loaded data or None if error occurs
    """
    try:
        df = pd.read_csv(file_path)
        print(f"Successfully loaded data from {file_path}")
        # print(f"Shape: {df.shape}")
        # print("Columns:", df.columns.tolist())
        return df
    except Exception as e:
        print(f"Error loading {file_path}: {str(e)}")
        return None

def prepare_data(remove_draws=False):
    df = load_csv_data('Data/processed/elo_features.csv')
    form_df = load_csv_data('Data/processed/form_features.csv')

    #add form_df columns to df
    df = df.merge(form_df, on=['match_id'])

    # FIRST create the result column
    df['result'] = np.where(df['home_team_score'] > df['away_team_score'], 'home_win', 
                           np.where(df['home_team_score'] < df['away_team_score'], 'away_win', 'draw'))
    
    if remove_draws:
        df = df[df['result'] != 'draw']

    # THEN drop it from features
    X = df.drop(columns=['match_id', 'home_team_id', 'away_team_id', 
                        'home_team_score', 'away_team_score', 'k_draw_parameter', 'eta_home_advantage', 'result'])
    
    #length of the columns of X
    print(len(X.columns))
    
    y = df['result']

    return X, y

def prepare_goal_data():
    # Load and merge data
    df = load_csv_data('Data/processed/elo_features.csv')
    form_df = load_csv_data('Data/processed/form_features.csv')
    merged_df = df.merge(form_df, on='match_id')
    
    # Prepare features and targets
    X = merged_df.drop(columns=[
        'match_id', 'home_team_id', 'away_team_id',
        'home_team_score', 'away_team_score', 'result',
        'k_draw_parameter', 'eta_home_advantage'
    ])
    
    # Goal targets
    y_home = merged_df['home_team_score']
    y_away = merged_df['away_team_score']
    
    return X, y_home, y_away