import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.metrics import confusion_matrix, recall_score, precision_score
import matplotlib.pyplot as plt
import seaborn as sns

def run_xgboost_model(n_runs=10, elo_threshold=40, weight_elo=0.4):
    """
    Train an XGBoost model with hybrid predictions
    """
    metrics = {
        'train_accuracies': [],
        'dev_accuracies': [],
        'draw_precision': [],
        'draw_recall': [],
        'draw_f1': [],
        'home_precision': [],
        'home_recall': [],
        'home_f1': [],
        'away_precision': [],
        'away_recall': [],
        'away_f1': []
    }
    
    # Load data
    df = pd.read_csv("sportradar/AI/processed_data/preprocessed_features.csv")
    
    # Create outcome labels
    df["outcome"] = [2 if h > a else (1 if h == a else 0) 
                    for h, a in zip(df["home_goals"], df["away_goals"])]
    
    # Get data splits
    train_data, dev_data, test_data = create_data_splits(df, test_size=100)
    
    best_model = None
    best_scaler = None
    best_dev_accuracy = 0
    
    # Define columns to drop
    cols_to_drop = ["outcome", "start_time", "home_team", "away_team", "home_goals", "away_goals"]
    
    # XGBoost parameters
    params = {
        'objective': 'multi:softprob',
        'num_class': 3,
        'max_depth': 5,              # Slightly increased complexity
        'learning_rate': 0.01,       # Keep slow learning rate
        'subsample': 0.9,            # Use more data per tree
        'colsample_bytree': 0.9,     # Use more features per tree
        'min_child_weight': 2,
        'gamma': 0.05,
        'eval_metric': 'mlogloss',
        'tree_method': 'hist',
        'random_state': 42,
        'num_boost_round': 150,      # More boosting rounds
        'early_stopping_rounds': 15   # More patience before stopping
    }
    
    for run_i in range(n_runs):
        try:
            # Randomize train/dev split after first run
            if run_i > 0:
                train_data, dev_data = train_test_split(
                    pd.concat([train_data, dev_data]),
                    test_size=0.2,
                    random_state=np.random.randint(0, 1000)
                )
            
            # Prepare features
            X_train = train_data.drop(columns=cols_to_drop)
            y_train = train_data["outcome"]
            X_dev = dev_data.drop(columns=cols_to_drop)
            y_dev = dev_data["outcome"]
            feature_names = X_train.columns
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = pd.DataFrame(
                scaler.fit_transform(X_train),
                columns=feature_names,
                index=X_train.index
            )
            X_dev_scaled = pd.DataFrame(
                scaler.transform(X_dev),
                columns=feature_names,
                index=X_dev.index
            )
            
            # Create XGBoost datasets
            dtrain = xgb.DMatrix(
                X_train_scaled, 
                label=y_train, 
                feature_names=list(feature_names)  # Convert Index to list
            )
            ddev = xgb.DMatrix(
                X_dev_scaled, 
                label=y_dev, 
                feature_names=list(feature_names)  # Convert Index to list
            )
            
            # Train model
            model = xgb.train(
                params,
                dtrain,
                num_boost_round=100,
                evals=[(dtrain, 'train'), (ddev, 'dev')],
                early_stopping_rounds=10,
                verbose_eval=False
            )
            
            # Function for hybrid predictions
            def get_hybrid_predictions(data, features_scaled):
                predictions = []
                probabilities = []
                
                for _, match in data.iterrows():
                    # ELO predictions
                    elo_diff = (match['home_elo_rating'] + 40) - match['away_elo_rating']
                    elo_probs = get_elo_probabilities(elo_diff, threshold=elo_threshold)
                    
                    # XGBoost predictions
                    match_features = pd.DataFrame([match.drop(cols_to_drop)], columns=feature_names)
                    match_features_scaled = pd.DataFrame(
                        scaler.transform(match_features),
                        columns=feature_names
                    )
                    xgb_dmatrix = xgb.DMatrix(
                        match_features_scaled, 
                        feature_names=list(feature_names)  # Convert Index to list
                    )
                    xgb_probs = model.predict(xgb_dmatrix)[0]
                    
                    # Combine probabilities
                    combined_probs = [
                        weight_elo * elo_p + (1 - weight_elo) * xgb_p 
                        for elo_p, xgb_p in zip(elo_probs, xgb_probs)
                    ]
                    
                    predictions.append(np.argmax(combined_probs))
                    probabilities.append(combined_probs)
                
                return predictions, probabilities
            
            # Get predictions
            y_train_pred, y_train_proba = get_hybrid_predictions(train_data, X_train_scaled)
            y_dev_pred, y_dev_proba = get_hybrid_predictions(dev_data, X_dev_scaled)
            
            # Calculate accuracies
            train_accuracy = accuracy_score(y_train, y_train_pred)
            dev_accuracy = accuracy_score(y_dev, y_dev_pred)
            
            # Store metrics
            metrics['train_accuracies'].append(train_accuracy)
            metrics['dev_accuracies'].append(dev_accuracy)
            
            # Update best model
            if dev_accuracy > best_dev_accuracy:
                best_dev_accuracy = dev_accuracy
                best_model = model
                best_scaler = scaler
            
            # Calculate class-specific metrics
            for outcome in [0, 1, 2]:  # Away, Draw, Home
                precision = precision_score(y_dev == outcome, np.array(y_dev_pred) == outcome, zero_division=0)
                recall = recall_score(y_dev == outcome, np.array(y_dev_pred) == outcome, zero_division=0)
                f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
                
                if outcome == 0:
                    metrics['away_precision'].append(precision)
                    metrics['away_recall'].append(recall)
                    metrics['away_f1'].append(f1)
                elif outcome == 1:
                    metrics['draw_precision'].append(precision)
                    metrics['draw_recall'].append(recall)
                    metrics['draw_f1'].append(f1)
                else:
                    metrics['home_precision'].append(precision)
                    metrics['home_recall'].append(recall)
                    metrics['home_f1'].append(f1)
            
            # Print run info
            print(f"\nRun {run_i+1}/{n_runs}")
            print(f"Train Accuracy: {train_accuracy:.2%}")
            print(f"Dev Accuracy:   {dev_accuracy:.2%}")
            print(f"Difference:     {(train_accuracy - dev_accuracy):.2%}")
            
            # Print confusion matrix
            cm = confusion_matrix(y_dev, y_dev_pred)
            print("\nConfusion Matrix (Dev Set):")
            print("Predicted →  [Away Win  Draw  Home Win]")
            print(f"Actual ↓\n{cm}")
            
            # Plot feature importance
            if run_i == n_runs - 1:  # Only for last run
                importance = model.get_score(importance_type='gain')
                importance_df = pd.DataFrame(
                    {'feature': list(importance.keys()),
                     'importance': list(importance.values())}
                ).sort_values('importance', ascending=False)
                
                plt.figure(figsize=(10, 6))
                plt.bar(importance_df['feature'], importance_df['importance'])
                plt.xticks(rotation=45, ha='right')
                plt.title('Feature Importance (XGBoost)')
                plt.tight_layout()
                plt.savefig('sportradar/AI/models/analysis/xgboost_importance.png')
                plt.close()
                
                print("\nTop 10 Most Important Features:")
                print(importance_df.head(10))
            
            print("-"*60)
            
        except Exception as e:
            print(f"Error in run {run_i + 1}: {str(e)}")
            continue
    
    # Print final results
    print("\nFinal Results:")
    print(f"Average Train Accuracy: {np.mean(metrics['train_accuracies']):.2%} (±{np.std(metrics['train_accuracies']):.2%})")
    print(f"Average Dev Accuracy:   {np.mean(metrics['dev_accuracies']):.2%} (±{np.std(metrics['dev_accuracies']):.2%})")
    print(f"Average Gap:           {(np.mean(metrics['train_accuracies']) - np.mean(metrics['dev_accuracies'])):.2%}")
    
    return metrics, best_model, best_scaler, test_data

