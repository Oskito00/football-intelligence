import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import KFold
from sklearn.metrics import accuracy_score, classification_report

def multi_label_random_forest(n_folds=10, n_estimators=100, top_n_features=10):
    """Train Random Forest using only top N most important features"""
    
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

    basic_df["outcome"] = [2 if h > a else (1 if h == a else 0) 
                    for h, a in zip(basic_df["home_goals"], basic_df["away_goals"])]
    
    # First split off test set
    train_dev_data, _, test_data = create_data_splits(basic_df, test_size=500)
    
    # Setup k-fold cross validation
    kf = KFold(n_splits=n_folds, shuffle=True, random_state=125)
    metadata_cols = ["start_time", "home_team", "away_team", "home_goals", "away_goals", "outcome"]
    print(f"Number of features: {len(train_dev_data.drop(columns=metadata_cols).columns)}")
    
    # Lists to store results
    fold_train_scores = []
    fold_val_scores = []
    all_feature_importances = []
    
    # Perform k-fold cross validation
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
        
        # Train model
        model = RandomForestClassifier(
            n_estimators=50,
            max_depth=7,
            min_samples_split=7,
            min_samples_leaf=3,
            random_state=42)
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
        all_feature_importances.append(model.feature_importances_)
    
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
    
    # Select top N features
    top_features = importance_df.head(top_n_features)['feature'].tolist()
    print(f"\nTop {top_n_features} features selected:")
    for idx, feature in enumerate(top_features, 1):
        print(f"{idx}. {feature}")
    
    # Prepare final training data with selected features
    X_train_dev_selected = train_dev_data[top_features]
    y_train_dev = train_dev_data["outcome"]
    X_test_selected = test_data[top_features]
    y_test = test_data["outcome"]
    
    # Train final model using only top features
    final_model = RandomForestClassifier(n_estimators=n_estimators, random_state=42)
    final_model.fit(X_train_dev_selected, y_train_dev)
    
    # Evaluate on test set with selected features
    test_preds = final_model.predict(X_test_selected)
    test_acc = accuracy_score(y_test, test_preds)
    
    print("\nFinal Test Set Results (Top Features Only):")
    print(f"Test Accuracy: {test_acc:.3f}")
    print("\nTest Set Classification Report:")
    print(classification_report(y_test, test_preds, 
                              target_names=['Home Win', 'Draw', 'Away Win']))
    
    return final_model, fold_train_scores, fold_val_scores, importance_df

#****************************************
#HELPER FUNCTIONS
#****************************************

def create_data_splits(df, test_size=500):
    """
    Split the data into train+dev and test sets.
    """
    test_data = df.sample(n=test_size, random_state=42)
    train_dev_data = df.drop(test_data.index)
    return train_dev_data, None, test_data

if __name__ == "__main__":
    model, train_scores, val_scores, importance_df = multi_label_random_forest()