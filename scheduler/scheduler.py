import psycopg2
import time
import os
from datetime import datetime
import sys 
import logging
from psycopg2.extras import RealDictCursor

# Import your script functions
from config import get_config
from data_scraping.api_football.all_data.scrape_league_ids import get_all_leagues_on_api
from data_scraping.api_football.current_season.current_seasons_scrape import scrape_current_seasons
from data_processing.for_training.match_result_features import process_matches
from data_processing.for_inferencing.match_result_features import process_future_matches
from ml_pipeline.main_infer import main as infer_results
from data_scraping.api_football.odds.scrape_future_match_odds import scrape_future_match_odds

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
    """Run all scripts in sequence"""
    config = get_config()
    with psycopg2.connect(
    host=config.DB_HOST,
    database=config.DB_NAME,
    user=config.DB_USER,
    password=config.DB_PASSWORD,
    cursor_factory=RealDictCursor
    ) as conn:
        scripts = [
        ("League IDs Scraper", lambda: get_all_leagues_on_api(conn)),
        ("Current Seasons Scraper", lambda: scrape_current_seasons()),
        ("Training Data Processor", lambda: process_matches(conn)),
        ("Future Matches Processor", lambda: process_future_matches(conn)),
        ("Result Model Inference", lambda: infer_results_with_args(conn)),
        ("Future Match Odds Scraper", lambda: scrape_future_match_odds(conn))
    ]
    
        for script_name, func in scripts:
            run_script(script_name, func)

def infer_results_with_args(conn):
    """Wrapper to call infer_results with proper arguments"""
    # Set up the arguments that main_infer.py expects
    sys.argv = ['main_infer.py', 'result_model_early', '--mode', 'inference']
    
    # Import and call the main function with the connection
    from ml_pipeline.main_infer import main
    main(conn)

def main():
    logger.info("🚀 Starting daily football prediction pipeline...")

    # Run all scripts once and exit
    run_all_scripts()
    
    logger.info("✅ Daily pipeline completed successfully!")

if __name__ == "__main__":
    main()