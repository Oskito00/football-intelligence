import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, confusion_matrix
import matplotlib.pyplot as plt

from logistic_regression import create_data_splits

def get_elo_probabilities(elo_diff, threshold=40):
    """
    Convert ELO difference to probabilities based on distance from threshold
    """
    abs_diff = abs(elo_diff)
    
    if abs_diff < threshold:
        # Close match - higher draw probability
        # Calculate how close to threshold (0 to 1)
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

def run_hybrid_forest(n_runs=10, elo_threshold=40, weight_elo=0.4):
    """
    Hybrid model combining ELO threshold and Random Forest with optimized balance
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
    
    # Load data once
    df = pd.read_csv("sportradar/AI/processed_data/preprocessed_features.csv")
    
    # Create outcome labels
    df["outcome"] = [2 if h > a else (1 if h == a else 0) 
                    for h, a in zip(df["home_goals"], df["away_goals"])]
    
    # Define columns to drop once
    cols_to_drop = ["outcome", "start_time", "home_team", "away_team", "home_goals", "away_goals"]
    
    for run_i in range(n_runs):
        try:
            # Split data into train and dev sets
            train_data, dev_data = train_test_split(
                df,
                test_size=0.2,
                random_state=np.random.randint(0, 1000)
            )
            
            # Prepare features and labels for both sets
            X_train = train_data.drop(columns=cols_to_drop)
            y_train = train_data["outcome"]
            X_dev = dev_data.drop(columns=cols_to_drop)
            y_dev = dev_data["outcome"]  # Define y_dev here
            
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
            
            # Optimized Random Forest parameters
            rf_model = RandomForestClassifier(
                n_estimators=300,          # More trees for stability
                max_depth=6,               # Moderate depth
                min_samples_split=8,       # Slightly reduced from 10
                min_samples_leaf=4,        # Slightly reduced from 5
                max_features='sqrt',       # Classic RF setting
                bootstrap=True,
                oob_score=True,
                random_state=42,
                class_weight={0: 1.2, 1: 1.5, 2: 1.0}  # Custom weights for away/draw/home
            )
            
            # Feature selection based on importance
            def select_features_for_bag(X, y, n_features):
                # Train a quick RF to get feature importance
                temp_rf = RandomForestClassifier(
                    n_estimators=100, 
                    max_depth=4,
                    random_state=42
                )
                temp_rf.fit(X, y)
                
                # Get feature importance scores
                importance = temp_rf.feature_importances_
                feature_scores = list(zip(X.columns, importance))
                feature_scores.sort(key=lambda x: x[1], reverse=True)
                
                # Always include top features
                top_features = [f[0] for f in feature_scores[:10]]  # Always keep top 10
                
                # Randomly select from remaining features
                remaining_features = [f[0] for f in feature_scores[10:]]
                n_additional = n_features - len(top_features)
                if n_additional > 0:
                    additional_features = np.random.choice(
                        remaining_features,
                        size=min(n_additional, len(remaining_features)),
                        replace=False
                    )
                    selected_features = top_features + list(additional_features)
                else:
                    selected_features = top_features[:n_features]
                
                return selected_features
            
            # Modified feature bagging
            n_feature_bags = 7  # Increased from 5
            feature_bag_size = 0.7  # Reduced from 0.8
            
            feature_predictions_train = []
            feature_probabilities_train = []
            feature_predictions_dev = []
            feature_probabilities_dev = []
            
            # Initial feature importance selection
            all_selected_features = select_features_for_bag(
                X_train_scaled, 
                y_train, 
                int(len(feature_names) * feature_bag_size)
            )
            
            for bag_i in range(n_feature_bags):
                # Randomly sample from pre-selected features
                n_features = int(len(all_selected_features) * 0.9)  # Use 90% of selected features
                selected_features = np.random.choice(
                    all_selected_features,
                    size=n_features,
                    replace=False
                )
                
                # Train model on feature subset
                X_train_bag = X_train_scaled[selected_features]
                X_dev_bag = X_dev_scaled[selected_features]
                
                rf_model.fit(X_train_bag, y_train)
                
                # Get predictions for both train and dev sets
                train_predictions = rf_model.predict(X_train_bag)
                train_probabilities = rf_model.predict_proba(X_train_bag)
                dev_predictions = rf_model.predict(X_dev_bag)
                dev_probabilities = rf_model.predict_proba(X_dev_bag)
                
                feature_predictions_train.append(train_predictions)
                feature_probabilities_train.append(train_probabilities)
                feature_predictions_dev.append(dev_predictions)
                feature_probabilities_dev.append(dev_probabilities)
                
                # Monitor OOB error
                print(f"Bag {bag_i+1} OOB Score: {rf_model.oob_score_:.2%}")
            
            # Average predictions across feature bags
            avg_rf_probabilities_train = np.mean(feature_probabilities_train, axis=0)
            avg_rf_probabilities_dev = np.mean(feature_probabilities_dev, axis=0)
            
            # Modified hybrid prediction function
            def get_hybrid_predictions(data, rf_probs):
                predictions = []
                probabilities = []
                
                for i in range(len(data)):
                    match = data.iloc[i]
                    
                    # Get ELO probabilities
                    elo_diff = (match['home_elo_rating'] + 40) - match['away_elo_rating']
                    elo_probs = get_elo_probabilities(elo_diff, threshold=elo_threshold)
                    
                    # Dynamic ELO weight based on rating difference
                    elo_confidence = min(abs(elo_diff) / 400, 1.0)
                    rf_confidence = max(rf_probs[i])
                    
                    # More balanced weighting
                    dynamic_weight = weight_elo * (1 + elo_confidence * 0.2)
                    dynamic_weight = min(dynamic_weight, 0.7)  # Lower cap on ELO weight
                    
                    # Combine probabilities
                    combined_probs = [
                        dynamic_weight * elo_p + (1 - dynamic_weight) * rf_p 
                        for elo_p, rf_p in zip(elo_probs, rf_probs[i])
                    ]
                    
                    predictions.append(np.argmax(combined_probs))
                    probabilities.append(combined_probs)
                
                return np.array(predictions), np.array(probabilities)
            
            # Print shapes for debugging
            print(f"\nArray shapes:")
            print(f"train_data: {train_data.shape}")
            print(f"avg_rf_probabilities_train: {avg_rf_probabilities_train.shape}")
            print(f"dev_data: {dev_data.shape}")
            print(f"avg_rf_probabilities_dev: {avg_rf_probabilities_dev.shape}")
            
            # Get final predictions for both sets
            y_train_pred, y_train_proba = get_hybrid_predictions(train_data, avg_rf_probabilities_train)
            y_dev_pred, y_dev_proba = get_hybrid_predictions(dev_data, avg_rf_probabilities_dev)
            
            # Print prediction shapes for debugging
            print(f"y_train_pred shape: {y_train_pred.shape}")
            print(f"y_train shape: {y_train.shape}")
            print(f"y_dev_pred shape: {y_dev_pred.shape}")
            print(f"y_dev shape: {y_dev.shape}")
            
            # Calculate metrics
            train_accuracy = accuracy_score(y_train, y_train_pred)
            dev_accuracy = accuracy_score(y_dev, y_dev_pred)
            
            metrics['train_accuracies'].append(train_accuracy)
            metrics['dev_accuracies'].append(dev_accuracy)
            
            # Calculate precision/recall metrics for dev set only
            metrics['draw_precision'].append(precision_score(y_dev, y_dev_pred, labels=[1], average='micro'))
            metrics['draw_recall'].append(recall_score(y_dev, y_dev_pred, labels=[1], average='micro'))
            metrics['draw_f1'].append(2 * (metrics['draw_precision'][-1] * metrics['draw_recall'][-1]) / 
                                   (metrics['draw_precision'][-1] + metrics['draw_recall'][-1] + 1e-10))
            
            metrics['home_precision'].append(precision_score(y_dev, y_dev_pred, labels=[2], average='micro'))
            metrics['home_recall'].append(recall_score(y_dev, y_dev_pred, labels=[2], average='micro'))
            metrics['home_f1'].append(2 * (metrics['home_precision'][-1] * metrics['home_recall'][-1]) / 
                                   (metrics['home_precision'][-1] + metrics['home_recall'][-1] + 1e-10))
            
            metrics['away_precision'].append(precision_score(y_dev, y_dev_pred, labels=[0], average='micro'))
            metrics['away_recall'].append(recall_score(y_dev, y_dev_pred, labels=[0], average='micro'))
            metrics['away_f1'].append(2 * (metrics['away_precision'][-1] * metrics['away_recall'][-1]) / 
                                   (metrics['away_precision'][-1] + metrics['away_recall'][-1] + 1e-10))
            
            # Print run results
            print(f"\nRun {run_i+1}/{n_runs}")
            print(f"Train Accuracy: {train_accuracy:.2%}")
            print(f"Dev Accuracy:   {dev_accuracy:.2%}")
            print(f"Gap:           {(train_accuracy - dev_accuracy):.2%}")
            
            # Print confusion matrix
            cm = confusion_matrix(y_dev, y_dev_pred)
            print("\nConfusion Matrix (Dev Set):")
            print("Predicted →  [Away Win  Draw  Home Win]")
            print(f"Actual ↓\n{cm}")
            print("-"*60)
            
        except Exception as e:
            print(f"Error in run {run_i + 1}: {str(e)}")
            print(f"Error location: {e.__traceback__.tb_lineno}")
            continue
    
    print("\nFinal Results:")
    print(f"Average Dev Accuracy:   {np.mean(metrics['dev_accuracies']):.2%} (±{np.std(metrics['dev_accuracies']):.2%})")
    
    return metrics

if __name__ == "__main__":
    metrics = run_hybrid_forest(n_runs=10) 