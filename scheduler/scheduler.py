import schedule
import time
import os
from datetime import datetime
import sys 
import logging

# Import your script functions
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
    scripts = [
        ("League IDs Scraper", get_all_leagues_on_api),
        ("Current Seasons Scraper", scrape_current_seasons),
        ("Training Data Processor", process_matches),
        ("Future Matches Processor", process_future_matches),
        ("Result Model Inference", infer_results),
        ("Future Match Odds Scraper", scrape_future_match_odds)
    ]
    
    for script_name, func in scripts:
        run_script(script_name, func)

def main():
    logger.info("Scheduler starting...")
    
    # Schedule all scripts to run at midnight
    schedule.every().day.at("00:00").do(run_all_scripts)
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()