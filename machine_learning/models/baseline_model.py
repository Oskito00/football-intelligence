import numpy as np
from sklearn.metrics import classification_report, confusion_matrix
from helpers.machine_learning.load_data import load_csv_data


def baseline_model():
    # Load data
    df = load_csv_data('data/api_football/processed/elo_features.csv')
    #drop all columns but home_team_elo_K30 and away_team_elo_K30
    df = df[['home_team_elo_K30', 'away_team_elo_K30', 'home_team_score', 'away_team_score']]
    # Create result column based on score comparison
    df['result'] = np.where(
        df['home_team_score'] > df['away_team_score'], 'home_win',
        np.where(df['home_team_score'] < df['away_team_score'], 'away_win', 'draw')
    )
    X = df[['home_team_elo_K30', 'away_team_elo_K30']]
    y = df['result']

    # Test different threshold values
    k_values = [10,0,2,5,10,20, 25, 30, 35, 40,50,60,70,80,90,100]  # Different threshold values to try
    best_k = 30
    best_acc = 0
    
    # Find best K value
    for k in k_values:
        temp_pred = np.where(X['home_team_elo_K30'] > X['away_team_elo_K30'] + k, 'home_win',
            np.where(X['home_team_elo_K30'] < X['away_team_elo_K30'] - k, 'away_win', 'draw')
        )
        acc = np.mean(y == temp_pred)
        if acc > best_acc:
            best_acc = acc
            best_k = k
            
    print(f"Best threshold K: {best_k} (accuracy: {best_acc:.3f})")
    
    # Final prediction with best K
    y_pred = np.where(X['home_team_elo_K30'] > X['away_team_elo_K30'] + best_k, 'home_win',
        np.where(X['home_team_elo_K30'] < X['away_team_elo_K30'] - best_k, 'away_win', 'draw')
    )

    accuracy = np.mean(y == y_pred)
    print(f"Accuracy: {accuracy:.2f}")

    print(classification_report(y, y_pred))
    print(confusion_matrix(y, y_pred))

if __name__ == "__main__":
    baseline_model()