def create_data_splits(data, test_size=100, random_seed=42):
    """
    Split data into train, dev, and test sets.
    - Test set: Most recent test_size matches
    - Remaining data split randomly into train (80%) and dev (20%)
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

def get_elo_probabilities(elo_diff, threshold=40):
    """
    Convert ELO difference to probabilities based on distance from threshold
    """
    abs_diff = abs(elo_diff)
    
    if abs_diff < threshold:
        # Close match - higher draw probability
        distance_ratio = abs_diff / threshold
        draw_prob = 0.5 + (0.3 * (1 - distance_ratio))  # 50-80% for draw
        remaining_prob = 1 - draw_prob
        
        if elo_diff > 0:
            home_prob = remaining_prob * 0.7  # Favor home team slightly
            away_prob = remaining_prob * 0.3
        else:
            away_prob = remaining_prob * 0.7
            home_prob = remaining_prob * 0.3
    else:
        # Clear favorite - lower draw probability
        excess_ratio = min((abs_diff - threshold) / threshold, 1.0)  # Cap at 1.0
        draw_prob = 0.3 * (1 - excess_ratio)  # 0-30% for draw
        
        if elo_diff > 0:
            home_prob = 0.6 + (0.3 * excess_ratio)  # 60-90% for favorite
            away_prob = 1 - home_prob - draw_prob
        else:
            away_prob = 0.6 + (0.3 * excess_ratio)
            home_prob = 1 - away_prob - draw_prob
    
    return [away_prob, draw_prob, home_prob]

if __name__ == "__main__":
    metrics, model, scaler, test_data = run_xgboost_model(n_runs=10) 