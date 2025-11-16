
import logging
from utils.db import Db
from utils.sofascore import Sofascore

logger = logging.getLogger(__name__)

class PredictDropping():
    """
        main class
    """
    def __init__(self):
        self.sofascore = Sofascore()
        self.db = Db()
    
    def __call__(self):
        logger.info("Fetching dropping odds from Sofascore")
        dropping_odds = self.sofascore.get_dropping_odds()
        for event in dropping_odds:
            try:
                self.db.insert_event(event=event)
                logger.info("Inserted event id: %s", event['id'])
            except Exception as e:
                logger.error("Error inserting event id %s: %s", event['id'], e)
