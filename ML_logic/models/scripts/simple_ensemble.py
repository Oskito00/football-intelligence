import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import cross_val_predict, StratifiedKFold

from ML_logic.feature_analysis.visualisation.plot_model_comparison import plot_classification_metrics, plot_model_comparison
from ML_logic.helpers.helpers import create_data_splits, perform_cross_validation, perform_cross_validation_with_metrics

def train_simple_ensemble_model(basic_features_path="Data/processed/preprocessed_basic_features.csv",
                        advanced_features_path="Data/processed/preprocessed_features.csv",
                        train_size=400, dev_size=150, test_size=150):
    """Train basic and advanced models and combine predictions using cross-validation"""
    
    # Load data
    basic_df = pd.read_csv(basic_features_path)
    advanced_df = pd.read_csv(advanced_features_path)
    top_non_redundant_features = [
        'match_importance',
        'home_elo_rating',
        'elo_rating_difference',
        'home_team_overall_strength',
        'goals_conceded_difference',
        'shot_accuracy_difference',
        'average_home_goals_conceded',
        'conversion_rate_difference',
        'h2h_goals_difference',
        'competition_id'
    ]
    advanced_df_non_redunant_features = [
        'home_team_overall_strength',
        'shot_accuracy_difference',
        'conversion_rate_difference',
        'h2h_goals_difference',
    ]
    # Define metadata columns
    metadata_columns = ['start_time', 'home_team', 'away_team', 'home_goals', 'away_goals']

    # Keep only top features in both dataframes and separate metadata columns
    basic_df = basic_df[metadata_columns + [col for col in top_non_redundant_features if col in basic_df.columns]]
    advanced_df = advanced_df[metadata_columns + [col for col in top_non_redundant_features if col in advanced_df.columns]]

    print("Columns in basic_df:", basic_df.columns.tolist())
    print("Columns in advanced_df:", advanced_df.columns.tolist())
    print(f"Number of columns in distilled basic_df: {basic_df.shape[1]}")
    print(f"Number of columns in distilled advanced_df: {advanced_df.shape[1]}")

    # Add outcome column to both dataframes
    basic_df["outcome"] = [2 if h > a else (1 if h == a else 0) 
                          for h, a in zip(basic_df["home_goals"], basic_df["away_goals"])]
    advanced_df["outcome"] = [2 if h > a else (1 if h == a else 0) 
                            for h, a in zip(advanced_df["home_goals"], advanced_df["away_goals"])]
    
    # Use all of basic_df as training data
    train_basic = basic_df
    # Create data splits for advanced_df
    train_advanced, dev_advanced, test_advanced = create_data_splits(advanced_df, test_size)

    # Extract features and labels, removing metadata columns
    X_train_basic = train_basic.drop(columns=metadata_columns + ['home_goals', 'away_goals', 'outcome'])
    y_train_basic = train_basic['outcome']

    X_train_advanced = train_advanced.drop(columns=metadata_columns + ['home_goals', 'away_goals', 'outcome'])
    y_train_advanced = train_advanced['outcome']
    X_dev_advanced = dev_advanced.drop(columns=metadata_columns + ['home_goals', 'away_goals', 'outcome'])
    y_dev_advanced = dev_advanced['outcome']

    # Standardize features
    scaler = StandardScaler()
    X_train_basic = scaler.fit_transform(X_train_basic)
    X_train_advanced = scaler.fit_transform(X_train_advanced)
    X_dev_basic = scaler.fit_transform(X_dev_advanced.drop(columns=advanced_df_non_redunant_features))
    X_dev_advanced = scaler.fit_transform(X_dev_advanced)

    # Define cross-validation strategy
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    # Train basic model with cross-validation
    basic_model = LogisticRegression(max_iter=1000, multi_class='multinomial', solver='lbfgs')
    basic_model.fit(X_train_basic, y_train_basic)
    basic_predictions = cross_val_predict(basic_model, X_dev_basic, y_dev_advanced, cv=cv, method='predict_proba')

    # Train advanced model with cross-validation
    advanced_model = LogisticRegression(max_iter=1000, multi_class='multinomial', solver='lbfgs')
    advanced_model.fit(X_train_advanced, y_train_advanced)
    advanced_predictions = cross_val_predict(advanced_model, X_dev_advanced, y_dev_advanced, cv=cv, method='predict_proba')
    # Ensemble predictions
    ensemble_predictions = (basic_predictions + advanced_predictions) / 2
    ensemble_pred_labels = np.argmax(ensemble_predictions, axis=1)
    
    # Evaluate models
    print("Basic Model Classification Report:")
    print(classification_report(y_dev_advanced, np.argmax(basic_predictions, axis=1)))
    print("Advanced Model Classification Report:")
    print(classification_report(y_dev_advanced, np.argmax(advanced_predictions, axis=1)))
    print("Ensemble Model Classification Report:")
    print(classification_report(y_dev_advanced, ensemble_pred_labels))
    
    # Compare ensemble predictions with actual y values
    comparison_df = pd.DataFrame({
        'Actual': y_dev_advanced,
        'Ensemble_Predicted': ensemble_pred_labels
    })
    print(comparison_df)
    
    # Calculate and print dev set accuracy for ensemble model
    dev_accuracy_ensemble = accuracy_score(y_dev_advanced, ensemble_pred_labels)
    print(f"Ensemble Dev Set Accuracy (Ensemble Model): {dev_accuracy_ensemble:.4f}")

    train_basic_predictions = basic_model.predict(X_train_basic)
    train_advanced_predictions = advanced_model.predict(X_train_advanced)
    train_basic_accuracy = accuracy_score(y_train_basic, train_basic_predictions)
    train_advanced_accuracy = accuracy_score(y_train_advanced, train_advanced_predictions)

    # Calculate and print dev set accuracy for basic and advanced models
    dev_basic_accuracy = accuracy_score(y_dev_advanced, np.argmax(basic_predictions, axis=1))
    dev_advanced_accuracy = accuracy_score(y_dev_advanced, np.argmax(advanced_predictions, axis=1))
    print(f"Train Set Accuracy (Basic Model): {train_basic_accuracy:.4f}")
    print(f"Train Set Accuracy (Advanced Model): {train_advanced_accuracy:.4f}")
    print(f"Dev Set Accuracy (Basic Model): {dev_basic_accuracy:.4f}")
    print(f"Dev Set Accuracy (Advanced Model): {dev_advanced_accuracy:.4f}")


    return 0

if __name__ == "__main__":
    train_simple_ensemble_model()