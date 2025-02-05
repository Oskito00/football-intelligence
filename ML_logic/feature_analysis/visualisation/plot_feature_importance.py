from matplotlib import pyplot as plt
import numpy as np
import pandas as pd

from ML_logic.models.scripts.logistic_regression import multi_label_logistic_regression
from ML_logic.models.scripts.random_forest import multi_label_random_forest


def analyze_feature_importance(model, feature_names):
    """Analyze and plot feature importance"""
    importances = np.abs(model.coef_).mean(axis=0)
    
    # Ensure lengths match
    if len(feature_names) != len(importances):
        raise ValueError(f"Feature names length ({len(feature_names)}) doesn't match importance length ({len(importances)})")
    
    feature_importance = pd.DataFrame({
        'feature': feature_names,
        'importance': importances
    })
    
    # Sort by importance
    feature_importance = feature_importance.sort_values('importance', ascending=False)
    
    # Plot top 20 features
    plt.figure(figsize=(12, 8))
    plt.bar(range(40), feature_importance['importance'][:40])
    plt.xticks(range(40), feature_importance['feature'][:40], rotation=45, ha='right')
    plt.title('Top 40 Most Important Features')
    plt.tight_layout()
    plt.show()
    
    return feature_importance

def plot_feature_importance(importance_df, n_features=20):
    """Plot top n features by importance"""
    plt.figure(figsize=(12, 8))
    plt.bar(range(n_features), importance_df['importance'][:n_features])
    plt.xticks(range(n_features), importance_df['feature'][:n_features], rotation=45, ha='right')
    plt.title(f'Top {n_features} Most Important Features')
    plt.tight_layout()
    plt.show()

def analyze_specific_features(importance_df):
    """Analyze importance of specific features"""
    
    features_of_interest = [
        'home_team_midfield_strength', 'away_team_overall_strength',
        'pass_effectiveness_difference', 'home_team_defence_strength',
        'home_team_overall_strength', 'conversion_rate_difference',
        'away_team_attack_strength', 'home_team_gk_strength',
        'shot_accuracy_difference', 'h2h_goals_difference',
        'h2h_avg_draw_rate', 'away_team_midfield_strength',
        'home_team_attack_strength', 'away_team_defence_strength',
        'defensive_success_difference', 'h2h_clean_sheets_difference',
        'form_similarity', 'h2h_points_difference', 'away_team_gk_strength'
    ]
    
    # Filter and sort specific features
    specific_features = importance_df[importance_df['feature'].isin(features_of_interest)]
    specific_features = specific_features.sort_values('importance', ascending=False)
    
    # Plot specific features
    plt.figure(figsize=(12, 8))
    plt.bar(range(len(specific_features)), specific_features['importance'])
    plt.xticks(range(len(specific_features)), specific_features['feature'], rotation=45, ha='right')
    plt.title('Importance of Selected Features')
    plt.tight_layout()
    plt.show()
    
    print("\nRankings of Selected Features:")
    for idx, row in specific_features.iterrows():
        overall_rank = importance_df.index.get_loc(idx) + 1
        print(f"{row['feature']:<30} {row['importance']:.4f} (Rank: {overall_rank})")



if __name__ == "__main__":
    model, train_scores, val_scores, importance_df, selected_features = multi_label_logistic_regression()
    analyze_specific_features(importance_df)