
import logging
from utils.db import Db
from utils.one_signal import OneSignal
from utils.sofascore import Sofascore
from utils.sportybet import Sportybet

logger = logging.getLogger(__name__)

class PredictWinning():
    """
        main class
    """
    def __init__(self):
        self.sofascore = Sofascore()
        self.db = Db()
        self.sportybet = Sportybet()
    
    def predict(self):
        events = self.sofascore.get_winning_odds()
        predicted_match_ids = self.db.fetch_predicted_match_ids()
        predictions = 0
        for event in events:
            try:
                if event['overall_prob'] >= 75 and event['odd'] >= 1.2:
                    self.db.insert_event(event=event)
                                        
                    sportybet_event = self.sportybet.search_event(event)
                    if sportybet_event:
                        logger.info(sportybet_event)
                        self.db.update_event_sportybet(event['id'], sportybet_event['_event_id'], sportybet_event['_market_id'], sportybet_event['_outcome_id'])
                        self.db.insert_matches([sportybet_event])
                        predictions += (1 if int(sportybet_event['parent_match_id']) not in predicted_match_ids else 0)
                
            except Exception as e:
                logger.error("Error inserting event %s: %s", event, e)
        
        return predictions
        
        
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
                    
    
    def book_bet(self):
        events = self.db.get_upcoming_events()
        event_chunks = [events[i:i + 20] for i in range(0, len(events), 20)]
        for chunk in event_chunks:    
            share_code = self.sportybet.book_bet(chunk)
            logger.info("Sportybet Share Code: %s", share_code)
        
        logger.info("----------------------------------------------------")
            
        event_chunks = [events[i:i + 8] for i in range(0, len(events), 8)]
        for chunk in event_chunks:    
            share_code = self.sportybet.book_bet(chunk)
            logger.info("Sportybet Share Code: %s", share_code)
            
    
    def __call__(self):
        logger.info("Checking for results of started events")
        self.get_results()
        logger.info("Results check completed")
        
        logger.info("Fetching winning odds from Sofascore")
        predictions = self.predict()
        logger.info("Fetch winning odds completed")
        
        logger.info("Booking Bet")
        self.book_bet()
                
        
        if predictions>0:
            logger.info("Sending Notification to app users")
            OneSignal().send_push_notification(
                heading="🔥 New Predictions Just Dropped! 🔥",
                message=f"{predictions} New Predictions have Just been Posted! Open App & Refresh to see them (Pull to Refresh)!!!",
                image="https://tipspesa.vercel.app/static/puh-notification-image.JPG"
            )
        else:
            logger.warning("No New predictions found")
