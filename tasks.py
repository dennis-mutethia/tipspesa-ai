
import logging
import time
import signal
import sys

from apscheduler.schedulers.background import BackgroundScheduler

from autobet import Autobet
from predict import Predict
from results import Results
from utils.withdraw import Withdraw

# Configure logging for debugging and monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def predict():
    logger.info('>>>>>>>> Starting Prediction task >>>>>>>>')
    try: 
        Predict()()
    except Exception as e:
        logger.error(e)
    logger.info('<<<<<<<< Prediction Task completed >>>>>>>>')
        

def results():
    logger.info('>>>>>>>> Starting Results task >>>>>>>>')
    try:
        results_processor = Results()
        matches = results_processor.helper.fetch_matches('', '=', '', limit=1000)
        logger.info('Fetched %d matches to process', len(matches))    
        results = results_processor(matches)
        logger.info('Updated %d matches', len(results))  # Minor fix: removed redundant "updated"
    except Exception as e:
        logger.error('Error in cycle: %s', e)
        
    logger.info('<<<<<<<< Results Task completed >>>>>>>>')


def withdraw_and_autobet():
    logger.info('>>>>>>>> Starting Withdraw & Autobet task >>>>>>>>')
    try: 
        Withdraw()()
        Autobet()()
    except Exception as e:
        logger.error(e)
    logger.info('<<<<<<<< Withdraw & Autobet Task completed >>>>>>>>')
    
    
if __name__ == "__main__":
    # Start the scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=results, trigger="interval", minutes=1)
    scheduler.add_job(func=predict, trigger="interval", hours=3)
    scheduler.add_job(func=withdraw_and_autobet, trigger="interval", hours=4)
    scheduler.start()
    
    # Graceful shutdown handler
    def shutdown_handler(signum, frame):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown(wait=True)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    # Keep the main thread alive to allow background tasks to run
    try:
        logger.info("Scheduler started. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Received interrupt. Shutting down...")
        scheduler.shutdown(wait=True)