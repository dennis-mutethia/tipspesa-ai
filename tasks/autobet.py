
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
        
    
    def bet(self, profile, bet_size=4):
        try:
            helper = Helper(phone=profile[0], password=profile[1])
            
            if helper.betika.balance>=1:
                unplaced_matches = self.db.fetch_unplaced_matches(helper.betika.profile_id)
                
                available_matches = []                    
                for match in unplaced_matches:
                    match = self.is_market_available(match)
                    if match:
                        available_matches.append(match)
                
                if available_matches: 
                    grouped_matches = [available_matches[i:i+bet_size] for i in range(0, len(available_matches), bet_size)]                    
                    grouped_matches = [matches for matches in grouped_matches if len(matches) > bet_size/2]
                    
                    if grouped_matches:
                        usable_balance = helper.betika.balance/2
                        stake = int(usable_balance/len(grouped_matches))                                  
                        for matches in grouped_matches:
                            if len(matches) > bet_size/2:
                                helper.auto_bet(matches, max(1, stake))    
                                time.sleep(2)   
                    else:
                        logger.info("No available matches for profile: %s", helper.betika.phone)
            else:
                logger.info("Betika Balance is too low: %s - for profile: %s", helper.betika.balance, helper.betika.phone)
                
        except Exception as e:
            logger.error(e)
            
                    
    def __call__(self):
        # Use ThreadPoolExecutor to spawn a thread for each profile
        with concurrent.futures.ThreadPoolExecutor() as executor:
            threads = [
                executor.submit(self.bet, profile) 
                for profile in self.db.get_active_profiles()
            ]

            # Wait for all threads to finish
            concurrent.futures.wait(threads)
        