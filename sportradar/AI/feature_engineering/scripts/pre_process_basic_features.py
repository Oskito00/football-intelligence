import pandas as pd
from sklearn.preprocessing import LabelEncoder
import joblib

# Load and preprocess data
df = pd.read_csv('sportradar/data/processed_data/test_data_basic.csv')
# df = pd.read_csv('sportradar/data/processed_data/training_data_basic.csv')

# Drop non-feature columns
df_features = df.drop(["fixture_id"], axis=1)

# Label encode competition_id
competition_encoder = LabelEncoder()
df_features["competition_id"] = competition_encoder.fit_transform(df_features["competition_id"])

# Save the label encoder for future use
joblib.dump(competition_encoder, 'sportradar/AI/competition_id_encoder_basic.joblib')

# Create derived difference features
df_features["goals_scored_difference"] = df_features["average_home_goals_scored"] - df_features["average_away_goals_scored"]
df_features["goals_conceded_difference"] = df_features["average_home_goals_conceded"] - df_features["average_away_goals_conceded"]
df_features["win_rate_difference"] = df_features["average_home_win_rate"] - df_features["average_away_win_rate"]
df_features["draw_rate_difference"] = df_features["average_home_draw_rate"] - df_features["average_away_draw_rate"]
df_features["fatigue_difference"] = df_features["home_fatigue"] - df_features["away_fatigue"]
df_features["clean_sheets_difference"] = df_features["average_home_clean_sheets"] - df_features["average_away_clean_sheets"]
df_features['momentum_difference'] = df_features['home_momentum'] - df_features['away_momentum']
df_features['elo_rating_difference'] = df_features['home_elo_rating'] - df_features['away_elo_rating']
df_features['elo_similarity'] = 1/(1+abs(df_features['elo_rating_difference'])) #Improves draw recall
df_features['draw_rate_similarity'] = 1/(1+abs(df_features['draw_rate_difference'])) #Improves draw recall
df_features['form_similarity'] = 1 / (1 + abs( #Improves draw recall
    # Attacking form
    0.3 * abs(df_features["goals_scored_difference"])+
    
    # Defensive form
    0.3 * abs(df_features["goals_conceded_difference"]) +
    0.3 * abs(df_features["clean_sheets_difference"]) +
    
    # Overall form
    0.4 * abs(df_features["win_rate_difference"]) +
    0.3 * abs(df_features["momentum_difference"])))

# Drop redundant original features, but keep core performance metrics
columns_to_drop = [
    # Keep these core metrics
    # "average_home_goals_scored", "average_away_goals_scored",
    # "average_home_goals_conceded", "average_away_goals_conceded",
    # "average_home_win_rate", "average_away_win_rate",
    # "average_home_draw_rate", "average_away_draw_rate",
    # "average_home_clean_sheets", "average_away_clean_sheets",
    #h2h_avg_draw_rate
    
    # Drop these comparison metrics
    "home_fatigue", "away_fatigue", 
    # "home_team_gk_strength", "home_team_defence_strength", "home_team_midfield_strength", "home_team_attack_strength", "home_team_overall_strength", "away_team_gk_sway_team_defence_strength", "away_team_midfield_strength","away_team_midfield_strength","away_team_attack_strength","away_team_overall_strength"
    # , "home_team_midfield_strength", "home_team_attack_strength", "away_team_gk_strength", "away_team_defence_strength", "away_team_midfield_strength", "away_team_attack_strength", "home_team_overall_strength", "away_team_overall_strength"
]
df_features = df_features.drop(columns=columns_to_drop)

ordered_columns = [
    'start_time', 'home_team', 'away_team', 'competition_id', 'match_importance',
    'average_home_goals_scored', 'average_home_goals_conceded', 
    'average_home_win_rate', 'average_home_draw_rate', 'average_home_clean_sheets',
    'home_momentum',
    'average_away_goals_scored', 'average_away_goals_conceded',
    'average_away_win_rate', 'average_away_draw_rate', 'average_away_clean_sheets',
    'away_momentum',
    'goals_scored_difference', 'goals_conceded_difference',
    'win_rate_difference', 'squad_strength_difference',
    'fatigue_difference', 'h2h_points_difference',
    'clean_sheets_difference', 'h2h_goals_difference',
    'h2h_clean_sheets_difference', 'momentum_difference',
    'home_goals', 'away_goals'
]

# Automatically move 'home_goals' and 'away_goals' to the end
# target_columns = ["home_goals", "away_goals"]
# feature_columns = [col for col in df_features.columns if col not in target_columns]
# df_features = df_features[feature_columns + target_columns]

# Save preprocessed features
df_features.to_csv('sportradar/AI/processed_data/test_preprocessed_basic_features.csv', index=False)

print("Preprocessed basic features saved!")
