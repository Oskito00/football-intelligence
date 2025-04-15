import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.model_selection import KFold
import numpy as np
from sklearn.metrics import classification_report


def create_data_splits(data, test_size=50, random_seed=42):
    """
    Split data into train, dev, and test sets.
    - Test set: Most recent test_size matches
    - Remaining data split randomly into train (80%) and dev (20%)
    
    Args:
        data: Either a pandas DataFrame or a path to a CSV file
        test_size: Number of most recent matches for test set
        random_seed: Random seed for reproducibility
    """
    # Handle input data
    if isinstance(data, str):
        df = pd.read_csv(data)
    else:
        df = data.copy()
    
    # Convert start_time to datetime and sort
    df['start_time'] = pd.to_datetime(df['start_time'])
    df = df.sort_values('start_time')
    
    # Split into historical and test data
    test_data = df.tail(test_size).copy()
    historical_data = df.iloc[:-test_size].copy()
    
    # Randomly split historical data into train and dev
    train_data, dev_data = train_test_split(
        historical_data,
        test_size=0.2,
        random_state=random_seed
    )
    
    print(f"Data split sizes:")
    print(f"Train: {len(train_data)} matches")
    print(f"Dev:   {len(dev_data)} matches")
    print(f"Test:  {len(test_data)} matches")
    print(f"\nTest set date range: {test_data['start_time'].min()} to {test_data['start_time'].max()}")
    
    return train_data, dev_data, test_data


def perform_cross_validation(X, y, model, scaler, n_folds=5):
    """Perform k-fold cross validation with scaling, return train and dev scores"""
    kf = KFold(n_splits=n_folds, shuffle=True, random_state=42)
    train_scores = []
    dev_scores = []
    
    for fold, (train_idx, val_idx) in enumerate(kf.split(X), 1):
        X_fold_train, X_fold_val = X.iloc[train_idx], X.iloc[val_idx]
        y_fold_train, y_fold_val = y.iloc[train_idx], y.iloc[val_idx]
        
        # Scale features
        X_fold_train_scaled = scaler.fit_transform(X_fold_train)
        X_fold_val_scaled = scaler.transform(X_fold_val)
        
        # Train and evaluate
        model.fit(X_fold_train_scaled, y_fold_train)
        train_score = model.score(X_fold_train_scaled, y_fold_train)
        dev_score = model.score(X_fold_val_scaled, y_fold_val)
        
        train_scores.append(train_score)
        dev_scores.append(dev_score)
    
    return (np.mean(train_scores), np.std(train_scores)), (np.mean(dev_scores), np.std(dev_scores))


def perform_cross_validation_with_metrics(X, y, model, scaler, n_folds=5):
    """Cross validation with classification metrics for each fold"""
    kf = KFold(n_splits=n_folds, shuffle=True, random_state=42)
    fold_reports = []
    
    for fold, (train_idx, val_idx) in enumerate(kf.split(X), 1):
        # Split and scale data
        X_fold_train, X_fold_val = X.iloc[train_idx], X.iloc[val_idx]
        y_fold_train, y_fold_val = y.iloc[train_idx], y.iloc[val_idx]
        
        X_fold_train_scaled = scaler.fit_transform(X_fold_train)
        X_fold_val_scaled = scaler.transform(X_fold_val)
        
        # Train and predict
        model.fit(X_fold_train_scaled, y_fold_train)
        y_pred = model.predict(X_fold_val_scaled)
        
        # Get metrics
        fold_report = classification_report(y_fold_val, y_pred, output_dict=True)
        fold_reports.append(fold_report)
    
    # Average metrics across folds
    avg_report = {}
    std_report = {}
    for class_label in ['0', '1', '2']:  # Home, Draw, Away
        avg_report[class_label] = {
            metric: np.mean([fold[class_label][metric] for fold in fold_reports])
            for metric in ['precision', 'recall', 'f1-score']
        }
        std_report[class_label] = {
            metric: np.std([fold[class_label][metric] for fold in fold_reports])
            for metric in ['precision', 'recall', 'f1-score']
        }
    
    return avg_report, std_report