import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score, confusion_matrix, recall_score, precision_score

def run_experiment_3_class(n_runs=10):
    """
    Train a 3-class classifier with comprehensive evaluation metrics
    """
    metrics = {
        'accuracies': [],
        'draw_precision': [],
        'draw_recall': [],
        'draw_f1': [],
        'home_precision': [],
        'home_recall': [],
        'home_f1': [],
        'away_precision': [],
        'away_recall': [],
        'away_f1': [],
        'home_win_accuracies': [],
        'roc_auc_scores': []
    }
    
    # Load data once
    df = pd.read_csv("sportradar/AI/processed_data/preprocessed_features.csv")
    
    # Create outcome labels
    df["outcome"] = [2 if h > a else (1 if h == a else 0) 
                    for h, a in zip(df["home_goals"], df["away_goals"])]
    
    # Get the fixed test set and reusable train/dev data
    train_data, dev_data, test_data = create_data_splits(df, test_size=100)
    metadata_cols = ["start_time", "home_team", "away_team", "home_goals", "away_goals", "outcome"]
    
    best_model = None
    best_scaler = None
    best_dev_accuracy = 0
    
    for run_i in range(n_runs):
        # For each run, only randomize train/dev split
        if run_i > 0:  # First split already done by create_data_splits
            train_data, dev_data = train_test_split(
                pd.concat([train_data, dev_data]),
                test_size=0.2,
                random_state=np.random.randint(0, 1000)
            )
        
        # Prepare features
        X_train = train_data.drop(columns=metadata_cols)
        y_train = train_data["outcome"]
        X_dev = dev_data.drop(columns=metadata_cols)
        y_dev = dev_data["outcome"]
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = pd.DataFrame(
            scaler.fit_transform(X_train),
            columns=X_train.columns,
            index=X_train.index
        )
        X_dev_scaled = pd.DataFrame(
            scaler.transform(X_dev),
            columns=X_dev.columns,
            index=X_dev.index
        )
        
        # Train model with grid search
        param_grid = {
            'C': [0.001, 0.01, 0.1, 1, 10],
            'max_iter': [1000]
        }
        clf = GridSearchCV(
            LogisticRegression(random_state=42, multi_class='multinomial'),
            param_grid,
            cv=3,
            scoring='accuracy'
        )
        clf.fit(X_train_scaled, y_train)
        best_model_run = clf.best_estimator_
        
        # Predictions
        y_train_pred = best_model_run.predict(X_train_scaled)
        y_dev_pred = best_model_run.predict(X_dev_scaled)
        y_dev_proba = best_model_run.predict_proba(X_dev_scaled)
        
        # Calculate metrics
        train_accuracy = accuracy_score(y_train, y_train_pred)
        dev_accuracy = accuracy_score(y_dev, y_dev_pred)
        
        # Keep track of best model
        if dev_accuracy > best_dev_accuracy:
            best_dev_accuracy = dev_accuracy
            best_model = best_model_run
            best_scaler = scaler
        
        # Calculate ROC-AUC
        roc_auc = roc_auc_score(
            pd.get_dummies(y_dev),
            y_dev_proba,
            multi_class='ovr'
        )
        metrics['roc_auc_scores'].append(roc_auc)
        
        # Baseline: always predict Home Win
        y_baseline = np.full_like(y_dev, fill_value=2)
        home_win_accuracy = accuracy_score(y_dev, y_baseline)
        metrics['home_win_accuracies'].append(home_win_accuracy)
        
        # Store metrics
        metrics['accuracies'].append(dev_accuracy)
        
        # Calculate class-specific metrics
        for outcome in [0, 1, 2]:  # Away, Draw, Home
            precision = precision_score(y_dev == outcome, y_dev_pred == outcome, zero_division=0)
            recall = recall_score(y_dev == outcome, y_dev_pred == outcome, zero_division=0)
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
        cm = confusion_matrix(y_dev, y_dev_pred)
        print(f"\nRun {run_i+1}/{n_runs}")
        print(f"Best Params: {clf.best_params_}")
        print("\nMetrics:")
        print(f"  Train Accuracy:    {train_accuracy:.2%}")
        print(f"  Dev Accuracy:      {dev_accuracy:.2%}")
        print(f"  ROC-AUC:           {roc_auc:.2%}")
        print(f"  Baseline Accuracy: {home_win_accuracy:.2%}")
        
        print("\nConfusion Matrix:")
        print("Predicted →  [Away Win  Draw  Home Win]")
        print(f"Actual ↓\n{cm}")
        
        # Print feature importance
        feature_importance = pd.DataFrame({
            'feature': X_train.columns,
            'importance': np.mean(np.abs(best_model_run.coef_), axis=0)
        }).sort_values('importance', ascending=False)
        
        print("\nTop 5 Most Important Features:")
        print(feature_importance.head())
        print("-"*60)
    
    # Print final results
    print(f"\nFinal Results Over {n_runs} Runs:")
    print("\nAccuracy Metrics:")
    print(f"  Mean Dev Accuracy:   {np.mean(metrics['accuracies']):.2%} (±{np.std(metrics['accuracies']):.2%})")
    print(f"  Mean ROC-AUC:        {np.mean(metrics['roc_auc_scores']):.2%} (±{np.std(metrics['roc_auc_scores']):.2%})")
    print(f"  Home Win Baseline:   {np.mean(metrics['home_win_accuracies']):.2%}")
    
    return metrics, best_model, best_scaler, test_data

