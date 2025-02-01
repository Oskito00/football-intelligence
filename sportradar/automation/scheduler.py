import time
import subprocess
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)

def run_scripts():
    try:
        # Run create_test_data.py
        logging.info("Starting create_test_data.py...")
        subprocess.run(['python', 'sportradar/scripts/data_processing/create_test_data.py'], check=True)
        logging.info("Finished create_test_data.py")

        #TODO: Add test_pre_process_basic_features.py
        logging.info("Starting test_pre_process_basic_features.py...")
        subprocess.run(['python', 'sportradar/AI/feature_engineering/scripts/test_pre_process_basic_features.py'], check=True)
        logging.info("Finished test_pre_process_basic_features.py")
        # Run pre-processing scripts
        logging.info("Starting pre_process_features_no_h2h.py...")
        subprocess.run(['python', 'sportradar/AI/feature_engineering/scripts/test_pre_process_features_no_h2h.py'], check=True)
        logging.info("Finished pre_process_features_no_h2h.py")

        logging.info("Starting pre_process_features.py...")
        subprocess.run(['python', 'sportradar/AI/feature_engineering/scripts/test_pre_process_features.py'], check=True)
        logging.info("Finished pre_process_features.py")

        #Test
        run = 1
        print(run)
        # Run logistic regression
        logging.info("Starting logistic_regression.py...")
        subprocess.run(['python', 'sportradar/AI/models/scripts/logistic_regression.py'], check=True)
        logging.info("Finished logistic_regression.py")

        # Run odds comparison
        logging.info("Starting compare_predictions.py...")
        subprocess.run(['python', 'sportradar/scripts/odds_comparison/compare_predictions_with_odds.py'], check=True)
        logging.info("Finished compare_predictions.py")

        logging.info("All scripts completed successfully\n")

    except subprocess.CalledProcessError as e:
        logging.error(f"Error running script: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")

def main():
    logging.info("Scheduler started")
    
    while True:
        run_scripts()
        logging.info(f"Sleeping for 5 minutes at {datetime.now()}")
        time.sleep(300)  # Sleep for 5 minutes (300 seconds)

if __name__ == "__main__":
    main()