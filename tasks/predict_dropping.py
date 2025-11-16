
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
        
    def get_results(self):
        started_events = self.db.get_started_events()
        for event in started_events:
            event_id = event['id']
            bet_pick = event['bet_pick']
            results = self.sofascore.get_results(event_id, bet_pick)
            if results:
                self.db.update_event_results(event_id, results['home_score'], results['away_score'], results['status'])
                logger.info("Updated result for event_id=%s, %s", event_id, results)
            else:
                logger.info("No result available yet for event_id=%s", event_id)
    
    def __call__(self):
        logger.info("Checking for results of started events")
        self.get_results()
        logger.info("Results check completed")
        
        logger.info("Fetching dropping odds from Sofascore")
        dropping_odds = self.sofascore.get_dropping_odds()
        for event in dropping_odds:
            try:
                self.db.insert_event(event=event)
                logger.info("Inserted event: %s", event)
            except Exception as e:
                logger.error("Error inserting event %s: %s", event, e)
