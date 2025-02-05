import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report

from ML_logic.feature_analysis.visualisation.plot_model_comparison import plot_classification_metrics, plot_model_comparison
from ML_logic.helpers.helpers import create_data_splits, perform_cross_validation, perform_cross_validation_with_metrics

def train_ensemble_models(basic_features_path="Data/processed/preprocessed_basic_features.csv",
                        advanced_features_path="Data/processed/preprocessed_features.csv",
                        train_size=400, dev_size=150, test_size=150):
    """Train basic and advanced models and combine predictions"""
    
    # Load data
    basic_df = pd.read_csv(basic_features_path)
    advanced_df = pd.read_csv(advanced_features_path)
    
    # Add outcome column to both dataframes
    basic_df["outcome"] = [2 if h > a else (1 if h == a else 0) 
                          for h, a in zip(basic_df["home_goals"], basic_df["away_goals"])]
    advanced_df["outcome"] = [2 if h > a else (1 if h == a else 0) 
                            for h, a in zip(advanced_df["home_goals"], advanced_df["away_goals"])]
    
    # Split advanced data
    advanced_df = advanced_df.sort_values('start_time')
    test_data = advanced_df.tail(test_size)
    dev_data = advanced_df.iloc[-(test_size + dev_size):-test_size]
    train_data = advanced_df.iloc[-(test_size + dev_size + train_size):-(test_size + dev_size)]
    
    # Get feature sets
    metadata_cols = ["start_time", "home_team", "away_team", "home_goals", "away_goals", "outcome"]
    basic_features = [col for col in basic_df.columns if col not in metadata_cols]
    advanced_only_features = [col for col in advanced_df.columns 
                            if col not in basic_features and col not in metadata_cols]
    
    print(f"Number of basic features: {len(basic_features)}")
    print(f"Number of advanced-only features: {len(advanced_only_features)}")
    
    # Train basic model on all basic data
    X_basic = basic_df[basic_features]
    y_basic = basic_df["outcome"]
    
    scaler_basic = StandardScaler()
    X_basic_scaled = scaler_basic.fit_transform(X_basic)
    
    basic_model = LogisticRegression(multi_class='multinomial', solver='lbfgs', max_iter=1000)
    basic_model.fit(X_basic_scaled, y_basic)
    
    # Define selected advanced features
    selected_advanced_features = [
        'h2h_points_difference',
        'conversion_rate_difference',
        'shot_accuracy_difference',
        'defensive_success_difference',
        'form_similarity'
    ]
    
    # Train advanced model on selected features only
    X_adv_train = train_data[selected_advanced_features]
    y_adv_train = train_data["outcome"]
    
    scaler_adv = StandardScaler()
    X_adv_train_scaled = scaler_adv.fit_transform(X_adv_train)
    
    advanced_model = LogisticRegression(multi_class='multinomial', solver='lbfgs', max_iter=1000)
    advanced_model.fit(X_adv_train_scaled, y_adv_train)
    
    # Get predictions on dev set
    X_dev_basic = dev_data[basic_features]
    X_dev_adv = dev_data[selected_advanced_features]
    y_dev = dev_data["outcome"]
    
    # Scale dev features
    X_dev_basic_scaled = scaler_basic.transform(X_dev_basic)
    X_dev_adv_scaled = scaler_adv.transform(X_dev_adv)
    
    # Get probabilities from both models
    basic_probs = basic_model.predict_proba(X_dev_basic_scaled)
    adv_probs = advanced_model.predict_proba(X_dev_adv_scaled)
    
    # Average probabilities
    ensemble_probs = (basic_probs + adv_probs) / 2
    ensemble_preds = np.argmax(ensemble_probs, axis=1)
        
    # Calculate accuracies
    basic_train_acc = accuracy_score(y_basic, basic_model.predict(X_basic_scaled))
    basic_dev_acc = accuracy_score(y_dev, basic_model.predict(X_dev_basic_scaled))
    
    adv_train_acc = accuracy_score(y_adv_train, advanced_model.predict(X_adv_train_scaled))
    adv_dev_acc = accuracy_score(y_dev, advanced_model.predict(X_dev_adv_scaled))
    
    ensemble_dev_acc = accuracy_score(y_dev, ensemble_preds)
    ensemble_train_acc = (basic_train_acc + adv_train_acc) / 2
    
    accuracies = {
        'train': [basic_train_acc, adv_train_acc, ensemble_train_acc],
        'dev': [basic_dev_acc, adv_dev_acc, ensemble_dev_acc]
    }
    
    # Perform CV for both models
    basic_scores = perform_cross_validation(X_basic, y_basic, basic_model, scaler_basic)
    adv_scores = perform_cross_validation(X_adv_train, y_adv_train, advanced_model, scaler_adv)
    
    # Unpack scores
    (basic_train_mean, basic_train_std), (basic_dev_mean, basic_dev_std) = basic_scores
    (adv_train_mean, adv_train_std), (adv_dev_mean, adv_dev_std) = adv_scores
    
    # Calculate ensemble scores
    ensemble_train_mean = (basic_train_mean + adv_train_mean) / 2
    ensemble_train_std = np.sqrt((basic_train_std**2 + adv_train_std**2) / 4)
    ensemble_dev_mean = (basic_dev_mean + adv_dev_mean) / 2
    ensemble_dev_std = np.sqrt((basic_dev_std**2 + adv_dev_std**2) / 4)
    
    accuracies = {
        'train': [(basic_train_mean, basic_train_std), 
                 (adv_train_mean, adv_train_std),
                 (ensemble_train_mean, ensemble_train_std)],
        'dev': [(basic_dev_mean, basic_dev_std),
                (adv_dev_mean, adv_dev_std),
                (ensemble_dev_mean, ensemble_dev_std)]
    }

    model_names = ['Basic', 'Advanced', 'Ensemble']

    
    # Get CV metrics for both models
    basic_metrics, basic_std = perform_cross_validation_with_metrics(X_basic, y_basic, 
                                                                   basic_model, scaler_basic)
    adv_metrics, adv_std = perform_cross_validation_with_metrics(X_adv_train, y_adv_train, 
                                                               advanced_model, scaler_adv)
    
    # Calculate ensemble metrics (average of basic and advanced)
    ensemble_metrics = {}
    ensemble_std = {}
    for class_label in ['0', '1', '2']:
        ensemble_metrics[class_label] = {
            metric: (basic_metrics[class_label][metric] + adv_metrics[class_label][metric])/2
            for metric in ['precision', 'recall', 'f1-score']
        }
        ensemble_std[class_label] = {
            metric: np.sqrt((basic_std[class_label][metric]**2 + 
                           adv_std[class_label][metric]**2)/4)
            for metric in ['precision', 'recall', 'f1-score']
        }
    
    cv_reports = [(basic_metrics, basic_std), 
                  (adv_metrics, adv_std), 
                  (ensemble_metrics, ensemble_std)]
    
    plot_classification_metrics(cv_reports, model_names)
    
    return basic_model, advanced_model, scaler_basic, scaler_adv, accuracies

if __name__ == "__main__":
    basic_model, advanced_model, scaler_basic, scaler_adv, accuracies = train_ensemble_models()
    plot_model_comparison(accuracies)