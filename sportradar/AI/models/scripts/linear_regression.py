import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

def run_experiment(n_runs=10):
    accuracies = []
    home_win_accuracies = []  # New list for baseline accuracies
    train_mse_homes = []
    train_mse_aways = []
    test_mse_homes = []
    test_mse_aways = []
    
    for run_i in range(n_runs):
        # 1. Load the preprocessed data
        df = pd.read_csv("sportradar/AI/preprocessed_features.csv")

        # The columns (for reference):
        # start_time,home_team,away_team,competition_id,match_importance,
        # goals_scored_difference,goals_conceded_difference,win_rate_difference,
        # squad_strength_difference,fatigue_difference,h2h_points_difference,
        # pass_effectiveness_difference,shot_accuracy_difference,conversion_rate_difference,
        # defensive_success_difference,clean_sheets_difference,h2h_goals_difference,
        # h2h_clean_sheets_difference,home_goals,away_goals

        # 2. Separate out the columns we do NOT train on
        metadata_cols = ["start_time", "home_team", "away_team"]
        target_cols = ["home_goals", "away_goals"]

        # Features for training (drop metadata + target columns)
        X = df.drop(columns=metadata_cols + target_cols)

        # Targets
        y_home = df["home_goals"]
        y_away = df["away_goals"]

        # Scale the features
        scaler = StandardScaler()
        X_scaled = pd.DataFrame(
            scaler.fit_transform(X),
            columns=X.columns,
            index=X.index
        )

        # 3. Split into training and test sets with a random seed
        random_state = np.random.randint(0, 1000)
        X_train, X_test, y_train_home, y_test_home, y_train_away, y_test_away = train_test_split(
            X_scaled, y_home, y_away, test_size=0.2, random_state=random_state
        )

        # Keep corresponding rows for metadata in the test set
        df_test_metadata = df.loc[X_test.index, metadata_cols + target_cols]

        # 4. Train two separate ridge regression models with cross-validation
        alphas = [0.001, 0.01, 0.1, 1.0, 10.0, 100.0]

        # Home model
        home_model = GridSearchCV(
            Ridge(random_state=42),
            {'alpha': alphas},
            cv=5,
            scoring='neg_mean_squared_error'
        )
        home_model.fit(X_train, y_train_home)

        # Away model
        away_model = GridSearchCV(
            Ridge(random_state=42),
            {'alpha': alphas},
            cv=5,
            scoring='neg_mean_squared_error'
        )
        away_model.fit(X_train, y_train_away)

        # 5. Predict on the test set
        y_pred_home_test = home_model.predict(X_test)
        y_pred_away_test = away_model.predict(X_test)

        # 6. Evaluate match outcome predictions
        def outcome_label(home_goals, away_goals):
            """
            Returns a string label for the outcome based on rounded goals
            """
            # Round to nearest integer
            home_goals = round(home_goals)
            away_goals = round(away_goals)
            
            if home_goals > away_goals:
                return "Home Win"
            elif home_goals < away_goals:
                return "Away Win"
            else:
                return "Draw"

        # Calculate model accuracy
        correct_count = 0
        predictions= []
        home_win_correct = 0  # Counter for baseline strategy
        total_matches = len(X_test)
        
        for i in range(total_matches):
            idx = X_test.index[i]
            actual_home = df_test_metadata.loc[idx, "home_goals"]
            actual_away = df_test_metadata.loc[idx, "away_goals"]
            
            # Model prediction
            predicted_home = y_pred_home_test[i]
            predicted_away = y_pred_away_test[i]
            predicted_outcome = outcome_label(predicted_home, predicted_away)
            actual_outcome = outcome_label(actual_home, actual_away)
            
            if predicted_outcome == actual_outcome:
                correct_count += 1
            
            # Baseline: Always predict home win
            if actual_outcome == "Home Win":
                home_win_correct += 1
        
        accuracy = correct_count / total_matches
        home_win_accuracy = home_win_correct / total_matches
        
        # Calculate MSE for both train and test sets
        train_mse_home = mean_squared_error(y_train_home, home_model.predict(X_train))
        train_mse_away = mean_squared_error(y_train_away, away_model.predict(X_train))
        test_mse_home = mean_squared_error(y_test_home, y_pred_home_test)
        test_mse_away = mean_squared_error(y_test_away, y_pred_away_test)
        
        # Store metrics
        train_mse_homes.append(train_mse_home)
        train_mse_aways.append(train_mse_away)
        test_mse_homes.append(test_mse_home)
        test_mse_aways.append(test_mse_away)
        accuracies.append(accuracy)
        home_win_accuracies.append(home_win_accuracy)
        
        print(f"Run {run_i + 1}/{n_runs} — "
              f"Model Accuracy: {accuracy:.2%}, "
              f"Home Win Baseline: {home_win_accuracy:.2%}, "
              f"Train MSE (Home/Away): {train_mse_home:.4f}/{train_mse_away:.4f}, "
              f"Test MSE (Home/Away): {test_mse_home:.4f}/{test_mse_away:.4f}")

    print("\nFinal Results Over", n_runs, "Runs:")
    print(f"Mean Model Accuracy: {np.mean(accuracies):.2%}")
    print(f"Mean Home Win Baseline: {np.mean(home_win_accuracies):.2%}")
    print(f"Model Std Dev: {np.std(accuracies):.2%}")
    print(f"\nMean Train MSE (Home/Away): {np.mean(train_mse_homes):.4f}/{np.mean(train_mse_aways):.4f}")
    print(f"Mean Test MSE (Home/Away): {np.mean(test_mse_homes):.4f}/{np.mean(test_mse_aways):.4f}")

# Now actually call the function
run_experiment(n_runs=100)