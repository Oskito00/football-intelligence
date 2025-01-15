import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score, confusion_matrix

def run_experiment_3_class(n_runs=10):
    """
    Train a 3-class classifier with comprehensive evaluation metrics
    """
    # Initialize metric storage
    test_accuracies = []
    train_accuracies = []
    home_win_accuracies = []
    test_precisions = []
    test_recalls = []
    test_f1s = []
    test_roc_aucs = []

    for run_i in range(n_runs):
        # 1. Load your preprocessed data
        df = pd.read_csv("sportradar/AI/preprocessed_features.csv")

        # 2. Create a 3-class outcome label: 2 = Home Win, 1 = Draw, 0 = Away Win
        def outcome_label(home_g, away_g):
            if home_g > away_g:
                return 2  # Home Win
            elif home_g < away_g:
                return 0  # Away Win
            else:
                return 1  # Draw

        df["outcome"] = [
            outcome_label(h, a) for h, a in zip(df["home_goals"], df["away_goals"])
        ]

        metadata_cols = ["start_time", "home_team", "away_team", "home_goals", "away_goals", "outcome"]
        
        # 3. Separate features (X) and target (y)
        X = df.drop(columns=metadata_cols)
        y = df["outcome"]

        # 4. Scale the features (important for logistic regression)
        scaler = StandardScaler()
        X_scaled = pd.DataFrame(
            scaler.fit_transform(X),
            columns=X.columns,
            index=X.index
        )

        # 5. Split into train/test
        random_state = np.random.randint(0, 1000)
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=random_state
        )

        df_test_metadata = df.loc[X_test.index, metadata_cols]

        # 6. Train a 3-class logistic regression
        param_grid = {
            'C': [0.001, 0.01, 0.1, 1, 10],  # Regularization parameter
            'max_iter': [1000]  # Increase max iterations to ensure convergence
        }
        clf = GridSearchCV(
            LogisticRegression(random_state=42, multi_class='multinomial'),
            param_grid,
            cv=3,
            scoring='accuracy'
        )
        clf.fit(X_train, y_train)

        best_model = clf.best_estimator_

        # 7. Predict on both train and test sets
        y_train_pred = best_model.predict(X_train)
        y_test_pred = best_model.predict(X_test)
        
        # Get prediction probabilities for ROC-AUC
        y_test_proba = best_model.predict_proba(X_test)

        # 8. Calculate all evaluation metrics
        # Basic accuracy
        train_accuracy = accuracy_score(y_train, y_train_pred)
        test_accuracy = accuracy_score(y_test, y_test_pred)
        
        # Precision, Recall, F1 (weighted averages)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_test, 
            y_test_pred, 
            average='weighted'
        )
        
        # ROC-AUC (one-vs-rest)
        roc_auc = roc_auc_score(
            pd.get_dummies(y_test), 
            y_test_proba, 
            multi_class='ovr'
        )
        
        # Confusion Matrix
        cm = confusion_matrix(y_test, y_test_pred)
        
        # Baseline: always predict Home Win
        y_baseline = np.full_like(y_test, fill_value=2)
        home_win_accuracy = accuracy_score(y_test, y_baseline)

        # Store metrics
        train_accuracies.append(train_accuracy)
        test_accuracies.append(test_accuracy)
        home_win_accuracies.append(home_win_accuracy)
        test_precisions.append(precision)
        test_recalls.append(recall)
        test_f1s.append(f1)
        test_roc_aucs.append(roc_auc)

        # # 9. Print test matches detail
        # outcome_map = {0: "Away Win", 1: "Draw", 2: "Home Win"}

        # print("  Test Matches Detail:")
        # for idx, pred_label in zip(X_test.index, y_test_pred):
        #     row = df_test_metadata.loc[idx]
        #     actual_label = row["outcome"]
        #     start_time = row["start_time"]
        #     home_team = row["home_team"]
        #     away_team = row["away_team"]
        #     actual_home_goals = row["home_goals"]
        #     actual_away_goals = row["away_goals"]

        #     pred_outcome = outcome_map[pred_label]
        #     actual_outcome = outcome_map[actual_label]
        #     print(
        #         f"    {start_time}: {home_team} vs {away_team} | "
        #         f"Predicted: {pred_outcome}, Actual: {actual_outcome} | "
        #         f"Score: {actual_home_goals}-{actual_away_goals}"
        #     )
        # print("-"*60)

        # Print run info
        print(f"\nRun {run_i+1}/{n_runs}")
        print(f"Best Params: {clf.best_params_}")
        print("\nMetrics:")
        print(f"  Train Accuracy:    {train_accuracy:.2%}")
        print(f"  Test Accuracy:     {test_accuracy:.2%}")
        print(f"  Precision:         {precision:.2%}")
        print(f"  Recall:            {recall:.2%}")
        print(f"  F1 Score:          {f1:.2%}")
        print(f"  ROC-AUC:           {roc_auc:.2%}")
        print(f"  Baseline Accuracy: {home_win_accuracy:.2%}")
        
        print("\nConfusion Matrix:")
        print("Predicted →  [Away Win  Draw  Home Win]")
        print(f"Actual ↓\n{cm}")

        # After each run, print feature importance
        feature_importance = pd.DataFrame({
            'feature': X.columns,
            'importance': np.mean(np.abs(best_model.coef_), axis=0)
        }).sort_values('importance', ascending=False)
        
        print("\nTop 5 Most Important Features:")
        print(feature_importance.head())
        print("-"*60)

    # 10. Final results
    print(f"\nFinal Results Over {n_runs} Runs:")
    print("\nAccuracy Metrics:")
    print(f"  Mean Train Accuracy: {np.mean(train_accuracies):.2%} (±{np.std(train_accuracies):.2%})")
    print(f"  Mean Test Accuracy:  {np.mean(test_accuracies):.2%} (±{np.std(test_accuracies):.2%})")
    print(f"  Home Win Baseline:   {np.mean(home_win_accuracies):.2%}")
    
    print("\nDetailed Test Metrics:")
    print(f"  Mean Precision:      {np.mean(test_precisions):.2%} (±{np.std(test_precisions):.2%})")
    print(f"  Mean Recall:         {np.mean(test_recalls):.2%} (±{np.std(test_recalls):.2%})")
    print(f"  Mean F1 Score:       {np.mean(test_f1s):.2%} (±{np.std(test_f1s):.2%})")
    print(f"  Mean ROC-AUC:        {np.mean(test_roc_aucs):.2%} (±{np.std(test_roc_aucs):.2%})")

def predict_future_match(future_match_csv, model_data_csv="sportradar/AI/preprocessed_features.csv"):
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

run_experiment_3_class(n_runs=100)

prediction, probabilities = predict_future_match("sportradar/future_matches/simple_implementation/preprocessed_features.csv")