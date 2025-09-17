import time
from utils.betika import Betika

class AutobetRed:
    """
        main class
    """
    def __init__(self):
        phone = '0105565532'
        password = 'Mmxsp65$$$'
        self.betika = Betika()
        self.betika.login(phone, password)
    
    def get_upcoming_match_ids(self, live=False):    
        total = 1001
        limit = 1000
        page = 1
        matches_ids = set()
        while limit*page < total:
            total, page, events = self.betika.get_events(limit, page, live)
            
            for event in events:
                parent_match_id = int(event.get('parent_match_id'))
                matches_ids.add(parent_match_id)
        
        return matches_ids
    
    def generate_betslip(self, parent_match_id):   
        try:
            url = f'https://api.betika.com/v1/uo/match?parent_match_id={parent_match_id}'
            match_details = self.betika.get_data(url)
            if not match_details:
                return None            
            meta = match_details.get('meta') 
            markets = [] 
            for datum in match_details.get('data', []):
                if int(datum.get('sub_type_id')) in [146]: # red
                    for odd in datum.get('odds'):
                        if odd.get('odd_key') == 'no':
                            return {
                                "sub_type_id": datum.get('sub_type_id'),
                                "bet_pick": odd.get('odd_key'),
                                "odd_value": odd.get('odd_value'),
                                "outcome_id": odd.get('outcome_id'),
                                "sport_id": '14',
                                "special_bet_value": odd.get('special_bet_value'),
                                "parent_match_id": meta.get('parent_match_id'),
                                "bet_type": 7
                            }
            
        except Exception as e:
            return None
        
        return None
        
    def __call__(self):
        upcoming_match_ids = self.get_upcoming_match_ids(live=False)
        min_matches = 5
        betslips = []
        composite_betslip = None
        composite_betslips = [] 
        total_odd = 1
        for parent_match_id in upcoming_match_ids:
            betslip = self.generate_betslip(parent_match_id)            
            if betslip:
                betslips.append(betslip)
                total_odd *= float(betslip.get('odd_value'))                                              
                composite_betslip = {
                    'total_odd': total_odd,
                    'betslips': betslips
                }
                
                if len(betslips) == min_matches:
                    composite_betslips.append(composite_betslip)
                    betslips = []
                    total_odd = 1
                    composite_betslip = None  
        
        if len(betslips) > min_matches/2:
            composite_betslips.append(composite_betslip)
                                              
        if len(composite_betslips) > 0:              
            usable = self.betika.balance #+ self.betika.bonus
            stake = int((usable/len(composite_betslips)))
            stake = max(1, stake)
            stake = 1 if (stake == 0 and int(usable)>0) else stake
            if stake > 0:
                composite_betslips.sort(key=lambda cb: cb['total_odd'], reverse=True)
                for cb in composite_betslips:
                    ttl_odd = cb['total_odd']
                    slips = cb['betslips']
                    print(slips, ttl_odd, stake)
                    code = self.betika.place_bet(slips, ttl_odd, stake)
                    time.sleep(2)
            else:
                print("Insufficient balance to place bets.")

if __name__ == "__main__":
    AutobetRed()()
