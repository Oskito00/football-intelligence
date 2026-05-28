import pandas as pd
from pathlib import Path
from typing import Any, Dict, Optional
import json
from datetime import datetime


class ModelIO:
    """
    Input/Output utilities for saving and loading models, features, and metadata
    """

    def __init__(self, base_path: str = "models"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save_model(self, model: Any, model_name: str,
                   metadata: Optional[Dict] = None,
                   preprocessor: Optional[Any] = None) -> str:
        """
        Save model with metadata and optional preprocessor

        Args:
            model: Trained model object
            model_name: Name for the model
            metadata: Dictionary with model metadata
            preprocessor: Optional preprocessing pipeline

        Returns:
            Path to saved model directory
        """
        # Create model directory with timestamp
        import joblib

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_dir = self.base_path / f"{model_name}_{timestamp}"
        model_dir.mkdir(exist_ok=True)

        # Save model
        model_path = model_dir / "model.pkl"
        joblib.dump(model, model_path)

        # Save preprocessor if provided
        if preprocessor is not None:
            preprocessor_path = model_dir / "preprocessor.pkl"
            joblib.dump(preprocessor, preprocessor_path)

        # Save metadata
        if metadata is None:
            metadata = {}

        metadata.update({
            'model_name': model_name,
            'saved_at': timestamp,
            'model_type': type(model).__name__,
            'has_preprocessor': preprocessor is not None
        })

        metadata_path = model_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)

        # Create latest symlink
        latest_path = self.base_path / f"{model_name}_latest"
        if latest_path.exists():
            latest_path.unlink()
        latest_path.symlink_to(model_dir.name, target_is_directory=True)

        print(f"Model saved to: {model_dir}")
        return str(model_dir)

    def load_model(self, model_name: str, version: Optional[str] = None) -> Dict[str, Any]:
        """
        Load model with metadata and preprocessor

        Args:
            model_name: Name of the model
            version: Specific version timestamp, or None for latest

        Returns:
            Dictionary containing model, metadata, and preprocessor (if exists)
        """
        import joblib

        if version is None:
            model_dir = self.base_path / f"{model_name}_latest"
            if not model_dir.exists():
                raise FileNotFoundError(f"No latest model found for {model_name}")
        else:
            model_dir = self.base_path / f"{model_name}_{version}"
            if not model_dir.exists():
                raise FileNotFoundError(f"Model version {version} not found for {model_name}")

        # Load model
        model_path = model_dir / "model.pkl"
        model = joblib.load(model_path)

        # Load metadata
        metadata_path = model_dir / "metadata.json"
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)

        # Load preprocessor if exists
        preprocessor_path = model_dir / "preprocessor.pkl"
        preprocessor = None
        if preprocessor_path.exists():
            preprocessor = joblib.load(preprocessor_path)

        return {
            'model': model,
            'metadata': metadata,
            'preprocessor': preprocessor,
            'model_dir': str(model_dir)
        }

    def save_features(self, features: pd.DataFrame, feature_name: str,
                     metadata: Optional[Dict] = None) -> str:
        """
        Save feature dataset with metadata

        Args:
            features: Feature DataFrame
            feature_name: Name for the feature set
            metadata: Optional metadata dictionary

        Returns:
            Path to saved features
        """
        # Create features directory
        features_dir = Path("data") / "features"
        features_dir.mkdir(parents=True, exist_ok=True)

        # Save features
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        features_path = features_dir / f"{feature_name}_{timestamp}.parquet"
        features.to_parquet(features_path, index=False)

        # Save metadata
        if metadata is None:
            metadata = {}

        metadata.update({
            'feature_name': feature_name,
            'saved_at': timestamp,
            'shape': features.shape,
            'columns': list(features.columns),
            'dtypes': {col: str(dtype) for col, dtype in features.dtypes.items()}
        })

        metadata_path = features_dir / f"{feature_name}_{timestamp}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)

        print(f"Features saved to: {features_path}")
        return str(features_path)

    def load_features(self, feature_name: str, version: Optional[str] = None) -> pd.DataFrame:
        """
        Load feature dataset

        Args:
            feature_name: Name of the feature set
            version: Specific version timestamp, or None for latest

        Returns:
            Feature DataFrame
        """
        features_dir = Path("data") / "features"

        if version is None:
            # Find latest version
            pattern = f"{feature_name}_*.parquet"
            feature_files = list(features_dir.glob(pattern))
            if not feature_files:
                raise FileNotFoundError(f"No features found for {feature_name}")
            feature_path = sorted(feature_files)[-1]  # Latest by name
        else:
            feature_path = features_dir / f"{feature_name}_{version}.parquet"
            if not feature_path.exists():
                raise FileNotFoundError(f"Feature version {version} not found for {feature_name}")

        return pd.read_parquet(feature_path)

    def list_models(self) -> Dict[str, list]:
        """List all available models and versions"""
        models = {}
        for model_dir in self.base_path.iterdir():
            if model_dir.is_dir() and not model_dir.name.endswith('_latest'):
                parts = model_dir.name.split('_')
                if len(parts) >= 2:
                    model_name = '_'.join(parts[:-1])
                    version = parts[-1]
                    if model_name not in models:
                        models[model_name] = []
                    models[model_name].append(version)

        return models


# Global IO manager instance
model_io = ModelIO()
