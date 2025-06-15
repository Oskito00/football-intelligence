"""
Evaluation utilities for model predictions
Provides metrics, visualization, and analysis tools
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_auc_score, log_loss
)
import matplotlib.pyplot as plt
import seaborn as sns


def evaluate_model(model, X_test: pd.DataFrame, y_test: pd.Series, 
                  config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive model evaluation
    
    Args:
        model: Trained model instance
        X_test: Test features
        y_test: Test targets
        config: Configuration dictionary
        
    Returns:
        Dictionary with evaluation results
    """
    # Get predictions
    y_pred = model.predict(X_test)
    
    # Basic metrics
    results = {
        'accuracy': accuracy_score(y_test, y_pred),
        'precision_macro': precision_score(y_test, y_pred, average='macro'),
        'recall_macro': recall_score(y_test, y_pred, average='macro'),
        'f1_macro': f1_score(y_test, y_pred, average='macro'),
    }
    
    # Class-wise metrics
    results['precision_by_class'] = precision_score(y_test, y_pred, average=None)
    results['recall_by_class'] = recall_score(y_test, y_pred, average=None)
    results['f1_by_class'] = f1_score(y_test, y_pred, average=None)
    
    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    results['confusion_matrix'] = cm.tolist()
    
    # Classification report
    results['classification_report'] = classification_report(y_test, y_pred, output_dict=True)
    
    # ROC AUC for multiclass if probabilities available
    if hasattr(model, 'predict_proba'):
        try:
            y_proba = model.predict_proba(X_test)
            results['roc_auc_macro'] = roc_auc_score(y_test, y_proba, multi_class='ovr', average='macro')
            results['log_loss'] = log_loss(y_test, y_proba)
        except:
            results['roc_auc_macro'] = None
            results['log_loss'] = None
    
    return results


def plot_confusion_matrix(y_true: pd.Series, y_pred: np.ndarray, 
                         class_names: Optional[List[str]] = None,
                         save_path: Optional[str] = None) -> plt.Figure:
    """
    Plot confusion matrix
    
    Args:
        y_true: True labels
        y_pred: Predicted labels
        class_names: Optional class names for labels
        save_path: Optional path to save the plot
        
    Returns:
        Matplotlib figure
    """
    cm = confusion_matrix(y_true, y_pred)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Plot heatmap
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax,
                xticklabels=class_names or range(len(cm)),
                yticklabels=class_names or range(len(cm)))
    
    ax.set_xlabel('Predicted')
    ax.set_ylabel('Actual')
    ax.set_title('Confusion Matrix')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


def plot_feature_importance(importance_df: pd.DataFrame, 
                           top_n: int = 20,
                           save_path: Optional[str] = None) -> plt.Figure:
    """
    Plot feature importance
    
    Args:
        importance_df: DataFrame with feature names and importance scores
        top_n: Number of top features to show
        save_path: Optional path to save the plot
        
    Returns:
        Matplotlib figure
    """
    # Get top N features
    top_features = importance_df.head(top_n)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Create horizontal bar plot
    bars = ax.barh(range(len(top_features)), top_features['importance'])
    ax.set_yticks(range(len(top_features)))
    ax.set_yticklabels(top_features['feature'])
    ax.set_xlabel('Importance')
    ax.set_title(f'Top {top_n} Feature Importance')
    
    # Invert y-axis to show highest importance at top
    ax.invert_yaxis()
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


def analyze_prediction_errors(y_true: pd.Series, y_pred: np.ndarray, 
                             features: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze prediction errors to identify patterns
    
    Args:
        y_true: True labels
        y_pred: Predicted labels
        features: Feature DataFrame
        
    Returns:
        Dictionary with error analysis results
    """
    # Create error DataFrame
    errors_df = pd.DataFrame({
        'true_label': y_true,
        'predicted_label': y_pred,
        'correct': y_true == y_pred
    })
    
    # Add feature data
    errors_df = pd.concat([errors_df, features], axis=1)
    
    # Calculate error rates by class
    error_by_class = {}
    for class_label in y_true.unique():
        class_mask = y_true == class_label
        error_rate = 1 - accuracy_score(y_true[class_mask], y_pred[class_mask])
        error_by_class[class_label] = error_rate
    
    # Most common misclassifications
    misclassifications = []
    for true_label in y_true.unique():
        for pred_label in np.unique(y_pred):
            if true_label != pred_label:
                count = ((y_true == true_label) & (y_pred == pred_label)).sum()
                if count > 0:
                    misclassifications.append({
                        'true_label': true_label,
                        'predicted_label': pred_label,
                        'count': count,
                        'percentage': count / len(y_true) * 100
                    })
    
    # Sort by count
    misclassifications = sorted(misclassifications, key=lambda x: x['count'], reverse=True)
    
    return {
        'error_by_class': error_by_class,
        'most_common_errors': misclassifications[:10],  # Top 10
        'total_errors': (y_true != y_pred).sum(),
        'error_rate': 1 - accuracy_score(y_true, y_pred)
    } 