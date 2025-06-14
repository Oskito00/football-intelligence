"""
Result prediction model implementation
Predicts match outcomes (home win, draw, away win)
"""

from typing import Dict, Any
import pandas as pd
import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
import tensorflow as tf
from tensorflow.keras import layers, models
import numpy as np

from ml_pipeline.models.base_model import BaseModel


class ResultModel(BaseModel):
    """
    Football match result prediction model
    Supports multiple algorithms: XGBoost, Random Forest, Logistic Regression, CNN
    """
    
    def create_model(self) -> Any:
        """Create the ML model based on config"""
        algorithm = self.config['model']['algorithm'].lower()
        params = self.get_model_params()
        
        if algorithm == 'xgboost':
            # Enable categorical support for XGBoost
            params['enable_categorical'] = True
            return xgb.XGBClassifier(**params)
        elif algorithm == 'random_forest':
            return RandomForestClassifier(**params)
        elif algorithm == 'logistic_regression':
            return LogisticRegression(**params)
        elif algorithm == 'cnn':
            return self._create_cnn_model(params)
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
    
    def _create_cnn_model(self, params: Dict[str, Any]) -> tf.keras.Model:
        """Create a CNN model for match prediction"""
        model = models.Sequential([
            # Input layer - reshape based on your data structure
            layers.Input(shape=params.get('input_shape', (None, None, 1))),
            
            # Convolutional layers
            *[layers.Conv2D(
                filters=params.get('filters', [32, 64, 128])[i],
                kernel_size=params.get('kernel_size', 3),
                activation='relu',
                padding='same'
            ) for i in range(params.get('num_conv_layers', 3))],
            
            # Pooling layer
            layers.MaxPooling2D(pool_size=(2, 2)),
            
            # Flatten layer
            layers.Flatten(),
            
            # Dense layers
            *[layers.Dense(
                units=params.get('dense_layers', [256, 128])[i],
                activation='relu'
            ) for i in range(len(params.get('dense_layers', [256, 128])))],
            
            # Dropout for regularization
            layers.Dropout(params.get('dropout_rate', 0.3)),
            
            # Output layer
            layers.Dense(3, activation='softmax')  # 3 classes: home win, draw, away win
        ])
        
        # Compile model
        model.compile(
            optimizer=params.get('optimizer', 'adam'),
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
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
        elif algorithm == 'cnn':
            defaults = {
                'input_shape': (None, None, 1),  # Adjust based on your data
                'num_conv_layers': 3,
                'filters': [32, 64, 128],
                'kernel_size': 3,
                'dense_layers': [256, 128],
                'dropout_rate': 0.3,
                'optimizer': 'adam',
                'batch_size': 32,
                'epochs': 50
            }
        else:
            defaults = {}
        
        # Merge with config params
        params = {**defaults, **base_params}
        return params
    
    def _train_basic(self, X_train: pd.DataFrame, y_train: pd.Series) -> Dict[str, Any]:
        """Basic training implementation"""
        algorithm = self.config['model']['algorithm'].lower()
        
        if algorithm == 'cnn':
            # Reshape data for CNN
            X_train_cnn = self._reshape_for_cnn(X_train)
            
            # Train CNN
            history = self.model.fit(
                X_train_cnn, y_train,
                batch_size=self.config['model']['hyperparameters'].get('batch_size', 32),
                epochs=self.config['model']['hyperparameters'].get('epochs', 50),
                verbose=0
            )
            
            return {
                'algorithm': algorithm,
                'training_samples': len(X_train),
                'features': X_train_cnn.shape[1:],
                'training_history': history.history
            }
        else:
            self.model.fit(X_train, y_train)
            return {
                'algorithm': algorithm,
                'training_samples': len(X_train),
                'features': len(X_train.columns)
            }
    
    def _reshape_for_cnn(self, X: pd.DataFrame) -> np.ndarray:
        """Reshape data for CNN input"""
        # This is a placeholder - you'll need to implement the actual reshaping
        # based on how you want to structure your data for CNN
        # Example: Convert features into a 2D grid
        n_samples = len(X)
        n_features = len(X.columns)
        grid_size = int(np.ceil(np.sqrt(n_features)))
        
        # Pad features to make a square grid
        padded_features = np.zeros((n_samples, grid_size, grid_size, 1))
        for i, col in enumerate(X.columns):
            row = i // grid_size
            col_idx = i % grid_size
            padded_features[:, row, col_idx, 0] = X[col].values
        
        return padded_features
    
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