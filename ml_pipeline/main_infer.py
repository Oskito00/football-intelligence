#!/usr/bin/env python3
"""
Main inference entry point for the ML pipeline
Loads trained models and makes predictions on new data
"""

import argparse
import logging
import sys
from pathlib import Path
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

from config import get_config
from ml_pipeline.inference.infer_result_model import infer_result_model
from ml_pipeline.utils.config import config_manager
from helpers.database_helpers.create_tables import create_match_result_predictions_table


# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))


def setup_logging(config: dict):
    """Setup logging based on config"""
    log_config = config.get('logging', {})
    level = getattr(logging, log_config.get('level', 'INFO').upper())
    format_str = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    logging.basicConfig(level=level, format=format_str)


def get_inferrer(model_name: str):
    """Get the appropriate inference function based on model name"""
    inferrers = {
        'result_model': infer_result_model,
        'result_model_early': infer_result_model,
        'result_model_late': infer_result_model,
        # Add more models here as needed
        # 'goal_scorer_model': infer_goal_scorer_model,
    }
    
    if model_name not in inferrers:
        raise ValueError(f"Unknown model: {model_name}. Available models: {list(inferrers.keys())}")
    
    return inferrers[model_name]


def main():
    parser = argparse.ArgumentParser(description='Run inference with trained ML models')
    parser.add_argument('config', help='Name of the config file (without extension)')
    parser.add_argument('--model-version', help='Specific model version to use (default: latest)')
    parser.add_argument('--output', help='Output file path for predictions')
    parser.add_argument('--limit', type=int, help='Limit number of samples for testing')
    parser.add_argument('--where-clause', help='SQL WHERE clause to filter data')
    parser.add_argument('--mode', choices=['training', 'inference'], default='inference', 
                        help='Mode: training (use elo_history) or inference (use elo_future)')
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        print(f"Loading configuration: {args.config}")
        config = config_manager.load_config(args.config)
        
        # Setup logging
        setup_logging(config)
        logger = logging.getLogger(__name__)
        logger.info(f"Starting inference for {args.config}")
        
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
        
        # Get model name from config
        model_name = config['model']['name']
        logger.info(f"Running inference for model: {model_name}")
        
        # Get the appropriate inferrer
        inferrer = get_inferrer(model_name)
        
        # Create the predictions table if it doesn't exist
        create_match_result_predictions_table(conn)
        
        # Run inference
        result = inferrer(
            conn, 
            config, 
            model_version=args.model_version,
            limit=args.limit,
            where_clause=args.where_clause,
            output_path=args.output,
            mode=args.mode
        )
        
        if result['success']:
            logger.info("Inference completed successfully!")
            logger.info(f"Generated {result['num_predictions']} predictions")
            
            if result.get('output_path'):
                logger.info(f"Predictions saved to: {result['output_path']}")
            
            # Show sample predictions if available
            if 'sample_predictions' in result:
                logger.info("Sample predictions:")
                for i, pred in enumerate(result['sample_predictions'][:5]):
                    logger.info(f"  {i+1}: {pred}")
                    
        else:
            logger.error("Inference failed!")
            if 'error' in result:
                logger.error(f"Error: {result['error']}")
            sys.exit(1)
            
    except Exception as e:
        logging.error(f"Inference failed with error: {str(e)}")
        raise
    finally:
        # Close database connection
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main() 