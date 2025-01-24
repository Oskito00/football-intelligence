import pandas as pd

# Load test data
test_df = pd.read_csv('sportradar/AI/processed_data/test_preprocessed_features.csv')

# Find rows with any NaN values
rows_with_nans = test_df[test_df.isna().any(axis=1)]

# Print the match details for these rows
for idx, row in rows_with_nans.iterrows():
    print(f"\nRow {idx}:")
    print(f"Match: {row['home_team']} vs {row['away_team']}")
    print(f"Date: {row['start_time']}")
    print("\nNaN values in columns:")
    nan_columns = row[row.isna()].index
    for col in nan_columns:
        print(f"- {col}")