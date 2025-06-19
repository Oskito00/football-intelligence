"""
Training script for CNN-based football prediction model
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder

from ml_pipeline_cnn.features.load_cnn_features import CNNFeatureLoader
from ml_pipeline_cnn.models.cnn_model import CNNModel
from ml_pipeline_cnn.utils.io import model_io


def train_cnn_model(conn, config: Dict[str, Any], 
                   dry_run: bool = False, 
                   limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Train the CNN-based football prediction model
    
    Args:
        conn: Database connection
        config: Configuration dictionary
        dry_run: If True, don't save the model
        limit: Optional limit on number of samples for testing
        
    Returns:
        Dictionary with training results and model information
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize feature loader
        logger.info("Initializing feature loader")
        feature_loader = CNNFeatureLoader(conn, config['data'])
        
        # Load data
        logger.info("Loading training data")
        where_clause = _build_where_clause(config['data'].get('filters', {}))
        traditional_features, form_sequences, h2h_sequences = feature_loader.load_features(
            where_clause=where_clause, 
            limit=limit
        )
        
        # Load targets
        logger.info("Loading targets")
        targets = _load_targets(conn, traditional_features.index)
        
        # Initialize model
        logger.info("Initializing model")
        model = CNNModel(config)
        
        # Train model
        logger.info("Training model")
        history = model.train(
            traditional_features=traditional_features,
            form_sequences=form_sequences,
            h2h_sequences=h2h_sequences,
            targets=targets,
            validation_split=config['data'].get('validation_split', 0.2)
        )
        
        # Save model if not dry run
        model_path = None
        if not dry_run:
            logger.info("Saving model")
            metadata = {
                'config': config,
                'training_samples': len(traditional_features),
                'features_count': len(traditional_features.columns),
                'feature_names': list(traditional_features.columns),
                'history': history
            }
            
            model_path = model_io.save_model(
                model,
                config['model']['name'],
                metadata=metadata
            )
        
        # Prepare results
        results = {
            'success': True,
            'model_path': model_path,
            'history': history,
            'training_samples': len(traditional_features)
        }
        
        return results
        
    except Exception as e:
        logger.error(f"Training failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def _build_where_clause(filters: Dict[str, Any]) -> Optional[str]:
    """Build WHERE clause from filters"""
    conditions = []
    
    if filters.get('min_date'):
        conditions.append(f"eh.start_time >= '{filters['min_date']}'")
    if filters.get('max_date'):
        conditions.append(f"eh.start_time <= '{filters['max_date']}'")
    if filters.get('leagues'):
        conditions.append(f"mih.competition_id IN ({','.join(map(str, filters['leagues']))})")
    
    return " AND ".join(conditions) if conditions else None


def _load_targets(conn, match_ids: pd.Index) -> np.ndarray:
    """Load target variable (match result)"""
    query = """
        SELECT match_id, 
               CASE 
                   WHEN home_score > away_score THEN 'home_win'
                   WHEN home_score < away_score THEN 'away_win'
                   ELSE 'draw'
               END as result
        FROM matches
        WHERE match_id = ANY(%s)
        AND home_score IS NOT NULL AND away_score IS NOT NULL
    """
    
    targets_df = pd.read_sql_query(query, conn, params=(list(match_ids),))
    targets_df.set_index('match_id', inplace=True)
    
    # Encode targets
    encoder = LabelEncoder()
    encoder.fit(['away_win', 'draw', 'home_win'])  # Consistent order
    targets = encoder.transform(targets_df['result'])
    
    return targets 