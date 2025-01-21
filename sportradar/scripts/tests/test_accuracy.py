import pandas as pd

def determine_actual_outcome(row):
    """Determine the actual match outcome based on goals scored."""
    if row['home_goals'] > row['away_goals']:
        return 'Home Win'
    elif row['home_goals'] < row['away_goals']:
        return 'Away Win'
    else:
        return 'Draw'

def calculate_prediction_accuracy(predictions_file, results_file):
    # Read the predictions and results CSV files
    predictions_df = pd.read_csv(predictions_file)
    results_df = pd.read_csv(results_file)
    
    # Ensure we have matching columns for merging
    predictions_df['match_key'] = predictions_df['start_time'] + predictions_df['home_team'] + predictions_df['away_team']
    results_df['match_key'] = results_df['start_time'] + results_df['home_team'] + results_df['away_team']
    
    # Merge predictions with actual results
    merged_df = pd.merge(predictions_df, results_df[['match_key', 'home_goals', 'away_goals']], 
                        on='match_key', how='inner')
    
    # Calculate actual outcomes
    merged_df['actual_outcome'] = merged_df.apply(determine_actual_outcome, axis=1)
    
    # Calculate accuracy
    total_predictions = len(merged_df)
    correct_predictions = (merged_df['predicted_outcome'] == merged_df['actual_outcome']).sum()
    accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0
    
    # Create detailed results
    results = {
        'total_matches': total_predictions,
        'correct_predictions': correct_predictions,
        'accuracy': accuracy,
        'detailed_results': merged_df[['start_time', 'home_team', 'away_team', 
                                     'predicted_outcome', 'actual_outcome',
                                     'home_goals', 'away_goals']]
    }
    
    return results

def print_results(results):
    """Print the analysis results in a readable format."""
    print(f"\nPrediction Analysis Results:")
    print(f"Total Matches Analyzed: {results['total_matches']}")
    print(f"Correct Predictions: {results['correct_predictions']}")
    print(f"Accuracy: {results['accuracy']:.2%}")
    
    print("\nDetailed Results:")
    print(results['detailed_results'].to_string(index=False))

if __name__ == "__main__":
    predictions_file = "sportradar/AI/match_predictions.csv"
    results_file = "sportradar/scripts/tests/results.csv"  # You'll need to provide this file with actual scores
    
    try:
        results = calculate_prediction_accuracy(predictions_file, results_file)
        print_results(results)
    except Exception as e:
        print(f"An error occurred: {str(e)}")