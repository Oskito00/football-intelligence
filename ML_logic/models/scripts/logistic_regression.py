from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, KFold
from sklearn.metrics import accuracy_score, classification_report
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import spearmanr

from ML_logic.helpers.helpers import create_data_splits

def multi_label_logistic_regression(n_folds=10):
    """Train a 3-class classifier with k-fold cross validation"""
    
    # Load and prepare data
    advanced_df = pd.read_csv("Data/processed/preprocessed_features.csv")
    basic_df = pd.read_csv("Data/processed/preprocessed_basic_features.csv")

    # Check for missing features
    basic_features = basic_df.columns
    advanced_features = advanced_df.columns
    missing_features = set(advanced_features) - set(basic_features)
    print(f"Missing features in preprocessed_features: {missing_features}")
    if missing_features:
        print("List of missing features:")
        for feature in missing_features:
            print(f"- {feature}")

    advanced_df["outcome"] = [2 if h > a else (1 if h == a else 0) 
                    for h, a in zip(advanced_df["home_goals"], advanced_df["away_goals"])]
    
    # First split off test set
    train_dev_data, _, test_data = create_data_splits(advanced_df)
    
    # Setup k-fold cross validation on train+dev data
    kf = KFold(n_splits=n_folds, shuffle=True, random_state=125)
    metadata_cols = ["start_time", "home_team", "away_team", "home_goals", "away_goals", "outcome"]
    print(f"Number of features: {len(train_dev_data.drop(columns=metadata_cols).columns)}")

    
    # Lists to store results
    fold_train_scores = []
    fold_val_scores = []
    all_feature_importances = []
    
    # Perform k-fold cross validation on train+dev data
    for fold, (train_idx, val_idx) in enumerate(kf.split(train_dev_data), 1):
        print(f"\nFold {fold}/{n_folds}")
        
        # Split data
        train_data = train_dev_data.iloc[train_idx]
        val_data = train_dev_data.iloc[val_idx]
        
        # Prepare features
        X_train = train_data.drop(columns=metadata_cols)
        feature_names = X_train.columns
        y_train = train_data["outcome"]
        X_val = val_data.drop(columns=metadata_cols)
        y_val = val_data["outcome"]
        
        # Scale features
        scaler = StandardScaler()
        X_train = pd.DataFrame(scaler.fit_transform(X_train), columns=feature_names)
        X_val = pd.DataFrame(scaler.transform(X_val), columns=feature_names)
        
        # Train model
        model = LogisticRegression(multi_class='multinomial', solver='lbfgs', max_iter=1000)
        model.fit(X_train, y_train)
        
        # Evaluate
        train_preds = model.predict(X_train)
        val_preds = model.predict(X_val)
        
        train_acc = accuracy_score(y_train, train_preds)
        val_acc = accuracy_score(y_val, val_preds)
        
        fold_train_scores.append(train_acc)
        fold_val_scores.append(val_acc)
        
        print(f"Train Accuracy: {train_acc:.3f}")
        print(f"Validation Accuracy: {val_acc:.3f}")
        
        # Store feature importance
        importances = np.abs(model.coef_).mean(axis=0)
        all_feature_importances.append(importances)
    
    # Print average results
    print("\nOverall Results:")
    print(f"Average Train Accuracy: {np.mean(fold_train_scores):.3f} ± {np.std(fold_train_scores):.3f}")
    print(f"Average Validation Accuracy: {np.mean(fold_val_scores):.3f} ± {np.std(fold_val_scores):.3f}")
    
    # Average feature importance across folds
    avg_importances = np.mean(all_feature_importances, axis=0)
    importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance': avg_importances
    }).sort_values('importance', ascending=False)
    
    # Plot average feature importance
    plt.figure(figsize=(12, 8))
    plt.bar(range(20), importance_df['importance'][:20])
    plt.xticks(range(20), importance_df['feature'][:20], rotation=45, ha='right')
    plt.title('Top 20 Most Important Features (Averaged Across Folds)')
    plt.tight_layout()
    plt.show()
    
    print("\nTop 10 Most Important Features (Averaged Across Folds):")
    print(importance_df.head(10))
    
    # After k-fold CV, train final model on all train+dev data
    X_train_dev = train_dev_data.drop(columns=metadata_cols)
    y_train_dev = train_dev_data["outcome"]
    X_test = test_data.drop(columns=metadata_cols)
    y_test = test_data["outcome"]
    
    # Scale features
    scaler = StandardScaler()
    X_train_dev = pd.DataFrame(scaler.fit_transform(X_train_dev), columns=X_train_dev.columns)
    X_test = pd.DataFrame(scaler.transform(X_test), columns=X_test.columns)
    
    # Train final model
    final_model = LogisticRegression(multi_class='multinomial', solver='lbfgs', max_iter=1000)
    final_model.fit(X_train_dev, y_train_dev)
    
    # Evaluate on test set
    test_preds = final_model.predict(X_test)
    test_acc = accuracy_score(y_test, test_preds)
    
    print("\nFinal Test Set Results:")
    print(f"Test Accuracy: {test_acc:.3f}")
    print("\nTest Set Classification Report:")
    print(classification_report(y_test, test_preds, 
                              target_names=['Home Win', 'Draw', 'Away Win']))
        
    # After calculating feature importance
    print("\nChecking for correlated features...")
    X_train_dev = train_dev_data.drop(columns=metadata_cols)
    
    # Try different thresholds
    for threshold in [0.8, 0.7, 0.6]:
        print(f"\nChecking correlations with threshold {threshold}")
        high_corr = find_correlated_features(X_train_dev, threshold=threshold)
        
        if high_corr:
            print(f"\nHighly correlated feature pairs (threshold={threshold}):")
            for f1, f2, corr in high_corr:
                print(f"{f1} - {f2}: {corr:.3f}")
    
    # Select top features removing correlations
    selected_features = select_top_features(
        X_train_dev, 
        importance_df,
        n_features=10, 
        corr_threshold=0.8
    )
    
    # Prepare final data with selected features
    X_train_dev_selected = X_train_dev[selected_features]
    y_train_dev = train_dev_data["outcome"]
    X_test_selected = test_data[selected_features]
    y_test = test_data["outcome"]
    
    # Scale selected features
    scaler = StandardScaler()
    X_train_dev_selected = pd.DataFrame(scaler.fit_transform(X_train_dev_selected), 
                                      columns=selected_features)
    X_test_selected = pd.DataFrame(scaler.transform(X_test_selected), 
                                 columns=selected_features)
    
    # Train final model with selected features
    final_model = LogisticRegression(multi_class='multinomial', solver='lbfgs', max_iter=1000)
    final_model.fit(X_train_dev_selected, y_train_dev)
    
    # Final evaluation with selected features
    test_preds = final_model.predict(X_test_selected)
    test_acc = accuracy_score(y_test, test_preds)
    
    print("\nFinal Test Set Results (Selected Features):")
    print(f"Test Accuracy: {test_acc:.3f}")
    print("\nTest Set Classification Report:")
    print(classification_report(y_test, test_preds, 
                              target_names=['Home Win', 'Draw', 'Away Win']))

    return final_model, fold_train_scores, fold_val_scores, importance_df, selected_features

