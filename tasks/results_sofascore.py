
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
            outcome_id = event['outcome_id']
            results = self.sofascore_client.get_match_result(event_id, outcome_id)
            if results:
                self.db.update_match_results(str(event_id), results['home_score'], results['away_score'], results['status'])
                logger.info("Updated result for event_id=%s, expected_outcome_id=%s, %s", event_id, outcome_id, results)
                if results['status'] == "WON":
                    logger.info("Sending Notification to app users")
                    OneSignal().send_push_notification(
                        heading="🎉🎉 Predicted Match WON!!! 🎉🎉",
                        message=f"{results['home_team']} vs {results['away_team']} :: {results['home_score']}-{results['away_score']}",
                        image="https://tipspesa.vercel.app/static/prediction-won.jpg"
                    )
            else:
                logger.info("No result available yet for event_id=%s", event_id)
                    
                
    def __call__(self):
        logger.info("Checking for results of started events")
        self.get_results()
        logger.info("Results check completed")
        