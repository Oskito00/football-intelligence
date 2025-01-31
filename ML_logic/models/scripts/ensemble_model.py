import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score

def run_ensemble_experiment(n_runs=10):
    """Run multiple training iterations and collect performance metrics"""
    
    # Initialize metric storage
    basic_accuracies = []
    advanced_accuracies = []
    basic_roc_aucs = []
    advanced_roc_aucs = []

    for run_i in range(n_runs):
        # Load datasets
        basic_df = pd.read_csv('sportradar/AI/preprocessed_basic_features.csv')
        advanced_df = pd.read_csv('sportradar/AI/preprocessed_features.csv')
        

        
        # Split data
        X_basic = basic_df.drop(['start_time', 'home_team', 'away_team', 'home_goals', 'away_goals'], axis=1)
        y_basic = create_outcome_labels(basic_df['home_goals'], basic_df['away_goals'])
        
        X_advanced = advanced_df.drop(['start_time', 'home_team', 'away_team', 'home_goals', 'away_goals'], axis=1)
        y_advanced = create_outcome_labels(advanced_df['home_goals'], advanced_df['away_goals'])
        
        # Train/test split
        X_basic_train, X_basic_test, y_basic_train, y_basic_test = train_test_split(X_basic, y_basic, test_size=0.2)
        X_adv_train, X_adv_test, y_adv_train, y_adv_test = train_test_split(X_advanced, y_advanced, test_size=0.2)
        
        # Scale features
        scaler_basic = StandardScaler()
        scaler_advanced = StandardScaler()
        
        X_basic_train_scaled = scaler_basic.fit_transform(X_basic_train)
        X_basic_test_scaled = scaler_basic.transform(X_basic_test)
        
        X_adv_train_scaled = scaler_advanced.fit_transform(X_adv_train)
        X_adv_test_scaled = scaler_advanced.transform(X_adv_test)
        
        # Train models
        basic_model = LogisticRegression(multi_class='multinomial', max_iter=1000)
        advanced_model = LogisticRegression(multi_class='multinomial', max_iter=1000)
        
        basic_model.fit(X_basic_train_scaled, y_basic_train)
        advanced_model.fit(X_adv_train_scaled, y_adv_train)
        
        # Get predictions
        basic_proba = basic_model.predict_proba(X_basic_test_scaled)
        basic_pred = basic_model.predict(X_basic_test_scaled)
        
        advanced_proba = advanced_model.predict_proba(X_adv_test_scaled)
        advanced_pred = advanced_model.predict(X_adv_test_scaled)
        
        # Calculate metrics
        basic_acc = accuracy_score(y_basic_test, basic_pred)
        advanced_acc = accuracy_score(y_adv_test, advanced_pred)
        
        basic_roc = roc_auc_score(y_basic_test, basic_proba, multi_class='ovr')
        advanced_roc = roc_auc_score(y_adv_test, advanced_proba, multi_class='ovr')
        
        # Store metrics
        basic_accuracies.append(basic_acc)
        advanced_accuracies.append(advanced_acc)
        basic_roc_aucs.append(basic_roc)
        advanced_roc_aucs.append(advanced_roc)
        
        if run_i % 10 == 0:
            print(f"\nRun {run_i + 1}/{n_runs}")
            print(f"Basic Model Accuracy: {basic_acc:.2%}")
            print(f"Advanced Model Accuracy: {advanced_acc:.2%}")
    
    # Print final results
    print("\nFinal Results:")
    print(f"Basic Model: {np.mean(basic_accuracies):.2%} ± {np.std(basic_accuracies):.2%}")
    print(f"Advanced Model: {np.mean(advanced_accuracies):.2%} ± {np.std(advanced_accuracies):.2%}")
    print(f"\nROC-AUC Scores:")
    print(f"Basic Model: {np.mean(basic_roc_aucs):.2%} ± {np.std(basic_roc_aucs):.2%}")
    print(f"Advanced Model: {np.mean(advanced_roc_aucs):.2%} ± {np.std(advanced_roc_aucs):.2%}")
    
    return {
        'basic_model': basic_model,
        'advanced_model': advanced_model,
        'basic_scaler': scaler_basic,
        'advanced_scaler': scaler_advanced,
        'basic_features': X_basic.columns,
        'advanced_features': X_advanced.columns
    }

def predict_with_ensemble(match_data, models):
    """
    Make predictions using both models when possible, otherwise use basic model
    """
    has_advanced_features = all(col in match_data.columns 
                              for col in models['advanced_features'])
    
    # Prepare basic features
    X_basic = match_data[models['basic_features']]
    X_basic_scaled = models['basic_scaler'].transform(X_basic)
    basic_pred = models['basic_model'].predict_proba(X_basic_scaled)
    
    if has_advanced_features:
        # If we have advanced stats, use both models
        X_advanced = match_data[models['advanced_features']]
        X_advanced_scaled = models['advanced_scaler'].transform(X_advanced)
        advanced_pred = models['advanced_model'].predict_proba(X_advanced_scaled)
        
        # Weighted ensemble (adjust weights based on performance)
        final_pred = 0.4 * basic_pred + 0.6 * advanced_pred
    else:
        # If no advanced stats, use only basic model
        final_pred = basic_pred
    
    return final_pred

def create_outcome_labels(home_goals, away_goals):
    return np.where(home_goals > away_goals, 2,
                   np.where(home_goals == away_goals, 1, 0)) 


# Train models
models = run_ensemble_experiment(n_runs=100)

# Make predictions
# predictions = predict_with_ensemble(new_match_data, models)