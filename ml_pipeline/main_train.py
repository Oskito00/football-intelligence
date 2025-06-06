#!/usr/bin/env python3
"""
Main training entry point for the ML pipeline
Loads configuration and dispatches to appropriate training logic
"""

import argparse
import logging
import sys
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

# Add project root to path (go up one level from ml_pipeline)
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import the database config from your existing config.py
from config import get_config

# Import the ML pipeline components
from ml_pipeline.utils.config import config_manager
from ml_pipeline.utils.io import model_io
from ml_pipeline.training.train_result_model import train_result_model


def setup_logging(ml_config: dict):
    """Setup logging based on ML config"""
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


def main():
    parser = argparse.ArgumentParser(description='Train ML models for football prediction')
    parser.add_argument('config', help='Name of the config file (without extension)')
    parser.add_argument('--dry-run', action='store_true', help='Run without saving model')
    parser.add_argument('--limit', type=int, help='Limit number of samples for testing')
    
    args = parser.parse_args()
    
    try:
        # Load ML configuration
        print(f"Loading ML configuration: {args.config}")
        ml_config = config_manager.load_config(args.config)
        
        # Setup logging
        setup_logging(ml_config)
        logger = logging.getLogger(__name__)
        logger.info(f"Starting training for {args.config}")
        
        # Get database connection using your existing config
        logger.info("Connecting to database")
        db_config = get_config()  # This gets your database config
        
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
        result = trainer(conn, ml_config, dry_run=args.dry_run, limit=args.limit)
        
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
            sys.exit(1)
            
    except Exception as e:
        logging.error(f"Training failed with error: {str(e)}")
        raise
    finally:
        # Close database connection
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main() 