def predict_future_match(future_match_csv, model_data_csv="sportradar/AI/processed_data/preprocessed_features.csv"):
    """
    Predict outcome for future matches using logistic regression
    """
    # Load training data and future matches
    df = pd.read_csv(model_data_csv)
    future_matches = pd.read_csv(future_match_csv)
    
    # Create outcome labels for training data
    df["outcome"] = [
        2 if h > a else (1 if h == a else 0)
        for h, a in zip(df["home_goals"], df["away_goals"])
    ]
    
    # Prepare training data
    metadata_cols = ["start_time", "home_team", "away_team", "home_goals", "away_goals", "outcome"]
    X_train = df.drop(columns=metadata_cols)
    y_train = df["outcome"]
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    
    # Train model
    clf = LogisticRegression(random_state=42, multi_class='multinomial', max_iter=1000)
    clf.fit(X_train_scaled, y_train)
    
    # Prepare future match data
    future_match_features = future_matches.drop(columns=["start_time", "home_team", "away_team"])
    future_match_scaled = scaler.transform(future_match_features)
    
    # Make predictions
    predictions = clf.predict(future_match_scaled)
    probabilities = clf.predict_proba(future_match_scaled)
    
    # Print results
    outcome_map = {0: "Away Win", 1: "Draw", 2: "Home Win"}
    print(f"\nFuture Match Predictions:")
    
    for idx, (_, match) in enumerate(future_matches.iterrows()):
        print(f"\nMatch {idx + 1}:")
        print(f"  {match['home_team']} vs {match['away_team']}")
        print(f"  Date: {match['start_time']}")
        print(f"  Predicted Outcome: {outcome_map[predictions[idx]]}")
        print(f"  Probabilities:")
        print(f"    Home Win: {probabilities[idx][2]:.2%}")
        print(f"    Draw:     {probabilities[idx][1]:.2%}")
        print(f"    Away Win: {probabilities[idx][0]:.2%}")
    
    return predictions, probabilities

