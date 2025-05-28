import pandas as pd
import numpy as np
from sklearn.compose import make_column_transformer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder

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

def prepare_data(k_fold=10, remove_draws=False, training_data_filter=None, test_year=None, test_competition_id=None):
    # Load all data
    df = load_csv_data('data/api_football/processed/elo_features.csv')
    # form_df = load_csv_data('data/api_football/processed/form_features.csv')
    match_info_df = load_csv_data('data/api_football/processed/match_info_features.csv')
    formation_df = load_csv_data('data/api_football/processed/formation_features.csv')
    stage_of_season_df = load_csv_data('data/api_football/processed/stage_of_season_features.csv')
    stage_of_season_df.drop(columns=['start_time','season_start_date','season_end_date'], inplace=True)
    league_standings_df = load_csv_data('data/api_football/processed/league_standings_features.csv')

    # Merge data
    merged = df.merge(
        match_info_df,
        on='match_id',
        how='inner'
    ).merge(
        formation_df[['match_id', 'home_team_formation', 'away_team_formation']],
        on='match_id',
        how='inner'
    ).merge(
        stage_of_season_df,
        on='match_id',
        how='inner'
    ).merge(
        league_standings_df,
        on='match_id',
        how='inner'
    ) # All of these actually reduce the accuracy of the model
    print("Length of merged data:", len(merged))

    # Create result column
    merged['result'] = np.where(
        merged['home_team_score'] > merged['away_team_score'], 'home_win',
        np.where(merged['home_team_score'] < merged['away_team_score'], 'away_win', 'draw')
    )

    # Only convert competition_id to categorical (XGBoost can handle this)
    merged['competition_id'] = merged['competition_id'].astype('category')
    
    if remove_draws:
        merged = merged[merged['result'] != 'draw']

    # Prepare formation features    
    preprocessor = make_column_transformer(
        (OneHotEncoder(handle_unknown='ignore'), ['home_team_formation', 'away_team_formation']),
        remainder='passthrough',
        verbose_feature_names_out=False
    )


    # Fit on ALL data to learn all possible formation categories
    merged = preprocessor.fit_transform(merged)

    #convert to dataframe
    merged = pd.DataFrame(merged, columns=preprocessor.get_feature_names_out())

    
    # 2. Now split into train/test
    if training_data_filter:
        print("Filtering data for test competition and year")
        print("Length of data before filtering:", len(merged))
        merged = merged[merged['competition_id'].astype('category').isin(training_data_filter)]
        print("Length of filtered data by competitions:", len(merged))
        if test_competition_id and test_year:
            training_data = merged[merged['competition_id'].astype('category') != test_competition_id]
            print("Length of training data:", len(training_data))
            test_data = merged[merged['competition_id'].astype('category') == test_competition_id]
            print("Length of test data:", len(test_data))

            #filter every year before test_year
            training_data = training_data[training_data['competition_season_name'] < test_year]
            test_data = test_data[test_data['competition_season_name'] == test_year]
            print("Length of training data after filtering by year:", len(training_data))
            print("Length of test data after filtering by year:", len(test_data))

            X_train = training_data.drop(columns=['result'])

            y_train = training_data['result']

            X_test = test_data.drop(columns=['result'])

            y_test = test_data['result']
        
            # 4. Convert to numeric
            X_train = X_train.apply(pd.to_numeric, errors='ignore')
            X_test = X_test.apply(pd.to_numeric, errors='ignore')
        
            # Ensure categorical columns remain categorical right before returning
            if 'stage_of_season_category' in X_train.columns:
                X_train['stage_of_season_category'] = X_train['stage_of_season_category'].astype('category')
                X_test['stage_of_season_category'] = X_test['stage_of_season_category'].astype('category')
        
            return X_train, y_train, X_test, y_test
    
    X = merged.drop(columns=['result'])
    
    y = merged['result']

    #split into training, test and dev data
    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.2, random_state=20)
    X_dev, X_test, y_dev, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=20)

    # 4. Convert to numeric
    X_train = X_train.apply(pd.to_numeric, errors='ignore')
    X_dev = X_dev.apply(pd.to_numeric, errors='ignore')
    X_test = X_test.apply(pd.to_numeric, errors='ignore')
    
    # Ensure categorical columns remain categorical right before returning
    if 'stage_of_season_category' in X_train.columns:
        X_train['stage_of_season_category'] = X_train['stage_of_season_category'].astype('category')
        X_dev['stage_of_season_category'] = X_dev['stage_of_season_category'].astype('category')
        X_test['stage_of_season_category'] = X_test['stage_of_season_category'].astype('category')
    
    print("Columns right before processing:", X_train.columns)

    return X_train, y_train, X_dev, y_dev, X_test, y_test

def analyze_feature_importance(model, X, top_n=20):
    """
    Analyze and display feature importance from a trained XGBoost model.
    
    Args:
        model: Trained XGBoost model
        X: Feature DataFrame (to get column names)
        top_n: Number of top features to display
        
    Returns:
        DataFrame with feature importance values
    """
    # Get feature importance scores using gain
    importance_dict = model.get_booster().get_score(importance_type='gain')
    
    # Convert to DataFrame for better visualization
    importance_df = pd.DataFrame({
        'Feature': list(importance_dict.keys()),
        'Gain': list(importance_dict.values())
    })
    importance_df = importance_df.sort_values('Gain', ascending=False)
    
    # Calculate percentage
    importance_df['Percentage'] = importance_df['Gain'] / importance_df['Gain'].sum() * 100
    
    # Display all features
    print("\n===== ALL FEATURES BY IMPORTANCE =====")
    pd.set_option('display.max_rows', None)  # Ensure all rows are displayed
    print(importance_df)
    pd.reset_option('display.max_rows')  # Reset to default setting
    
    # Analyze competition features specifically
    competition_features = [f for f in importance_df['Feature'] if 'competition' in f]
    if competition_features:
        print("\n===== COMPETITION FEATURE IMPORTANCE =====")
        comp_df = importance_df[importance_df['Feature'].isin(competition_features)]
        print(comp_df)
        print(f"Total competition feature importance: {comp_df['Percentage'].sum():.2f}%")
    
    # Analyze formation features if they exist
    formation_features = [f for f in importance_df['Feature'] if 'formation' in f]
    if formation_features:
        print("\n===== FORMATION FEATURE IMPORTANCE =====")
        form_df = importance_df[importance_df['Feature'].isin(formation_features)]
        print(form_df)
        print(f"Total formation feature importance: {form_df['Percentage'].sum():.2f}%")
    
    return importance_df