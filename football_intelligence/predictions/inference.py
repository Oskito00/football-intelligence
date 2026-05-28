"""
Inference logic for football result prediction model
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime

from football_intelligence.database import save_predictions_to_db
from football_intelligence.predictions.model_io import model_io
from football_intelligence.predictions.result_features import ResultFeatureLoader


def infer_result_model(conn, config: Dict[str, Any],
                      model_version: Optional[str] = None,
                      limit: Optional[int] = None,
                      where_clause: Optional[str] = None,
                      output_path: Optional[str] = None,
                      mode: str = 'inference',
                      match_id: Optional[int] = None) -> Dict[str, Any]:
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
        match_id: Optional specific match_id to run inference on

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

        # Build where clause for specific match_id if provided
        if match_id is not None:
            where_clause = f"eh.match_id = {match_id}"
            logger.info(f"Running inference for specific match_id: {match_id}")
        elif where_clause is None:
            if mode == 'inference':
                where_clause = "1=1"  # For inference, process all available future data
            else:
                where_clause = "1=1"  # For training mode on historical data

        features = feature_loader.load_features(where_clause=where_clause, limit=limit)
        if match_id is not None:
            # Convert the first row to a dictionary
            feature_dict = features.iloc[0].to_dict()
            # Print each key-value pair on its own line
            for k, v in feature_dict.items():
                print(f"{k}: {v}")

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

        # Create results DataFrame with predictions
        results_df = pd.DataFrame({
            'match_id': features_processed.index,
            'predicted_result': predictions
        })

        # Remove duplicates from results
        results_df = results_df.drop_duplicates(subset=['match_id'])
        logger.info(f"Results shape after removing duplicates: {results_df.shape}")

        # Filter and deduplicate metadata
        filtered_metadata = feature_loader.metadata_df[feature_loader.metadata_df['match_id'].isin(features_processed.index)]
        filtered_metadata = filtered_metadata.drop_duplicates(subset=['match_id'])
        logger.info(f"Filtered metadata shape after removing duplicates: {filtered_metadata.shape}")

        # Join with metadata
        results_df = pd.merge(
            results_df,
            filtered_metadata,
            on='match_id',
            how='left',
            validate='1:1'
        )

        # Add prediction probabilities if available
        if hasattr(model, 'predict_proba'):
            # Get probabilities for all matches
            all_probabilities = model.predict_proba(features_processed)

            # Create probability DataFrame
            prob_df = pd.DataFrame({
                'match_id': features_processed.index,
                'prob_home_win': all_probabilities[:, 2],  # sklearn index 2 is home_win
                'prob_draw': all_probabilities[:, 1],      # sklearn index 1 is draw
                'prob_away_win': all_probabilities[:, 0]   # sklearn index 0 is away_win
            })

            # Remove duplicates to match results
            prob_df = prob_df.drop_duplicates(subset=['match_id'])

            # Merge probabilities with results
            results_df = pd.merge(
                results_df,
                prob_df,
                on='match_id',
                how='left',
                validate='1:1'
            )

        # Add timestamp
        results_df['prediction_timestamp'] = datetime.now()

        # Ensure columns are in the correct order
        column_order = [
            'match_id',
            'predicted_result',
            'start_time',
            'home_team_name',
            'away_team_name',
            'prob_home_win',
            'prob_draw',
            'prob_away_win',
            'prediction_timestamp'
        ]

        results_df = results_df[column_order]

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
            if hasattr(model, 'predict_proba'):
                sample['confidence'] = max([row[f'prob_{cls}'] for cls in ['home_win', 'draw', 'away_win']])
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
