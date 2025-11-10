import logging
import time
import signal
import sys

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz  # pip install pytz if not installed

from tasks.autobet import Autobet
from tasks.predict import Predict
from tasks.results import Results
from tasks.withdraw import Withdraw

# Global logging configuration (applies to all modules)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'  # Optional: Custom date format (e.g., 2025-11-04 22:13:45)
)
logger = logging.getLogger(__name__)


# Wrapper functions to ensure proper callable passing (avoids instant instantiation)
def results_task():
    results_instance = Results()
    results_instance()  # Assuming __call__ or run method

def predict_task():
    predict_instance = Predict()
    predict_instance()  # Assuming __call__ or run method

def withdraw_task():
    withdraw_instance = Withdraw()
    withdraw_instance()  # Assuming __call__ or run method

def autobet_task():
    autobet_instance = Autobet()
    autobet_instance()  # Assuming __call__ or run method (includes Withdraw if needed)


if __name__ == "__main__":
    # Start the scheduler with explicit timezone
    scheduler = BackgroundScheduler(timezone=pytz.timezone('Africa/Nairobi'))  # EAT/UTC+3 for Meru, KE
    
    # Add jobs with explicit CronTrigger for absolute wall-clock scheduling
    scheduler.add_job(
        func=results_task,
        trigger=CronTrigger(
            minute="*",  # Every minute
            second="0"   # At the start of the minute
        ),
        id="results_cron",
        replace_existing=True,
        misfire_grace_time=30,  # 30s grace for delays
        coalesce=True  # Skip missed runs if piled up
    )
    
    scheduler.add_job(
        func=predict_task,
        trigger=CronTrigger(
            hour="*",      # Every hour
            minute="0",
            second="0"
        ),
        id="predict_cron",
        replace_existing=True,
        misfire_grace_time=60,  # 1min grace
        coalesce=True
    )
        
    scheduler.add_job(
        func=autobet_task,  # Handles Withdraw then Autobet
        trigger=CronTrigger(
            hour="*/2",   # 00:00, 03:00, 06:00, etc. (absolute times)
            minute="0",
            second="0"
        ),
        id="autobet_cron",
        replace_existing=True,
        misfire_grace_time=60,  # 1min grace for startup lag
        coalesce=True
    )
        
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