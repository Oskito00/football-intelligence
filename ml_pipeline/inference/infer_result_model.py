"""
Inference logic for football result prediction model
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime

from ml_pipeline.features.load_result_features import ResultFeatureLoader
from ml_pipeline.utils.io import model_io


def infer_result_model(conn, config: Dict[str, Any], 
                      model_version: Optional[str] = None,
                      limit: Optional[int] = None,
                      where_clause: Optional[str] = None,
                      output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Run inference with the football result prediction model
    
    Args:
        conn: Database connection
        config: Configuration dictionary
        model_version: Specific model version to use (None for latest)
        limit: Optional limit on number of samples
        where_clause: Optional SQL WHERE clause to filter data
        output_path: Optional path to save predictions
        
    Returns:
        Dictionary with inference results
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Load trained model
        logger.info("Loading trained model")
        model_name = config['model']['name']
        model_artifacts = model_io.load_model(model_name, version=model_version)
        
        model = model_artifacts['model']
        preprocessor = model_artifacts['preprocessor']
        metadata = model_artifacts['metadata']
        
        logger.info(f"Loaded model version: {metadata.get('saved_at', 'unknown')}")
        logger.info(f"Model type: {metadata.get('model_type', 'unknown')}")
        
        # Initialize feature loader
        logger.info("Initializing feature loader")
        feature_loader = ResultFeatureLoader(conn, config['data'])
        
        # Validate required tables exist
        if not feature_loader.validate_required_tables():
            raise ValueError("Required tables not found in database")
        
        # Load features for inference
        logger.info("Loading features for inference")
        
        # Build where clause for unprocessed matches if not specified
        if where_clause is None:
            where_clause = "m.is_processed = false"  # Only predict on unprocessed matches
        
        features = feature_loader.load_features(where_clause=where_clause, limit=limit)
        
        if features.empty:
            logger.warning("No features found for inference")
            return {
                'success': True,
                'num_predictions': 0,
                'message': 'No data found for inference'
            }
        
        logger.info(f"Loaded {len(features)} samples for inference")
        
        # Ensure features match training schema
        training_features = metadata.get('feature_names', [])
        missing_features = set(training_features) - set(features.columns)
        extra_features = set(features.columns) - set(training_features)
        
        if missing_features:
            logger.warning(f"Missing features from training: {missing_features}")
            # Fill missing features with default values
            for feature in missing_features:
                features[feature] = 0  # or appropriate default
        
        if extra_features:
            logger.info(f"Dropping extra features not in training: {extra_features}")
            features = features.drop(columns=list(extra_features))
        
        # Reorder columns to match training
        features = features[training_features]
        
        # Apply preprocessing
        if preprocessor is not None:
            logger.info("Applying preprocessing")
            features_processed = pd.DataFrame(
                preprocessor.transform(features),
                columns=features.columns,
                index=features.index
            )
        else:
            features_processed = features
        
        # Make predictions
        logger.info("Making predictions")
        predictions = model.predict(features_processed)
        
        # Get prediction probabilities if available
        prediction_probabilities = None
        if hasattr(model, 'predict_proba'):
            prediction_probabilities = model.predict_proba(features_processed)
        
        # Create results DataFrame
        results_df = pd.DataFrame({
            'match_id': features.index,
            'predicted_result': predictions
        })
        
        # Add probabilities if available
        if prediction_probabilities is not None:
            class_names = ['away_win', 'draw', 'home_win']  # Typical sklearn order
            for i, class_name in enumerate(class_names):
                results_df[f'prob_{class_name}'] = prediction_probabilities[:, i]
        
        # Add timestamp
        results_df['prediction_timestamp'] = datetime.now()
        
        # Save predictions if output path specified
        if output_path:
            logger.info(f"Saving predictions to {output_path}")
            results_df.to_csv(output_path, index=False)
        
        # Prepare sample predictions for logging
        sample_predictions = []
        for i, row in results_df.head(10).iterrows():
            sample = {
                'match_id': row['match_id'],
                'prediction': row['predicted_result']
            }
            if prediction_probabilities is not None:
                sample['confidence'] = max([row[f'prob_{cls}'] for cls in class_names])
            sample_predictions.append(sample)
        
        return {
            'success': True,
            'num_predictions': len(results_df),
            'predictions': results_df.to_dict('records'),
            'sample_predictions': sample_predictions,
            'output_path': output_path,
            'model_metadata': metadata
        }
        
    except Exception as e:
        logger.error(f"Inference failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        } 