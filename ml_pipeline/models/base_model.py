from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, classification_report
import logging


class BaseModel(ABC):
    """
    Abstract base class for all ML models in the pipeline
    Provides common interface and functionality
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model = None
        self.preprocessor = None
        self.label_encoder = None
        self.is_trained = False
        self.feature_names = None
        self.target_name = None
        
        # Setup logging
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def create_model(self) -> Any:
        """
        Create and return the ML model instance
        Must be implemented by subclasses
        """
        pass
    
    @abstractmethod
    def get_model_params(self) -> Dict[str, Any]:
        """
        Get model hyperparameters from config
        Must be implemented by subclasses
        """
        pass
    
    def prepare_data(self, X: pd.DataFrame, y: pd.Series, 
                    test_size: float = 0.2, random_state: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        Prepare data for training including train/test split and preprocessing
        
        Args:
            X: Feature DataFrame
            y: Target Series
            test_size: Proportion of data for testing
            random_state: Random seed for reproducibility
            
        Returns:
            X_train, X_test, y_train, y_test
        """
        self.logger.info(f"Preparing data with {len(X)} samples and {len(X.columns)} features")
        
        # Store feature names and target name
        self.feature_names = list(X.columns)
        self.target_name = y.name if hasattr(y, 'name') else 'target'
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, 
            stratify=y if self._is_classification_task() else None
        )
        
        # Handle categorical targets for classification
        if self._is_classification_task() and y.dtype == 'object':
            self.label_encoder = LabelEncoder()
            y_train = pd.Series(self.label_encoder.fit_transform(y_train), index=y_train.index)
            y_test = pd.Series(self.label_encoder.transform(y_test), index=y_test.index)
        
        self.logger.info(f"Train set: {len(X_train)} samples, Test set: {len(X_test)} samples")
        return X_train, X_test, y_train, y_test
    
    def preprocess_features(self, X_train: pd.DataFrame, X_test: Optional[pd.DataFrame] = None) -> Tuple[pd.DataFrame, Optional[pd.DataFrame]]:
        """
        Preprocess features (scaling, encoding, etc.)
        
        Args:
            X_train: Training features
            X_test: Test features (optional)
            
        Returns:
            Preprocessed X_train and X_test
        """
        preprocessing_config = self.config.get('preprocessing', {})
        
        if preprocessing_config.get('scale_features', True):
            self.logger.info("Applying feature scaling")
            self.preprocessor = StandardScaler()
            
            # Fit on training data only
            X_train_scaled = pd.DataFrame(
                self.preprocessor.fit_transform(X_train),
                columns=X_train.columns,
                index=X_train.index
            )
            
            X_test_scaled = None
            if X_test is not None:
                X_test_scaled = pd.DataFrame(
                    self.preprocessor.transform(X_test),
                    columns=X_test.columns,
                    index=X_test.index
                )
            
            return X_train_scaled, X_test_scaled
        
        return X_train, X_test
    
    def train(self, X_train: pd.DataFrame, y_train: pd.Series, 
              X_val: Optional[pd.DataFrame] = None, y_val: Optional[pd.Series] = None) -> Dict[str, Any]:
        """
        Train the model
        
        Args:
            X_train: Training features
            y_train: Training targets
            X_val: Validation features (optional)
            y_val: Validation targets (optional)
            
        Returns:
            Training history/metrics
        """
        if self.model is None:
            self.model = self.create_model()
        
        self.logger.info("Starting model training")
        
        # Train the model
        if X_val is not None and y_val is not None:
            # Use validation data if provided
            training_result = self._train_with_validation(X_train, y_train, X_val, y_val)
        else:
            training_result = self._train_basic(X_train, y_train)
        
        self.is_trained = True
        self.logger.info("Model training completed")
        
        return training_result
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Make predictions
        
        Args:
            X: Features to predict on
            
        Returns:
            Predictions
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        # Apply same preprocessing as training
        if self.preprocessor is not None:
            X_processed = pd.DataFrame(
                self.preprocessor.transform(X),
                columns=X.columns,
                index=X.index
            )
        else:
            X_processed = X
        
        predictions = self.model.predict(X_processed)
        
        # Convert back to original labels if label encoder was used
        if self.label_encoder is not None:
            predictions = self.label_encoder.inverse_transform(predictions)
        
        return predictions
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict class probabilities (for classification models)
        
        Args:
            X: Features to predict on
            
        Returns:
            Class probabilities
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        if not hasattr(self.model, 'predict_proba'):
            raise ValueError("Model does not support probability predictions")
        
        # Apply same preprocessing as training
        if self.preprocessor is not None:
            X_processed = pd.DataFrame(
                self.preprocessor.transform(X),
                columns=X.columns,
                index=X.index
            )
        else:
            X_processed = X
        
        return self.model.predict_proba(X_processed)
    
    def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, Any]:
        """
        Evaluate model performance
        
        Args:
            X_test: Test features
            y_test: Test targets
            
        Returns:
            Dictionary of evaluation metrics
        """
        predictions = self.predict(X_test)
        
        if self._is_classification_task():
            return self._evaluate_classification(y_test, predictions)
        else:
            return self._evaluate_regression(y_test, predictions)
    
    @abstractmethod
    def _train_basic(self, X_train: pd.DataFrame, y_train: pd.Series) -> Dict[str, Any]:
        """Basic training implementation - must be overridden"""
        pass
    
    def _train_with_validation(self, X_train: pd.DataFrame, y_train: pd.Series,
                              X_val: pd.DataFrame, y_val: pd.Series) -> Dict[str, Any]:
        """Training with validation - can be overridden for early stopping, etc."""
        return self._train_basic(X_train, y_train)
    
    def _is_classification_task(self) -> bool:
        """Determine if this is a classification task"""
        return self.config.get('task_type', 'classification') == 'classification'
    
    def _evaluate_classification(self, y_true: pd.Series, y_pred: np.ndarray) -> Dict[str, Any]:
        """Evaluate classification performance"""
        accuracy = accuracy_score(y_true, y_pred)
        report = classification_report(y_true, y_pred, output_dict=True)
        
        return {
            'accuracy': accuracy,
            'classification_report': report,
            'task_type': 'classification'
        }
    
    def _evaluate_regression(self, y_true: pd.Series, y_pred: np.ndarray) -> Dict[str, Any]:
        """Evaluate regression performance"""
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
        
        mse = mean_squared_error(y_true, y_pred)
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)
        
        return {
            'mse': mse,
            'mae': mae,
            'r2': r2,
            'rmse': np.sqrt(mse),
            'task_type': 'regression'
        }
    
    def get_feature_importance(self) -> Optional[pd.DataFrame]:
        """Get feature importance if supported by the model"""
        if not self.is_trained:
            return None
        
        if hasattr(self.model, 'feature_importances_'):
            importance_df = pd.DataFrame({
                'feature': self.feature_names,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)
            return importance_df
        
        return None 