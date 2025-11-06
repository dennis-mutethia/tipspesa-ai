
import concurrent.futures
import logging 

from utils.betika import Betika
from utils.db import Db


logger = logging.getLogger(__name__)

class Withdraw():
    def __init__(self):
        self.betika = Betika()
        self.db = Db()

    def withdraw(self, profile):
        try:
            phone = profile[0]
            password = profile[1]
            self.betika.login(phone, password)
            amount = min(int(self.betika.balance/3), 300000) 
            
            if amount >= 50:
                logger.info("Requesting withdraw phone=%s, amount=%s", phone, amount)
                amount = min(int(self.betika.balance/3), 300000) 
            
                if amount==300000:
                    self.withdraw(profile)
                
                
        except Exception as e:
            logger.error(e)
    
    def __call__(self):
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:        
                threads = [executor.submit(self.withdraw, profile) for profile in self.db.get_active_profiles()]
                concurrent.futures.wait(threads)
            
        except Exception as e:
            logger.error(e)

