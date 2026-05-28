#!/usr/bin/env python3
"""Model Training entrypoint for Football Intelligence Predictions."""

import argparse
import logging
import sys
from typing import Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

from config import get_config
from football_intelligence.predictions.config import config_manager


def setup_logging(ml_config: dict):
    """Setup logging based on ML config"""
    from pathlib import Path

    log_config = ml_config.get('logging', {})
    level = getattr(logging, log_config.get('level', 'INFO').upper())
    format_str = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create logs directory if specified
    log_file = log_config.get('file')
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(level=level, format=format_str, 
                          handlers=[
                              logging.FileHandler(log_file),
                              logging.StreamHandler(sys.stdout)
                          ])
    else:
        logging.basicConfig(level=level, format=format_str)


def get_trainer(model_name: str):
    """Get the appropriate trainer function based on model name"""
    from football_intelligence.predictions.training import train_result_model

    trainers = {
        'result_model': train_result_model,
        'result_model_early': train_result_model,  # Early variant (no formations)
        'result_model_late': train_result_model,   # Late variant (with formations)
        # Add more models here as needed
        # 'goal_scorer_model': train_goal_scorer_model,
    }
    
    if model_name not in trainers:
        raise ValueError(f"Unknown model: {model_name}. Available models: {list(trainers.keys())}")
    
    return trainers[model_name]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Train ML models for football prediction')
    parser.add_argument('config', help='Name of the config file (without extension)')
    parser.add_argument('--dry-run', action='store_true', help='Run without saving model')
    parser.add_argument('--limit', type=int, help='Limit number of samples for testing')
    return parser


def run_model_training(
    config_name: str,
    dry_run: bool = False,
    limit: Optional[int] = None,
) -> dict[str, Any]:
    conn = None
    try:
        print(f"Loading ML configuration: {config_name}")
        ml_config = config_manager.load_config(config_name)
        
        setup_logging(ml_config)
        logger = logging.getLogger(__name__)
        logger.info(f"Starting training for {config_name}")
        
        logger.info("Connecting to database")
        db_config = get_config()
        
        conn = psycopg2.connect(
            host=db_config.DB_HOST,
            database=db_config.DB_NAME,
            user=db_config.DB_USER,
            password=db_config.DB_PASSWORD,
            cursor_factory=RealDictCursor
        )
        
        # Get model name from ML config
        model_name = ml_config['model']['name']
        logger.info(f"Training model: {model_name}")
        
        # Get the appropriate trainer
        trainer = get_trainer(model_name)
        
        # Run training
        result = trainer(conn, ml_config, dry_run=dry_run, limit=limit)
        
        if result['success']:
            logger.info("Training completed successfully!")
            if result.get('model_path'):
                logger.info(f"Model saved to: {result['model_path']}")
            
            # Print evaluation metrics
            if 'evaluation' in result:
                logger.info("Evaluation Results:")
                for metric, value in result['evaluation'].items():
                    if isinstance(value, dict):
                        logger.info(f"  {metric}:")
                        for sub_metric, sub_value in value.items():
                            logger.info(f"    {sub_metric}: {sub_value}")
                    else:
                        logger.info(f"  {metric}: {value}")
        else:
            logger.error("Training failed!")
            if 'error' in result:
                logger.error(f"Error: {result['error']}")
        return result
            
    except Exception as e:
        logging.error(f"Training failed with error: {str(e)}")
        raise
    finally:
        if conn is not None:
            conn.close()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    result = run_model_training(args.config, dry_run=args.dry_run, limit=args.limit)
    if not result['success']:
        sys.exit(1)


if __name__ == "__main__":
    main() 
