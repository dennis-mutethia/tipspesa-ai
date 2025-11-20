
import logging
from utils.betika import Betika
from utils.db import Db
from utils.one_signal import OneSignal
from utils.sofascore import Sofascore
from utils.sportybet import Sportybet

logger = logging.getLogger(__name__)

class PredictDropping():
    """
        main class
    """
    def __init__(self):
        self.sofascore = Sofascore()
        self.db = Db()
        self.sportybet = Sportybet()
    
    def predict(self):
        dropping_odds = self.sofascore.get_dropping_odds()
        predicted_match_ids = self.db.fetch_predicted_match_ids()
        predictions = 0
        for event in dropping_odds:
            try:
                if 1.2 < event['odd'] < 1.55 and (event['bet_pick']=='1' or event['sport'] == 'Tennis'):
                    self.db.insert_event(event=event)
                    logger.info(event)
                    
                    betika_match = Betika().search_match(event)
                    if betika_match and int(betika_match['parent_match_id']) not in predicted_match_ids:
                        self.db.insert_matches([betika_match])
                        predictions += 1
                    
                    sportybet_event = self.sportybet.search_event(event)
                    if sportybet_event:
                        self.db.update_event_sportybet(event['id'], sportybet_event['_event_id'], sportybet_event['_market_id'], sportybet_event['_outcome_id'])
                        
                        if not betika_match and int(sportybet_event['parent_match_id']) not in predicted_match_ids:
                            self.db.insert_matches([sportybet_event])
                            predictions += 1
                
            except Exception as e:
                logger.error("Error inserting event %s: %s", event, e)
        
        return predictions
        
            
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
        logger.info("Fetching dropping odds from Sofascore")
        predictions = self.predict()
        logger.info("Fetch droppin odds completed")
        
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
