from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, KFold
from sklearn.metrics import accuracy_score, classification_report
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def multi_label_logistic_regression(n_folds=10):
    """Train a 3-class classifier with k-fold cross validation"""
    
    # Load and prepare data
    advanced_df = pd.read_csv("Data/processed/preprocessed_features.csv")
    basic_df = pd.read_csv("Data/processed/preprocessed_basic_features.csv")

    # Check for missing features
    basic_features = basic_df.columns
    advanced_features = advanced_df.columns
    missing_features = set(advanced_features) - set(basic_features)
    print(f"Missing features in preprocessed_features: {missing_features}")
    if missing_features:
        print("List of missing features:")
        for feature in missing_features:
            print(f"- {feature}")

    advanced_df["outcome"] = [2 if h > a else (1 if h == a else 0) 
                    for h, a in zip(advanced_df["home_goals"], advanced_df["away_goals"])]
    
    # First split off test set
    train_dev_data, _, test_data = create_data_splits(advanced_df, test_size=100)
    
    # Setup k-fold cross validation on train+dev data
    kf = KFold(n_splits=n_folds, shuffle=True, random_state=40)
    metadata_cols = ["start_time", "home_team", "away_team", "home_goals", "away_goals", "outcome"]
    print(f"Number of features: {len(train_dev_data.drop(columns=metadata_cols).columns)}")

    
    # Lists to store results
    fold_train_scores = []
    fold_val_scores = []
    all_feature_importances = []
    
    # Perform k-fold cross validation on train+dev data
    for fold, (train_idx, val_idx) in enumerate(kf.split(train_dev_data), 1):
        print(f"\nFold {fold}/{n_folds}")
        
        # Split data
        train_data = train_dev_data.iloc[train_idx]
        val_data = train_dev_data.iloc[val_idx]
        
        # Prepare features
        X_train = train_data.drop(columns=metadata_cols)
        feature_names = X_train.columns
        y_train = train_data["outcome"]
        X_val = val_data.drop(columns=metadata_cols)
        y_val = val_data["outcome"]
        
        # Scale features
        scaler = StandardScaler()
        X_train = pd.DataFrame(scaler.fit_transform(X_train), columns=feature_names)
        X_val = pd.DataFrame(scaler.transform(X_val), columns=feature_names)
        
        # Train model
        model = LogisticRegression(multi_class='multinomial', solver='lbfgs', max_iter=1000)
        model.fit(X_train, y_train)
        
        # Evaluate
        train_preds = model.predict(X_train)
        val_preds = model.predict(X_val)
        
        train_acc = accuracy_score(y_train, train_preds)
        val_acc = accuracy_score(y_val, val_preds)
        
        fold_train_scores.append(train_acc)
        fold_val_scores.append(val_acc)
        
        print(f"Train Accuracy: {train_acc:.3f}")
        print(f"Validation Accuracy: {val_acc:.3f}")
        
        # Store feature importance
        importances = np.abs(model.coef_).mean(axis=0)
        all_feature_importances.append(importances)
    
    # Print average results
    print("\nOverall Results:")
    print(f"Average Train Accuracy: {np.mean(fold_train_scores):.3f} ± {np.std(fold_train_scores):.3f}")
    print(f"Average Validation Accuracy: {np.mean(fold_val_scores):.3f} ± {np.std(fold_val_scores):.3f}")
    
    # Average feature importance across folds
    avg_importances = np.mean(all_feature_importances, axis=0)
    importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance': avg_importances
    }).sort_values('importance', ascending=False)
    
    # Plot average feature importance
    plt.figure(figsize=(12, 8))
    plt.bar(range(20), importance_df['importance'][:20])
    plt.xticks(range(20), importance_df['feature'][:20], rotation=45, ha='right')
    plt.title('Top 20 Most Important Features (Averaged Across Folds)')
    plt.tight_layout()
    plt.show()
    
    print("\nTop 10 Most Important Features (Averaged Across Folds):")
    print(importance_df.head(10))
    
    # After k-fold CV, train final model on all train+dev data
    X_train_dev = train_dev_data.drop(columns=metadata_cols)
    y_train_dev = train_dev_data["outcome"]
    X_test = test_data.drop(columns=metadata_cols)
    y_test = test_data["outcome"]
    
    # Scale features
    scaler = StandardScaler()
    X_train_dev = pd.DataFrame(scaler.fit_transform(X_train_dev), columns=X_train_dev.columns)
    X_test = pd.DataFrame(scaler.transform(X_test), columns=X_test.columns)
    
    # Train final model
    final_model = LogisticRegression(multi_class='multinomial', solver='lbfgs', max_iter=1000)
    final_model.fit(X_train_dev, y_train_dev)
    
    # Evaluate on test set
    test_preds = final_model.predict(X_test)
    test_acc = accuracy_score(y_test, test_preds)
    
    print("\nFinal Test Set Results:")
    print(f"Test Accuracy: {test_acc:.3f}")
    print("\nTest Set Classification Report:")
    print(classification_report(y_test, test_preds, 
                              target_names=['Home Win', 'Draw', 'Away Win']))
    
    analyze_specific_features(importance_df)
    
    return final_model, fold_train_scores, fold_val_scores, importance_df

