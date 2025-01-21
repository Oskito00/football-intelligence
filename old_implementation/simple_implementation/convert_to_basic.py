import pandas as pd

# Read the CSV file
df = pd.read_csv('sportradar/AI/preprocessed_features.csv')

# Select only the columns you want
selected_columns = [
    'start_time',
    'home_team',
    'away_team',
    'competition_id',
    'goals_scored_difference',
    'goals_conceded_difference',
    'win_rate_difference',
    'home_goals',
    'away_goals'
]

# Create new dataframe with only selected columns
df_filtered = df[selected_columns]

# Save to new CSV file
df_filtered.to_csv('sportradar/AI/preprocessed_features_basic.csv', index=False)