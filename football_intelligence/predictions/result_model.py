"""
Result prediction model implementation
Predicts match outcomes (home win, draw, away win)
"""

from typing import Dict, Any
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
import numpy as np

from football_intelligence.predictions.base_model import BaseModel


class ResultModel(BaseModel):
    """
    Football match result prediction model
    Supports multiple algorithms: XGBoost, Random Forest, Logistic Regression
    """

    def create_model(self) -> Any:
        """Create the ML model based on config"""
        algorithm = self.config['model']['algorithm'].lower()
        params = self.get_model_params()

        if algorithm == 'xgboost':
            import xgboost as xgb

            # Enable categorical support for XGBoost
            params['enable_categorical'] = True
            return xgb.XGBClassifier(**params)
        elif algorithm == 'random_forest':
            return RandomForestClassifier(**params)
        elif algorithm == 'logistic_regression':
            return LogisticRegression(**params)
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

    def get_model_params(self) -> Dict[str, Any]:
        """Get model hyperparameters from config"""
        base_params = self.config['model'].get('hyperparameters', {})
        algorithm = self.config['model']['algorithm'].lower()

        # Add algorithm-specific defaults
        if algorithm == 'xgboost':
            defaults = {
                'objective': 'multi:softprob',
                'eval_metric': 'mlogloss',
                'num_class': 3,  # home win, draw, away win
                'random_state': 42
            }
        elif algorithm == 'random_forest':
            defaults = {
                'n_estimators': 100,
                'random_state': 42,
                'n_jobs': -1
            }
        elif algorithm == 'logistic_regression':
            defaults = {
                'multi_class': 'multinomial',
                'solver': 'lbfgs',
                'random_state': 42,
                'max_iter': 1000
            }
        else:
            defaults = {}

        # Merge with config params
        params = {**defaults, **base_params}
        return params

    def _train_basic(self, X_train: pd.DataFrame, y_train: pd.Series) -> Dict[str, Any]:
        """Basic training implementation"""
        algorithm = self.config['model']['algorithm'].lower()

        self.model.fit(X_train, y_train)
        return {
            'algorithm': algorithm,
            'training_samples': len(X_train),
            'features': len(X_train.columns)
        }

    def _train_with_validation(self, X_train: pd.DataFrame, y_train: pd.Series,
                              X_val: pd.DataFrame, y_val: pd.Series) -> Dict[str, Any]:
        """Training with validation for early stopping (XGBoost only)"""
        algorithm = self.config['model']['algorithm'].lower()

        if algorithm == 'xgboost':
            # XGBoost with early stopping
            self.model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                early_stopping_rounds=self.config.get('training', {}).get('early_stopping', {}).get('patience', 10),
                verbose=False
            )

            return {
                'algorithm': algorithm,
                'training_samples': len(X_train),
                'validation_samples': len(X_val),
                'best_iteration': self.model.best_iteration,
                'best_score': self.model.best_score
            }
        else:
            # Fall back to basic training for other algorithms
            return self._train_basic(X_train, y_train)
