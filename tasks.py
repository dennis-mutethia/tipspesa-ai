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

    
if __name__ == "__main__":
    # Start the scheduler
    scheduler = BackgroundScheduler()
    
    # Use CronTrigger to align to clock times (won't start immediately)
    scheduler.add_job(
        func=Results(),
        trigger="cron",
        minute="*"  # Every minute, at the top (:00 seconds)
    )
    scheduler.add_job(
        func=Predict(),
        trigger="cron",
        hour="*", minute="0"  # Every hour, at the top of the hour
    )
    scheduler.add_job(
        func=Withdraw(),
        trigger="cron",
        hour="*/4", minute="0"  # Every 4 hours, at the top of those hours
    )
    scheduler.add_job(
        func=Autobet(),
        trigger="cron",
        hour="*/4", minute="10"  # Every 4 hours, at the 10th min of those hours
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