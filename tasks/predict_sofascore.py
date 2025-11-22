
import logging
from utils.db import Db
from utils.one_signal import OneSignal
from utils.sofascore_client import SofascoreClient
from utils.sportybet_client import SportybetClient

logger = logging.getLogger(__name__)

class PredictSofascore():
    """
        main class
    """
    def __init__(self):
        self.db = Db()
        self.sofascore_client = SofascoreClient()
        self.sportybet_client = SportybetClient()
    
    def predict(self):
        dropping_odds = [] #self.sofascore_client.get_dropping_odds()
        winning_odds = self.sofascore_client.get_winning_odds()
        events = dropping_odds + winning_odds
        predicted_match_ids = self.db.fetch_predicted_match_ids()
        predictions = 0
        for event in events:
            try:
                if 1.2 < event['odd'] < 2:
                    sportybet_event = self.sportybet_client.search_event(event)
                    logger.info(sportybet_event)
                    self.db.insert_matches([sportybet_event])
                    predictions += (1 if sportybet_event['match_id'] not in predicted_match_ids else 0)
                
            except Exception as e:
                logger.error("Error inserting event %s: %s", event, e)
        
        return predictions
        
            
    def book_bet(self):
        events = self.db.get_upcoming_events()
        event_chunks = [events[i:i + 20] for i in range(0, len(events), 20)]
        for chunk in event_chunks:    
            share_code = self.sportybet_client.book_bet(chunk)
            logger.info("Sportybet Share Code: %s", share_code)
        
        logger.info("----------------------------------------------------")
        
        if len(events) > 8:            
            event_chunks = [events[i:i + 8] for i in range(0, len(events), 8)]
            for chunk in event_chunks:    
                share_code = self.sportybet_client.book_bet(chunk)
                logger.info("Sportybet Share Code: %s", share_code)
            
    
    def __call__(self):        
        logger.info("Fetching predictions from Sofascore")
        predictions = self.predict()
        logger.info("Fetch predictions completed")
        
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
