"""
Main entry point for training CNN-based football prediction model
"""

import os
import sys
import psycopg2
import yaml
import logging
import argparse
from typing import Dict, Any

# Add parent directory to path to import from ml_pipeline
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_config
from ml_pipeline_cnn.training.train_cnn_model import train_cnn_model


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('ml_pipeline_cnn/logs/training.log')
        ]
    )


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Train CNN-based football prediction model')
    parser.add_argument('config', help='Path to configuration file')
    parser.add_argument('--dry-run', action='store_true', help='Run without saving model')
    parser.add_argument('--limit', type=int, help='Limit number of samples for testing')
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        logger.info(f"Loading configuration from {args.config}")
        model_config = load_config(args.config)
        
        # Get database connection
        logger.info("Connecting to database")
        db_config = get_config()
        conn = psycopg2.connect(
            host=db_config.DB_HOST,
            database=db_config.DB_NAME,
            user=db_config.DB_USER,
            password=db_config.DB_PASSWORD
        )
        
        # Train model
        logger.info("Starting model training")
        results = train_cnn_model(
            conn=conn,
            config=model_config,
            dry_run=args.dry_run,
            limit=args.limit
        )
        
        if results['success']:
            logger.info("Training completed successfully")
            if results['model_path']:
                logger.info(f"Model saved to {results['model_path']}")
            logger.info(f"Training samples: {results['training_samples']}")
        else:
            logger.error(f"Training failed: {results['error']}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error during training: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main() 