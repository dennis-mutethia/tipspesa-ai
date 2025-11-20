
import logging
from utils.db import Db
from utils.one_signal import OneSignal
from utils.sofascore_client import SofascoreClient

logger = logging.getLogger(__name__)

class ResultsSofascore():
    """
        main class
    """
    def __init__(self):
        self.sofascore_client = SofascoreClient()
        self.db = Db()
        
        
    def get_results(self):
        started_events = self.db.get_started_events()
        for event in started_events:
            event_id = event['id']
            bet_pick = event['bet_pick']
            results = self.sofascore_client.get_match_result(event_id, bet_pick)
            if results:
                self.db.update_event_results(event_id, results['home_score'], results['away_score'], results['status'])
                self.db.update_match_results(str(event_id), results['home_score'], results['away_score'], results['status'])
                logger.info("Updated result for event_id=%s, %s", event_id, results)
            else:
                logger.info("No result available yet for event_id=%s", event_id)
                    
                
    def __call__(self):
        logger.info("Checking for results of started events")
        self.get_results()
        logger.info("Results check completed")
        