def run_elo_baseline(n_runs=10):
    """
    Train a 3-class logistic regression using only ELO features
    """
    metrics = {
        'accuracies': [],
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
    
    # Create outcome label (2 = Home Win, 1 = Draw, 0 = Away Win)
    df["outcome"] = [2 if h > a else (1 if h == a else 0) 
                    for h, a in zip(df["home_goals"], df["away_goals"])]
    
    # Get the fixed test set and reusable train/dev data
    train_data, dev_data, test_data = create_data_splits(df, test_size=100)
    
    for run_i in range(n_runs):
        # For each run, only randomize train/dev split
        if run_i > 0:  # First split already done by create_data_splits
            train_data, dev_data = train_test_split(
                pd.concat([train_data, dev_data]),
                test_size=0.2,
                random_state=np.random.randint(0, 1000)
            )
        
        # Only use ELO features
        X_train = train_data[['home_elo_rating', 'away_elo_rating']]
        y_train = train_data["outcome"]
        X_dev = dev_data[['home_elo_rating', 'away_elo_rating']]
        y_dev = dev_data["outcome"]
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_dev_scaled = scaler.transform(X_dev)
        
        # Train logistic regression
        clf = LogisticRegression(random_state=42, multi_class='multinomial', max_iter=1000)
        clf.fit(X_train_scaled, y_train)
        
        # Predict
        y_pred = clf.predict(X_dev_scaled)
        y_pred_proba = clf.predict_proba(X_dev_scaled)
        
        # Calculate metrics
        accuracy = accuracy_score(y_dev, y_pred)
        metrics['accuracies'].append(accuracy)
        
        # Calculate class-specific metrics
        for outcome in [0, 1, 2]:  # Away, Draw, Home
            precision = precision_score(y_dev == outcome, y_pred == outcome, zero_division=0)
            recall = recall_score(y_dev == outcome, y_pred == outcome, zero_division=0)
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
        
        # Calculate confusion matrix
        cm = confusion_matrix(y_dev, y_pred)
        
        print(f"\nRun {run_i+1}/{n_runs}")
        print(f"Dev Set Accuracy: {accuracy:.2%}")
        print("\nConfusion Matrix:")
        print("Predicted →  [Away Win  Draw  Home Win]")
        print(f"Actual ↓\n{cm}")
        
        # Print draw prediction stats
        draws_mask = y_dev == 1
        if draws_mask.sum() > 0:
            draw_recall = recall_score(y_dev == 1, y_pred == 1, zero_division=0)
            draw_precision = precision_score(y_dev == 1, y_pred == 1, zero_division=0)
            print(f"\nDraw Recall: {draw_recall:.2%}")
            print(f"Draw Precision: {draw_precision:.2%}")
        
        # Example probability output for a few matches
        print("\nExample Predictions:")
        for i in range(min(5, len(y_dev))):
            print(f"Match {i+1}:")
            print(f"Probabilities: Home Win: {y_pred_proba[i][2]:.2%}, Draw: {y_pred_proba[i][1]:.2%}, Away Win: {y_pred_proba[i][0]:.2%}")
            print(f"Predicted: {['Away Win', 'Draw', 'Home Win'][y_pred[i]]}")
            print(f"Actual: {['Away Win', 'Draw', 'Home Win'][y_dev.iloc[i]]}")
        print("-"*60)
    
    # Return metrics, model, scaler and test data for final evaluation
    return metrics, clf, scaler, test_data

def run_elo_threshold_baseline(n_runs=10, threshold=40, home_advantage=40):
    """
    Simple ELO baseline that predicts:
    - Draw if ELO difference < threshold
    - Home win if home_elo > away_elo + threshold
    - Away win if away_elo > home_elo + threshold
    
    Incorporates home advantage by adding bonus points to home team's ELO
    """
    metrics = {
        'accuracies': [],
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
    
    # Get the fixed test set and reusable train/dev data
    train_data, dev_data, test_data = create_data_splits(df, test_size=100)
    
    def predict_with_threshold(row):
        # Add home advantage to home team's ELO
        adjusted_home_elo = row['home_elo_rating'] + home_advantage
        elo_diff = adjusted_home_elo - row['away_elo_rating']
        
        if abs(elo_diff) < threshold:
            return 1  # Draw
        return 2 if elo_diff > 0 else 0  # Home/Away win
    
    for run_i in range(n_runs):
        # For each run, only randomize train/dev split
        if run_i > 0:  # First split already done by create_data_splits
            train_data, dev_data = train_test_split(
                pd.concat([train_data, dev_data]),
                test_size=0.2,
                random_state=np.random.randint(0, 1000)
            )
        
        y_dev = dev_data["outcome"]
        y_pred = dev_data.apply(predict_with_threshold, axis=1)
        
        # Calculate metrics
        accuracy = accuracy_score(y_dev, y_pred)
        metrics['accuracies'].append(accuracy)
        
        # Calculate class-specific metrics
        for outcome in [0, 1, 2]:  # Away, Draw, Home
            precision = precision_score(y_dev == outcome, y_pred == outcome, zero_division=0)
            recall = recall_score(y_dev == outcome, y_pred == outcome, zero_division=0)
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
        cm = confusion_matrix(y_dev, y_pred)
        print(f"\nRun {run_i+1}/{n_runs}")
        print(f"Dev Set Accuracy: {accuracy:.2%}")
        print(f"Home Advantage: {home_advantage} ELO points")
        print(f"Threshold: {threshold} points")
        print("\nConfusion Matrix:")
        print("Predicted →  [Away Win  Draw  Home Win]")
        print(f"Actual ↓\n{cm}")
        print("-"*60)
    
    # Return metrics and test data for final evaluation
    return metrics, test_data

def print_three_way_comparison(full_metrics, elo_metrics, threshold_metrics):
    print("\n" + "="*140)
    print("Three-Way Model Comparison:")
    print("-"*140)
    print(f"{'Metric':<20} {'Full Model':<38} {'ELO ML Model':<38} {'ELO Threshold Model':<38}")
    print("-"*140)
    
    metrics_to_print = [
        ('Overall Accuracy', 'accuracies'),
        ('Home Win Precision', 'home_precision'),
        ('Home Win Recall', 'home_recall'),
        ('Home Win F1', 'home_f1'),
        ('Draw Precision', 'draw_precision'),
        ('Draw Recall', 'draw_recall'),
        ('Draw F1', 'draw_f1'),
        ('Away Win Precision', 'away_precision'),
        ('Away Win Recall', 'away_recall'),
        ('Away Win F1', 'away_f1')
    ]
    
    for metric_name, metric_key in metrics_to_print:
        full_mean = np.mean(full_metrics[metric_key])
        full_std = np.std(full_metrics[metric_key])
        elo_mean = np.mean(elo_metrics[metric_key])
        elo_std = np.std(elo_metrics[metric_key])
        threshold_mean = np.mean(threshold_metrics[metric_key])
        threshold_std = np.std(threshold_metrics[metric_key])
        
        print(f"{metric_name:<20} {full_mean:>6.2%} (±{full_std:>5.2%}) {' '*10} "
              f"{elo_mean:>6.2%} (±{elo_std:>5.2%}) {' '*10} "
              f"{threshold_mean:>6.2%} (±{threshold_std:>5.2%})")
    
    print("="*140)

def run_hybrid_model(n_runs=10, elo_threshold=40, weight_elo=0.3):
    """
    Hybrid model combining ELO threshold and full logistic regression
    """
    metrics = {
        'accuracies': [],
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
    
    # Get the fixed test set and reusable train/dev data
    train_data, dev_data, test_data = create_data_splits(df, test_size=100)
    
    best_model = None
    best_scaler = None
    best_dev_accuracy = 0
    
    # Define columns to drop once
    cols_to_drop = ["outcome", "start_time", "home_team", "away_team", "home_goals", "away_goals"]
    
    for run_i in range(n_runs):
        try:
            # For each run, only randomize train/dev split
            if run_i > 0:  # First split already done by create_data_splits
                train_data, dev_data = train_test_split(
                    pd.concat([train_data, dev_data]),
                    test_size=0.2,
                    random_state=np.random.randint(0, 1000)
                )
            
            # Train full model
            X_train = train_data.drop(columns=cols_to_drop)
            y_train = train_data["outcome"]
            feature_names = X_train.columns
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = pd.DataFrame(
                scaler.fit_transform(X_train),
                columns=feature_names,
                index=X_train.index
            )
            
            # Train model
            full_model = LogisticRegression(random_state=42, multi_class='multinomial', max_iter=1000)
            full_model.fit(X_train_scaled, y_train)
            
            # Evaluate on dev set
            X_dev = dev_data.drop(columns=cols_to_drop)
            y_dev = dev_data["outcome"]
            X_dev_scaled = pd.DataFrame(
                scaler.transform(X_dev),
                columns=feature_names,
                index=X_dev.index
            )
            
            # Make hybrid predictions
            y_pred = []
            y_pred_proba = []
            
            for _, match in dev_data.iterrows():
                # Add 100 point home advantage to ELO difference
                elo_diff = (match['home_elo_rating'] + 40) - match['away_elo_rating']
                elo_probs = get_elo_probabilities(elo_diff, threshold=elo_threshold)
                
                # Get ML probabilities
                match_features = pd.DataFrame([match.drop(cols_to_drop)], columns=feature_names)
                match_features_scaled = pd.DataFrame(
                    scaler.transform(match_features),
                    columns=feature_names
                )
                ml_probs = full_model.predict_proba(match_features_scaled)[0]
                
                # Combine probabilities
                combined_probs = [
                    weight_elo * elo_p + (1 - weight_elo) * ml_p 
                    for elo_p, ml_p in zip(elo_probs, ml_probs)
                ]
                
                y_pred.append(np.argmax(combined_probs))
                y_pred_proba.append(combined_probs)
            
            # Calculate metrics
            accuracy = accuracy_score(y_dev, y_pred)
            metrics['accuracies'].append(accuracy)
            
            # Update best model if needed
            if accuracy > best_dev_accuracy:
                best_dev_accuracy = accuracy
                best_model = full_model
                best_scaler = scaler
            
            # Calculate class-specific metrics
            for outcome in [0, 1, 2]:  # Away, Draw, Home
                precision = precision_score(y_dev == outcome, np.array(y_pred) == outcome, zero_division=0)
                recall = recall_score(y_dev == outcome, np.array(y_pred) == outcome, zero_division=0)
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
            
            print(f"\nRun {run_i+1}/{n_runs}")
            print(f"Dev Accuracy: {accuracy:.2%}")
            
            # Print confusion matrix
            cm = confusion_matrix(y_dev, y_pred)
            print("\nConfusion Matrix:")
            print("Predicted →  [Away Win  Draw  Home Win]")
            print(f"Actual ↓\n{cm}")
            print("-"*60)
            
        except Exception as e:
            print(f"Error in run {run_i + 1}: {str(e)}")
            continue
    
    return metrics, best_model, best_scaler, test_data

def print_four_way_comparison(full_metrics, elo_metrics, threshold_metrics, hybrid_metrics):
    print("\n" + "="*180)
    print("Four-Way Model Comparison:")
    print("-"*180)
    print(f"{'Metric':<20} {'Full Model':<38} {'ELO ML Model':<38} {'ELO Threshold Model':<38} {'Hybrid Model':<38}")
    print("-"*180)
    
    metrics_to_print = [
        ('Overall Accuracy', 'accuracies'),
        ('Home Win Precision', 'home_precision'),
        ('Home Win Recall', 'home_recall'),
        ('Home Win F1', 'home_f1'),
        ('Draw Precision', 'draw_precision'),
        ('Draw Recall', 'draw_recall'),
        ('Draw F1', 'draw_f1'),
        ('Away Win Precision', 'away_precision'),
        ('Away Win Recall', 'away_recall'),
        ('Away Win F1', 'away_f1')
    ]
    
    for metric_name, metric_key in metrics_to_print:
        full_mean = np.mean(full_metrics[metric_key])
        full_std = np.std(full_metrics[metric_key])
        elo_mean = np.mean(elo_metrics[metric_key])
        elo_std = np.std(elo_metrics[metric_key])
        threshold_mean = np.mean(threshold_metrics[metric_key])
        threshold_std = np.std(threshold_metrics[metric_key])
        hybrid_mean = np.mean(hybrid_metrics[metric_key])
        hybrid_std = np.std(hybrid_metrics[metric_key])
        
        print(f"{metric_name:<20} {full_mean:>6.2%} (±{full_std:>5.2%}) {' '*10} "
              f"{elo_mean:>6.2%} (±{elo_std:>5.2%}) {' '*10} "
              f"{threshold_mean:>6.2%} (±{threshold_std:>5.2%}) {' '*10} "
              f"{hybrid_mean:>6.2%} (±{hybrid_std:>5.2%})")
    
    print("="*180)

def optimize_hybrid_weights(n_runs=100, thresholds=[40], weights=np.arange(0.1, 1.0, 0.1)):
    """
    Test different combinations of ELO thresholds and weights
    """
    results = {}
    
    for threshold in thresholds:
        for weight in weights:
            print(f"\nTesting threshold={threshold}, weight_elo={weight:.1f}")
            metrics = run_hybrid_model(n_runs=n_runs, 
                                     elo_threshold=threshold, 
                                     weight_elo=weight)
            
            # Store average metrics
            results[(threshold, weight)] = {
                'accuracy': np.mean(metrics['accuracies']),
                'accuracy_std': np.std(metrics['accuracies']),
                'draw_f1': np.mean(metrics['draw_f1']),
                'home_f1': np.mean(metrics['home_f1']),
                'away_f1': np.mean(metrics['away_f1'])
            }
    
    # Convert to DataFrame for easier analysis
    results_df = pd.DataFrame(results).T
    results_df.index.names = ['threshold', 'weight']
    
    # Print results
    print("\nResults Summary:")
    print("="*100)
    print("Weight  Accuracy     Draw F1    Home F1    Away F1")
    print("-"*100)
    
    for (threshold, weight), row in results_df.iterrows():
        print(f"{weight:>6.1f}   {row['accuracy']:>6.2%} (±{row['accuracy_std']:>4.2%})   "
              f"{row['draw_f1']:>6.2%}   {row['home_f1']:>6.2%}   {row['away_f1']:>6.2%}")
    
    # Find best weights for different metrics
    print("\nBest Weights:")
    metrics = ['accuracy', 'draw_f1', 'home_f1', 'away_f1']
    for metric in metrics:
        best_idx = results_df[metric].idxmax()
        best_value = results_df[metric].max()
        print(f"Best {metric:<10}: weight={best_idx[1]:.1f}, value={best_value:.2%}")
    
    return results_df

def predict_test_matches(test_data_csv="sportradar/AI/processed_data/test_preprocessed_features.csv", 
                        train_data_csv="sportradar/AI/processed_data/preprocessed_features.csv",
                        home_advantage=40):  # Add home_advantage parameter
    """
    Predict outcomes for test matches using hybrid model (ML + ELO)
    """
    # Load training data and test matches
    train_df = pd.read_csv(train_data_csv)
    test_matches = pd.read_csv(test_data_csv)
    
    # Create outcome labels for training data
    train_df["outcome"] = [
        2 if h > a else (1 if h == a else 0)
        for h, a in zip(train_df["home_goals"], train_df["away_goals"])
    ]
    
    # Get common features and prepare data
    test_features = set(test_matches.columns) - set(["start_time", "home_team", "away_team"])
    train_features = set(train_df.columns) - set(["start_time", "home_team", "away_team", "home_goals", "away_goals", "outcome"])
    common_features = list(test_features.intersection(train_features))
    
    print(f"\nUsing {len(common_features)} common features for prediction:")
    print(", ".join(sorted(common_features)))
    
    # Prepare data
    X_train = train_df[common_features]
    y_train = train_df["outcome"]
    X_test = test_matches[common_features]
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train model
    model = LogisticRegression(random_state=42, multi_class='multinomial', max_iter=1000)
    model.fit(X_train_scaled, y_train)
    
    # Get ML probabilities
    ml_probabilities = model.predict_proba(X_test_scaled)
    
    # Hybrid prediction parameters
    elo_threshold = 40
    weight_elo = 0.3
    
    # Final predictions and probabilities
    final_predictions = []
    final_probabilities = []
    
    # Make hybrid predictions
    for i, match in test_matches.iterrows():
        # Use specified home advantage
        elo_diff = (match['home_elo_rating'] + home_advantage) - match['away_elo_rating']
        elo_probs = get_elo_probabilities(elo_diff, threshold=elo_threshold)
        
        # Get ML probabilities for this match
        ml_probs = ml_probabilities[i]
        
        # Combine probabilities using weighted average
        combined_probs = [
            weight_elo * elo_p + (1 - weight_elo) * ml_p 
            for elo_p, ml_p in zip(elo_probs, ml_probs)
        ]
        
        final_probabilities.append(combined_probs)
        final_predictions.append(np.argmax(combined_probs))
        
        # Print match details
        print(f"\nMatch {i + 1}:")
        print(f"  {match['home_team']} vs {match['away_team']}")
        print(f"  Date: {match['start_time']}")
        print(f"  Predicted Outcome: {['Away Win', 'Draw', 'Home Win'][np.argmax(combined_probs)]}")
        print(f"  Probabilities:")
        print(f"    Home Win: {combined_probs[2]:.2%}")
        print(f"    Draw:     {combined_probs[1]:.2%}")
        print(f"    Away Win: {combined_probs[0]:.2%}")
        print(f"  ELO Difference: {elo_diff:.1f}")
    
    return final_predictions, final_probabilities

#********************************************************************************
#Helper functions
#********************************************************************************

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

# Main execution
if __name__ == "__main__":
    # Remove these lines at the bottom of the file
    # print("Running Full Model:")
    # full_metrics, full_model, scaler, test_data = run_experiment_3_class(n_runs=50)
    # print("\nRunning ELO ML Model:")
    # elo_metrics, elo_model, elo_scaler, test_data = run_elo_baseline(n_runs=400)
    # print("\nRunning ELO Threshold Model:")
    # threshold_metrics, test_data = run_elo_threshold_baseline(n_runs=400, threshold=40)
    # print("\nRunning Hybrid Model:")
    # hybrid_metrics, full_model, scaler, test_data = run_hybrid_model(n_runs=400, elo_threshold=40, weight_elo=0.3)
    # print_four_way_comparison(full_metrics, elo_metrics, threshold_metrics, hybrid_metrics)
    # Remove all the model comparison code and just run predictions
    print("Predicting Test Matches:")
    predictions, probabilities = predict_test_matches(
        test_data_csv="sportradar/AI/processed_data/test_preprocessed_features.csv",
        train_data_csv="sportradar/AI/processed_data/preprocessed_features.csv",
        home_advantage=100
    )
    
    # Save predictions to CSV
    test_df = pd.read_csv("sportradar/AI/processed_data/test_preprocessed_features.csv")
    results_df = pd.DataFrame({
        'start_time': test_df['start_time'],
        'home_team': test_df['home_team'],
        'away_team': test_df['away_team'],
        'predicted_outcome': [['Away Win', 'Draw', 'Home Win'][p] for p in predictions],
        'home_win_prob': [round(p[2], 2) for p in probabilities],
        'draw_prob': [round(p[1], 2) for p in probabilities],
        'away_win_prob': [round(p[0], 2) for p in probabilities]
    })
    
    output_path = "sportradar/AI/match_predictions.csv"
    results_df.to_csv(output_path, index=False)
    print(f"\nPredictions saved to {output_path}")
