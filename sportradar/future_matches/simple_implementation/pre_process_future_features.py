import pandas as pd

# Load and preprocess data
df = pd.read_csv('sportradar/future_matches/simple_implementation/match_metrics.csv')

# Create derived difference features
df_features = pd.DataFrame()

# Keep original identifying columns
df_features['start_time'] = df['start_time']
df_features['home_team'] = df['home_team']
df_features['away_team'] = df['away_team']
df_features['competition_id'] = df['competition_id']
df_features['match_importance'] = df['match_importance']

# Create difference features
df_features["goals_scored_difference"] = df["average_home_goals_scored"] - df["average_away_goals_scored"]
df_features["goals_conceded_difference"] = df["average_home_goals_conceded"] - df["average_away_goals_conceded"]
df_features["win_rate_difference"] = df["average_home_win_rate"] - df["average_away_win_rate"]
df_features["squad_strength_difference"] = df["home_squad_strength"] - df["away_squad_strength"]
df_features["fatigue_difference"] = df["home_fatigue"] - df["away_fatigue"]
df_features["h2h_points_difference"] = df["home_h2h_avg_points"] - df["away_h2h_avg_points"]
df_features["pass_effectiveness_difference"] = df["home_pass_effectiveness"] - df["away_pass_effectiveness"]
df_features["shot_accuracy_difference"] = df["home_shot_accuracy"] - df["away_shot_accuracy"]
df_features["conversion_rate_difference"] = df["home_conversion_rate"] - df["away_conversion_rate"]
df_features["defensive_success_difference"] = df["home_defensive_success"] - df["away_defensive_success"]
df_features["clean_sheets_difference"] = df["average_home_clean_sheets"] - df["average_away_clean_sheets"]
df_features["h2h_goals_difference"] = df["home_h2h_avg_goals"] - df["away_h2h_avg_goals"]
df_features["h2h_clean_sheets_difference"] = df["home_h2h_avg_clean_sheets"] - df["away_h2h_avg_clean_sheets"]

# Save preprocessed features
df_features.to_csv('sportradar/future_matches/simple_implementation/preprocessed_features.csv', index=False)

print("Preprocessed features saved!")