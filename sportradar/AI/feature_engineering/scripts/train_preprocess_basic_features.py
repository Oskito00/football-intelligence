import pandas as pd
from sklearn.preprocessing import LabelEncoder
import joblib  # for saving the LabelEncoder

# Load and preprocess data
df = pd.read_csv('sportradar/data/processed_data/training_data_basic.csv')

# Drop non-feature columns
df_features = df.drop(["fixture_id"], axis=1)

# Label encode competition_id and referee_id
competition_encoder = LabelEncoder()
referee_encoder = LabelEncoder()

df_features["competition_id"] = competition_encoder.fit_transform(df_features["competition_id"])
# df_features["referee_id"] = referee_encoder.fit_transform(df_features["referee_id"])

# Save the label encoders for future use
joblib.dump(competition_encoder, 'sportradar/AI/feature_engineering/jobs/competition_id_encoder.joblib')
joblib.dump(referee_encoder, 'sportradar/AI/feature_engineering/jobs/referee_id_encoder.joblib')

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

# Drop redundant original features, but keep core performance metrics
columns_to_drop = [
    # Keep these core metrics
    # "average_home_goals_scored", "average_away_goals_scored",
    # "average_home_goals_conceded", "average_away_goals_conceded",
    # "average_home_win_rate", "average_away_win_rate",
    # "average_home_draw_rate", "average_away_draw_rate",
    # "average_home_clean_sheets", "average_away_clean_sheets",
    # "home_momentum", "away_momentum",
    # "home_elo_rating", "away_elo_rating",
    
    # Drop these comparison metrics
    "home_fatigue", "away_fatigue",

]
df_features = df_features.drop(columns=columns_to_drop)

# Automatically move 'home_goals' and 'away_goals' to the end
target_columns = ["home_goals", "away_goals"]
feature_columns = [col for col in df_features.columns if col not in target_columns]
df_features = df_features[feature_columns + target_columns]

# Save preprocessed features
df_features.to_csv('sportradar/AI/processed_data/preprocessed_basic_features.csv', index=False)

print("Preprocessed features saved!")