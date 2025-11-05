
import concurrent.futures
import logging
import time

from utils.betika import Betika
from utils.helper import Helper
from utils.db import Db


logger = logging.getLogger(__name__)

class Autobet:
    """
        main class
    """
    def __init__(self):
        self.betika = Betika()
        self.db = Db()
    
    def is_market_available(self, match):
        try:
            url = f'https://api.betika.com/v1/uo/match?parent_match_id={match.get("parent_match_id")}'
            match_details = self.betika.get_data(url)
            if not match_details:
                return None     
            
            for datum in match_details.get('data', []):
                if int(datum.get('sub_type_id')) == match.get("sub_type_id"):
                    for odd in datum.get('odds', []):
                        if odd.get('odd_key') ==  match.get("bet_pick"):
                            match["odd"] = odd.get('odd_value')
                            return match
                        
        except Exception as e:
            logger.error(e)
            
        return None
        
    
    def bet(self, profile, size=4):
        try:
            phone = profile[0]
            password = profile[1]
            profile_id = profile[2]
            unplaced_matches = self.db.fetch_unplaced_matches(profile_id)
            
            matches = []                    
            for match in unplaced_matches:
                match = self.is_market_available(match)
                if match:
                    matches.append(match)
            
            if matches:  
                helper = Helper(phone, password)
                grouped_matches = [matches[i:i+size] for i in range(0, len(matches), size)]
                
                usable_bal = self.betika.balance #+ self.betika.bonus
                stake = int((usable_bal/len(grouped_matches)))
                                
                for group in grouped_matches:
                    helper.auto_bet(profile_id, group, max(1, stake))    
                    time.sleep(2)    
                
        except Exception as e:
            logger.error(e)
            
                    
    def __call__(self):
        # Use ThreadPoolExecutor to spawn a thread for each profile
        with concurrent.futures.ThreadPoolExecutor() as executor:
            threads = [executor.submit(self.bet, profile) for profile in self.db.get_active_profiles()]

            # Wait for all threads to finish
            concurrent.futures.wait(threads)
        