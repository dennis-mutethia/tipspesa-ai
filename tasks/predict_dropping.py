
import logging
from utils.betika import Betika
from utils.db import Db
from utils.one_signal import OneSignal
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
                self.db.update_match_results(str(event_id), results['home_score'], results['away_score'], results['status'])
                logger.info("Updated result for event_id=%s, %s", event_id, results)
            else:
                logger.info("No result available yet for event_id=%s", event_id)
    
    def __call__(self):
        logger.info("Checking for results of started events")
        self.get_results()
        logger.info("Results check completed")
        
        logger.info("Fetching dropping odds from Sofascore")
        dropping_odds = self.sofascore.get_dropping_odds()
        predicted_match_ids = self.db.fetch_predicted_match_ids()
        predictions = 0
        for event in dropping_odds:
            try:
                self.db.insert_event(event=event)
                logger.info("Inserted event: %s", event)
                if event['odd'] < 2:
                    predicted_match = Betika().search_match(event)
                    if predicted_match and int(predicted_match['parent_match_id']) not in predicted_match_ids:
                        self.db.insert_matches([predicted_match])
                        predictions += 1
                
            except Exception as e:
                logger.error("Error inserting event %s: %s", event, e)
                
        
        if predictions>0:
            logger.info("Sending Notification to app users")
            OneSignal().send_push_notification(
                heading="🔥 New Predictions Just Dropped! 🔥",
                message=f"{predictions} New Predictions have Just been Posted! Open App & Refresh to see them (Pull to Refresh)!!!",
                image="https://tipspesa.vercel.app/static/puh-notification-image.JPG"
            )
        else:
            logger.warning("No New predictions found")
