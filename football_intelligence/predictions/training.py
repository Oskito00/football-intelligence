"""
Training logic for football result prediction model
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional

from utils.parsing.pandas import convert_to_native_types
from football_intelligence.predictions.model_io import model_io


def train_result_model(conn, config: Dict[str, Any],
                      dry_run: bool = False,
                      limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Train the football result prediction model

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
        from football_intelligence.predictions.result_features import ResultFeatureLoader
        from football_intelligence.predictions.result_model import ResultModel

        # Initialize feature loader
        logger.info("Initializing feature loader")
        feature_loader = ResultFeatureLoader(conn, config['data'])

        # Validate required tables exist
        if not feature_loader.validate_required_tables():
            raise ValueError("Required tables not found in database")

        # Load data
        logger.info("Loading training data")
        where_clause = _build_where_clause(config['data'].get('filters', {}))
        features, targets = feature_loader.load_data(where_clause=where_clause, limit=limit)


        # Check data quality
        quality_report = feature_loader.check_data_quality(features, targets)

        # Clean data
        features, targets = feature_loader.clean_data(features, targets)


        # Initialize model
        logger.info("Initializing model")
        model = ResultModel(config)

        # Prepare data (train/test split)
        data_config = config['data']

        X_train, X_test, y_train, y_test = model.prepare_data(
            features, targets,
            test_size=data_config.get('test_size', 0.2),
            random_state=data_config.get('random_state', 42)
        )

        # Preprocess features
        logger.info("Preprocessing features")
        X_train_processed, X_test_processed = model.preprocess_features(X_train, X_test)

        # Cross-validation if enabled
        training_config = config.get('training', {})
        cv_config = training_config.get('cross_validation', {})

        if cv_config.get('enabled', False):
            logger.info("Running cross-validation")
            cv_scores = _run_cross_validation(
                model, X_train, y_train, cv_config
            )
            logger.info(f"CV scores: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")

        # Train the model
        logger.info("Training model")
        training_history = model.train(X_train_processed, y_train)

        # Evaluate on test set
        logger.info("Evaluating model")
        evaluation_results = model.evaluate(X_test, y_test)

        # Get feature importance
        feature_importance = model.get_feature_importance()

        # Save model if not dry run
        model_path = None
        if not dry_run:
            logger.info("Saving model")
            metadata = {
                'config': config,
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'features_count': len(X_train.columns),
                'feature_names': list(X_train.columns),
                'evaluation': convert_to_native_types(evaluation_results),
                'quality_report': convert_to_native_types(quality_report)
            }

            if feature_importance is not None:
                metadata['feature_importance'] = feature_importance.to_dict('records')

            model_path = model_io.save_model(
                model.model,
                config['model']['name'],
                metadata=metadata,
                preprocessor=model.preprocessor
            )

        # Prepare results
        results = {
            'success': True,
            'model_path': model_path,
            'evaluation': evaluation_results,
            'training_history': training_history,
            'feature_importance': feature_importance.to_dict('records') if feature_importance is not None else None,
            'data_quality': quality_report
        }

        if cv_config.get('enabled', False):
            results['cross_validation'] = {
                'scores': cv_scores.tolist(),
                'mean': cv_scores.mean(),
                'std': cv_scores.std()
            }

        return results

    except Exception as e:
        logger.error(f"Training failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def _build_where_clause(filters: Dict[str, Any]) -> Optional[str]:
    """Build SQL WHERE clause from filters configuration"""
    conditions = []

    if filters.get('min_date'):
        conditions.append(f"eh.start_time >= '{filters['min_date']}'")

    if filters.get('max_date'):
        conditions.append(f"eh.start_time <= '{filters['max_date']}'")

    if filters.get('leagues'):
        league_list = "', '".join(str(l) for l in filters['leagues'])
        conditions.append(f"mih.competition_id IN ('{league_list}')")

    return " AND ".join(conditions) if conditions else None


def _run_cross_validation(model, X, y, cv_config: Dict[str, Any]):
    """Run cross-validation on the model"""
    from sklearn.model_selection import cross_val_score, StratifiedKFold

    folds = cv_config.get('folds', 5)
    scoring = cv_config.get('scoring', 'accuracy')

    # Create a fresh model instance for CV
    cv_model = model.__class__(model.config)
    cv_model.model = cv_model.create_model()

    # Use StratifiedKFold for classification
    cv_splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=42)

    scores = cross_val_score(
        cv_model.model, X, y,
        cv=cv_splitter,
        scoring=scoring,
        n_jobs=-1
    )

    return scores
