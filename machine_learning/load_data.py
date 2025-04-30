import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer, make_column_transformer
from sklearn.preprocessing import OneHotEncoder, LabelEncoder
from xgboost import XGBClassifier

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
    # Load all data
    df = load_csv_data('data/sportradar/processed/elo_features.csv')
    form_df = load_csv_data('data/sportradar/processed/form_features.csv')
    formation_df = load_csv_data('data/sportradar/processed/formation_features.csv')

    # Merge data
    merged = df.merge(
        form_df,
        on='match_id',
        how='inner'
    ).merge(
        formation_df[['match_id', 'home_team_formation', 'away_team_formation']],
        on='match_id',
        how='inner'
    )

    # Create result column
    merged['result'] = np.where(
        merged['home_team_score'] > merged['away_team_score'], 'home_win',
        np.where(merged['home_team_score'] < merged['away_team_score'], 'away_win', 'draw')
    )

    if remove_draws:
        merged = merged[merged['result'] != 'draw']

    # Prepare features
    X = merged.drop(columns=[
        'match_id', 'home_team_id', 'away_team_id',
        'home_team_score', 'away_team_score', 
        'k_draw_parameter', 'eta_home_advantage', 'result'
    ])
    
    # One-hot encode formations
    preprocessor = make_column_transformer(
        (OneHotEncoder(handle_unknown='ignore'), ['home_team_formation', 'away_team_formation']),
        remainder='passthrough',
        verbose_feature_names_out=False
    )
    
    X = preprocessor.fit_transform(X)
    X = pd.DataFrame(X, columns=preprocessor.get_feature_names_out())
    
    print(f"Final feature matrix shape: {X.shape}")
    
    y = merged['result']
    
    # X, le = feature_reduction(X, y, top_n=300)  # Keep 25 non-formation + all formations
    # print(f"Selected features: {X.columns.tolist()}")
    
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


def feature_reduction(X, y, top_n=300):
    # Encode labels
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    
    # Identify formation features
    formation_features = [col for col in X.columns if 'formation' in col]
    
    # Train model with encoded labels
    model = XGBClassifier()
    model.fit(X, y_encoded)
    
    # Get non-formation importances
    non_formation_cols = X.columns.difference(formation_features)
    non_formation_importances = model.feature_importances_[~X.columns.isin(formation_features)]
    
    # Select top N non-formation features
    top_non_formation = non_formation_cols[np.argsort(non_formation_importances)[-top_n:]]
    
    # Combine with formation features
    selected = list(top_non_formation) + formation_features
    
    return X[selected], le