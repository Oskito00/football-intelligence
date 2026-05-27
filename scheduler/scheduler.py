import logging
import sys

from football_intelligence.predictions.refresh import run_prediction_refresh

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("scheduler.log"),
    ],
)
logger = logging.getLogger(__name__)


def run_script(script_name, func):
    """Wrapper to run a script and log its execution"""
    try:
        logger.info("Starting %s", script_name)
        func()
        logger.info("Completed %s", script_name)
    except Exception as exc:
        logger.error("Error in %s: %s", script_name, exc)


def run_all_scripts():
    """Run Prediction Refresh for scheduler compatibility."""
    return run_prediction_refresh(logger=logger)


def infer_results_with_args(conn):
    """Compatibility wrapper for callers that still use scheduler inference."""
    from football_intelligence.predictions.refresh import run_result_model_inference

    return run_result_model_inference(conn)


def main():
    logger.info("🚀 Starting daily football prediction pipeline...")

    run_all_scripts()

    logger.info("✅ Daily pipeline completed successfully!")


if __name__ == "__main__":
    main()
