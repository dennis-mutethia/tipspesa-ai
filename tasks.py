
import logging

from utils.autobet import Autobet
from utils.predict import Predict
from utils.results import Results
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
        logger.info('Updated %d matches updated', len(results))        
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