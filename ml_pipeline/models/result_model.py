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
        """Create a CNN model for match prediction with form data"""
        # Input for form data (10 matches x 5 features for each team)
        home_form_input = layers.Input(shape=(10, 5), name='home_form')
        away_form_input = layers.Input(shape=(10, 5), name='away_form')
        
        # Input for existing features
        existing_features_input = layers.Input(shape=(params.get('num_existing_features', 20),), name='existing_features')
        
        # Process home team form
        home_form = layers.Conv1D(32, kernel_size=3, activation='relu')(home_form_input)
        home_form = layers.MaxPooling1D(2)(home_form)
        home_form = layers.Conv1D(64, kernel_size=2, activation='relu')(home_form)
        home_form = layers.MaxPooling1D(2)(home_form)
        home_form = layers.Flatten()(home_form)
        
        # Process away team form
        away_form = layers.Conv1D(32, kernel_size=3, activation='relu')(away_form_input)
        away_form = layers.MaxPooling1D(2)(away_form)
        away_form = layers.Conv1D(64, kernel_size=2, activation='relu')(away_form)
        away_form = layers.MaxPooling1D(2)(away_form)
        away_form = layers.Flatten()(away_form)
        
        # Combine all features
        combined = layers.Concatenate()([existing_features_input, home_form, away_form])
        
        # Dense layers
        x = layers.Dense(256, activation='relu')(combined)
        x = layers.Dropout(params.get('dropout_rate', 0.3))(x)
        x = layers.Dense(128, activation='relu')(x)
        x = layers.Dropout(params.get('dropout_rate', 0.3))(x)
        
        # Output layer
        output = layers.Dense(3, activation='softmax')(x)  # 3 classes: home win, draw, away win
        
        # Create model
        model = models.Model(
            inputs=[existing_features_input, home_form_input, away_form_input],
            outputs=output
        )
        
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
                'features': {
                    'existing_features': X_train_cnn['existing_features'].shape[1],
                    'form_features': X_train_cnn['home_form'].shape[1:]
                },
                'training_history': history.history
            }
        else:
            self.model.fit(X_train, y_train)
            return {
                'algorithm': algorithm,
                'training_samples': len(X_train),
                'features': len(X_train.columns)
            }
    
    def _reshape_for_cnn(self, X: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Reshape data for CNN input including form data"""
        # Extract form data
        home_form = np.stack(X['home_form'].values)  # Shape: (n_samples, 10, 5)
        away_form = np.stack(X['away_form'].values)  # Shape: (n_samples, 10, 5)
        
        # Extract existing features
        existing_features = X.drop(['home_form', 'away_form'], axis=1).values
        
        return {
            'existing_features': existing_features,
            'home_form': home_form,
            'away_form': away_form
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