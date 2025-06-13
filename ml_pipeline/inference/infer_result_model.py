"""
Inference logic for football result prediction model
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime

from utils.database.postgresql import save_predictions_to_db
from ml_pipeline.features.load_result_features import ResultFeatureLoader
from ml_pipeline.utils.io import model_io


def infer_result_model(conn, config: Dict[str, Any], 
                      model_version: Optional[str] = None,
                      limit: Optional[int] = None,
                      where_clause: Optional[str] = None,
                      output_path: Optional[str] = None,
                      mode: str = 'inference') -> Dict[str, Any]:
    """
    Run inference with the football result prediction model
    
    Args:
        conn: Database connection
        config: Configuration dictionary
        model_version: Specific model version to use (None for latest)
        limit: Optional limit on number of samples
        where_clause: Optional SQL WHERE clause to filter data
        output_path: Optional path to save predictions
        mode: 'training' or 'inference' - determines which tables to use
        
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
        
        # Initialize feature loader with mode
        logger.info(f"Initializing feature loader for {mode} mode")
        feature_loader = ResultFeatureLoader(conn, config['data'], mode=mode)
        
        # Validate required tables exist
        if not feature_loader.validate_required_tables():
            raise ValueError("Required tables not found in database")
        
        # Load features for inference
        logger.info("Loading features for inference")
        
        # Build where clause for unprocessed matches if not specified
        if where_clause is None:
            if mode == 'inference':
                where_clause = "1=1"  # For inference, process all available future data
            else:
                where_clause = "1=1"  # For training mode on historical data
        
        features = feature_loader.load_features(where_clause=where_clause, limit=limit)
        
        if features.empty:
            logger.warning("No features found for inference")
            return {
                'success': True,
                'num_predictions': 0,
                'message': 'No data found for inference'
            }
        
        logger.info(f"Loaded {len(features)} samples for inference")
        
        # Debug: Check if metadata columns exist and have data
        metadata_columns = ['home_team_name', 'away_team_name', 'start_time']
        logger.info(f"Available columns: {list(features.columns)}")
        
        for col in metadata_columns:
            if col in features.columns:
                non_null_count = features[col].notna().sum()
                logger.info(f"Column '{col}': {non_null_count}/{len(features)} non-null values")
                if non_null_count > 0:
                    logger.info(f"Sample values: {features[col].dropna().head(3).tolist()}")
            else:
                logger.warning(f"Column '{col}' not found in features")
        
        # Extract metadata before model processing
        metadata_df = None
        available_metadata = [col for col in metadata_columns if col in features.columns]
        if available_metadata:
            metadata_df = features[available_metadata].copy()
            logger.info(f"Extracted metadata for columns: {available_metadata}")
            logger.info(f"Metadata sample:\n{metadata_df.head()}")
        else:
            logger.warning("No metadata columns found")
        
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
        
        # Create results DataFrame starting with match_id and predictions
        results_df = pd.DataFrame({
            'match_id': features_processed.index,
            'predicted_result': predictions
        })
        
        # Add metadata if available
        if metadata_df is not None and not metadata_df.empty:
            logger.info("Joining metadata to results")
            # Reset index to join properly
            results_df = results_df.reset_index(drop=True)
            metadata_df = metadata_df.reset_index()
            
            # Merge on match_id
            results_df = pd.merge(results_df, metadata_df, on='match_id', how='left')
            logger.info(f"Results after metadata join:\n{results_df.head()}")
        else:
            logger.warning("No metadata to join")
        
        # Add probabilities if available
        if prediction_probabilities is not None:
            # Reorder to put home team first (more intuitive)
            class_names = ['away_win', 'draw', 'home_win']  # This is sklearn's internal order
            display_names = ['home_win', 'draw', 'away_win']  # This is the display order we want
            
            # Map sklearn output to our preferred display order
            sklearn_to_display = {
                'home_win': prediction_probabilities[:, 2],  # sklearn index 2
                'draw': prediction_probabilities[:, 1],      # sklearn index 1  
                'away_win': prediction_probabilities[:, 0]   # sklearn index 0
            }
            
            for class_name in display_names:
                results_df[f'prob_{class_name}'] = sklearn_to_display[class_name]
        
        # Add timestamp
        results_df['prediction_timestamp'] = datetime.now()
        
        # Reorder columns for better readability
        base_columns = ['match_id', 'predicted_result']
        metadata_columns_available = [col for col in ['start_time', 'home_team_name', 'away_team_name'] if col in results_df.columns]
        # Reorder probability columns to show home first
        prob_columns = ['prob_home_win', 'prob_draw', 'prob_away_win']
        prob_columns = [col for col in prob_columns if col in results_df.columns]
        other_columns = ['prediction_timestamp']
        
        column_order = base_columns + metadata_columns_available + prob_columns + other_columns
        results_df = results_df[[col for col in column_order if col in results_df.columns]]
        
        logger.info(f"Final results shape: {results_df.shape}")
        logger.info(f"Final columns: {list(results_df.columns)}")
        
        # Determine model type based on config
        model_type = 'basic'
        if config.get('data', {}).get('feature_requirements', {}).get('formations', False):
            model_type = 'with_formation'
        
        # Alternative: determine from model name
        if 'late' in model_name.lower() or 'formation' in model_name.lower():
            model_type = 'with_formation'
        
        # Save to database using the new helper
        logger.info("Saving predictions to database")
        success = save_predictions_to_db(conn, results_df, model_type=model_type)
        
        if success:
            logger.info("Successfully saved predictions to database")
        else:
            logger.warning("Failed to save predictions to database")
        
        # Save to CSV if output path specified (keep existing functionality)
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