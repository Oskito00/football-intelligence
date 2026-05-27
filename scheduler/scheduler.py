import sys 
import logging

from football_intelligence.predictions.refresh import run_prediction_refresh

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('scheduler.log')
    ]
)
logger = logging.getLogger(__name__)

def run_script(script_name, func):
    """Wrapper to run a script and log its execution"""
    try:
        logger.info(f"Starting {script_name}")
        func()
        logger.info(f"Completed {script_name}")
    except Exception as e:
        logger.error(f"Error in {script_name}: {str(e)}")

def run_all_scripts():
    """Run Prediction Refresh for scheduler compatibility."""
    return run_prediction_refresh(logger=logger)

def infer_results_with_args(conn):
    """Compatibility wrapper for callers that still use scheduler inference."""
    from football_intelligence.predictions.refresh import run_result_model_inference

    return run_result_model_inference(conn)

def main():
    logger.info("🚀 Starting daily football prediction pipeline...")

    # Run all scripts once and exit
    run_all_scripts()
    
    logger.info("✅ Daily pipeline completed successfully!")

if __name__ == "__main__":
    main()