#****************************************************
#Helper functions
#****************************************************

def create_data_splits(data, test_size=100, random_seed=42):
    """
    Split data into train, dev, and test sets.
    - Test set: Most recent test_size matches
    - Remaining data split randomly into train (80%) and dev (20%)
    
    Args:
        data: Either a pandas DataFrame or a path to a CSV file
        test_size: Number of most recent matches for test set
        random_seed: Random seed for reproducibility
    """
    # Handle input data
    if isinstance(data, str):
        df = pd.read_csv(data)
    else:
        df = data.copy()
    
    # Convert start_time to datetime and sort
    df['start_time'] = pd.to_datetime(df['start_time'])
    df = df.sort_values('start_time')
    
    # Split into historical and test data
    test_data = df.tail(test_size).copy()
    historical_data = df.iloc[:-test_size].copy()
    
    # Randomly split historical data into train and dev
    train_data, dev_data = train_test_split(
        historical_data,
        test_size=0.2,
        random_state=random_seed
    )
    
    print(f"Data split sizes:")
    print(f"Train: {len(train_data)} matches")
    print(f"Dev:   {len(dev_data)} matches")
    print(f"Test:  {len(test_data)} matches")
    print(f"\nTest set date range: {test_data['start_time'].min()} to {test_data['start_time'].max()}")
    
    return train_data, dev_data, test_data

def analyze_feature_importance(model, feature_names):
    """Analyze and plot feature importance"""
    importances = np.abs(model.coef_).mean(axis=0)
    
    # Ensure lengths match
    if len(feature_names) != len(importances):
        raise ValueError(f"Feature names length ({len(feature_names)}) doesn't match importance length ({len(importances)})")
    
    feature_importance = pd.DataFrame({
        'feature': feature_names,
        'importance': importances
    })
    
    # Sort by importance
    feature_importance = feature_importance.sort_values('importance', ascending=False)
    
    # Plot top 20 features
    plt.figure(figsize=(12, 8))
    plt.bar(range(40), feature_importance['importance'][:40])
    plt.xticks(range(40), feature_importance['feature'][:40], rotation=45, ha='right')
    plt.title('Top 40 Most Important Features')
    plt.tight_layout()
    plt.show()
    
    return feature_importance

def analyze_specific_features(importance_df):
    """Analyze importance of specific features"""
    
    features_of_interest = [
        'home_team_midfield_strength', 'away_team_overall_strength',
        'pass_effectiveness_difference', 'home_team_defence_strength',
        'home_team_overall_strength', 'conversion_rate_difference',
        'away_team_attack_strength', 'home_team_gk_strength',
        'shot_accuracy_difference', 'h2h_goals_difference',
        'h2h_avg_draw_rate', 'away_team_midfield_strength',
        'home_team_attack_strength', 'away_team_defence_strength',
        'defensive_success_difference', 'h2h_clean_sheets_difference',
        'form_similarity', 'h2h_points_difference', 'away_team_gk_strength'
    ]
    
    # Filter and sort specific features
    specific_features = importance_df[importance_df['feature'].isin(features_of_interest)]
    specific_features = specific_features.sort_values('importance', ascending=False)
    
    # Plot specific features
    plt.figure(figsize=(12, 8))
    plt.bar(range(len(specific_features)), specific_features['importance'])
    plt.xticks(range(len(specific_features)), specific_features['feature'], rotation=45, ha='right')
    plt.title('Importance of Selected Features')
    plt.tight_layout()
    plt.show()
    
    print("\nRankings of Selected Features:")
    for idx, row in specific_features.iterrows():
        overall_rank = importance_df.index.get_loc(idx) + 1
        print(f"{row['feature']:<30} {row['importance']:.4f} (Rank: {overall_rank})")

if __name__ == "__main__":
    model, train_scores, val_scores, importances = multi_label_logistic_regression()