#****************************************************
#Helper functions
#****************************************************



def find_correlated_features(X, threshold=0.8):
    """
    Find highly correlated features using Spearman correlation
    Returns pairs of features with correlation above threshold
    """
    # Print shape and sample of data
    print(f"\nData shape: {X.shape}")
    
    # Calculate correlation matrix
    corr_matrix = X.corr(method='spearman')
    
    # Visualize correlation matrix
    plt.figure(figsize=(12, 8))
    sns.heatmap(corr_matrix, cmap='coolwarm', center=0)
    plt.title('Feature Correlation Matrix')
    plt.tight_layout()
    plt.show()
    
    # Try lower threshold to see if correlations exist
    high_corr_pairs = []
    
    for i in range(len(corr_matrix.columns)):
        for j in range(i+1, len(corr_matrix.columns)):
            correlation = abs(corr_matrix.iloc[i,j])
            if correlation > threshold:
                high_corr_pairs.append((
                    corr_matrix.columns[i],
                    corr_matrix.columns[j],
                    correlation
                ))
                
    # Print number of correlations found
    print(f"\nFound {len(high_corr_pairs)} correlations above {threshold}")
    
    return high_corr_pairs

def select_top_features(X, importance_df, n_features=10, corr_threshold=0.8):
    """
    Select top N features while removing highly correlated ones
    """
    # Get ordered features by importance
    ordered_features = importance_df['feature'].tolist()
    selected_features = []
    
    # Keep most important features that aren't highly correlated
    for feature in ordered_features:
        if len(selected_features) >= n_features:
            break
            
        # Check correlation with already selected features
        if not selected_features:
            selected_features.append(feature)
            continue
            
        X_selected = X[selected_features]
        corr = X_selected.corrwith(X[feature], method='spearman')
        
        if all(abs(c) < corr_threshold for c in corr):
            selected_features.append(feature)
    
    print(f"\nSelected {len(selected_features)} features:")
    for idx, feature in enumerate(selected_features, 1):
        print(f"{idx}. {feature}")
    
    return selected_features