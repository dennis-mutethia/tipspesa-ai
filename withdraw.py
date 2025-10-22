
import concurrent.futures
from utils.betika import Betika
from utils.db import Db


# Configure logging for debugging and monitoring
logging.basicConfig(level=logging.INFO)
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
            amount = int(self.betika.balance/3) 
            while amount >= 50 and amount <= 300000:
                self.betika.withdraw(amount)
                amount = int(self.betika.balance/3) 
                
        except Exception as e:
            logger.error(e)
    
    def __call__(self):
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:        
                threads = [executor.submit(self.withdraw, profile) for profile in self.db.get_active_profiles()]
                concurrent.futures.wait(threads)
            
        except Exception as e:
            logger.error(e)

if __name__ == "__main__":
    try: 
        Withdraw()()
    except Exception as e:
        logger.error(e)
