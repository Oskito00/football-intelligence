import numpy as np
from sklearn.metrics import classification_report
from sklearn.model_selection import KFold


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