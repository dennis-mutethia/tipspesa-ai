
import json
import logging
import time
import sys

from utils.betika import Betika
from utils.db import Db
from utils.gemini import Gemini
from utils.github_models import GithubModels
from utils.one_signal import OneSignal

# Configure logging for debugging and monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Predict:
    """
        main class
    """
    def __init__(self):
        self.betika = Betika()
        self.gemini = Gemini()
        self.github_models = GithubModels()
        self.db = Db()
    
    def prepare_query(self, parent_match_id):
        logger.info("Preparing query for match id: %s", parent_match_id)
        url = f'https://api.betika.com/v1/uo/match?parent_match_id={parent_match_id}'
        match_details = self.betika.get_data(url)
        if not match_details:
            return None            
        meta = match_details.get('meta') 
        markets = [] 
        for datum in match_details.get('data', []):
            if int(datum.get('sub_type_id')) in [1, 10, 29, 18]: # 1X2, DOUBLE CHANCE, BOTH TEAMS TO SCORE, TOTAL
                market = {
                    "sub_type_id": datum.get('sub_type_id'),
                    "prediction": datum.get('name'),
                    "odds": [
                        { 
                            "odd_key": odd.get('odd_key'),
                            "odd_value": odd.get('odd_value'),
                            "special_bet_value": odd.get('special_bet_value') ,
                            "outcome_id": odd.get('outcome_id') 
                        } for odd in datum.get('odds', [])]
                }            
            
                markets.append(market)
        #start_time = meta.get('start_time') 
        
        #if datetime.now().date() == datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S").date():
        # Define the query structure as a dictionary for cleaner JSON handling
        query_dict = {
            "instruction": "Analyze the following match using ALL available data from the internet including tweets, bookmarkers data, team histories, team forms, etc and return the probability percentage of the highest most probable outcome using the provided markets. Respond with ONLY the JSON object, with no additional text, prose, or explanation. The output must strictly adhere to the provided JSON schema for the 'expected_output_schema'.",
            "match_details": meta,
            "markets": markets,
            "expected_output_schema": {
                "type": "object",
                "properties": {
                    "parent_match_id": {
                        "type": "string",
                        "description": "Unique identifier for the match, as provided in the input match_details['parent_match_id']"
                    },
                    "match_id": {
                        "type": "string",
                        "description": "Also Unique identifier for the match, as provided in the input match_details['match_id']"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Match Start Time, as provided in the input match_details['start_time']"
                    },
                    "home_team": {
                        "type": "string",
                        "description": "Home Team, as provided in the input match_details['home_team']"
                    },
                    "away_team": {
                        "type": "string",
                        "description": "Away Team, as provided in the input match_details['away_team']"
                    },
                    "overall_prob": {
                        "type": "integer",
                        "pattern": "^(100|[1-9][0-9]?|[0-9])$",
                        "description": "The probability percentage (0-100) as an integer."
                    },
                    "sub_type_id": {
                        "type": "string",
                        "description": "Unique identifier for the picked market, as provided in the input markets[i]['sub_type_id']"
                    },
                    "prediction": {
                        "type": "string",
                        "description": "The prediction name as provided in the input markets[i]['prediction']"
                    },
                    "bet_pick": {
                        "type": "string",
                        "description": "The predicted outcome display value as provided in the input markets[i]['odd_key']"
                    },
                    "odd": {
                        "type": "float",
                        "description": "The predicted outcome odd value as provided in the input markets[i]['odd_value']"
                    },
                    "special_bet_value": {
                        "type": "string",
                        "description": "The predicted outcome special_bet_value value as provided in the input markets[i]['special_bet_value']"
                    },
                    "outcome_id": {
                        "type": "string",
                        "description": "The predicted outcome outcome_id value as provided in the input markets[i]['outcome_id']"
                    }
                }
            }
        }
        
        # Convert to JSON string with proper formatting
        query = json.dumps(query_dict, indent=4)
        return query
    
    def is_valid_match(self, filtered_match):
        MIN_ODD, MAX_ODD, MIN_PROB = 1.10, 1.79, 80
        
        filtered_match = (
            filtered_match
            if filtered_match
            and MIN_ODD <= filtered_match["odd"] <= MAX_ODD #or filtered_match["overall_prob"] >= MAX_PROB)
            and filtered_match["overall_prob"] >= MIN_PROB
            and 'under' not in filtered_match["bet_pick"].lower()
            else None
        )
        
        if filtered_match:
            filtered_match = (
                None 
                if (int(filtered_match['sub_type_id']) == 1  and int(filtered_match['outcome_id']) == 1 and filtered_match['odd'] >= 1.45)
                or (int(filtered_match['sub_type_id']) == 1  and int(filtered_match['outcome_id']) == 3 and filtered_match['odd'] <= 1.3) 
                or (filtered_match["bet_pick"].lower() == 'over 1.5' and not 1.2 <= filtered_match['odd'] >= 1.27)
                or (filtered_match["bet_pick"].lower() == 'yes' and not 1.3 <= filtered_match['odd'] >= 1.4)
                or (int(filtered_match['sub_type_id']) == 10 and not 1.15 <= filtered_match['odd'] >= 1.19) #double chance
                #or (int(filtered_match['sub_type_id']) == 29 and filtered_match["odd"] >= 1.3)
                else filtered_match
            )
        
        return filtered_match  
    
    def predict_match(self, parent_match_id):   
        try:     
            query = self.prepare_query(parent_match_id)
            if query:
                logger.info("Predicting match id: %s - Invoking AI Agents...", parent_match_id)
                response, model = self.github_models.get_response(query) 
                if response:
                    time.sleep(6) #10 requests per minute
                else:
                    response, model = self.gemini.get_response(query)   
                    time.sleep(30) #2 requests per minute
                    
                if response:                 
                    clean_response = response.replace('```json', '').strip('```')
                    filtered_match = json.loads(clean_response)
                                      
                    if filtered_match:
                        self.db.update_source_model(parent_match_id, model, filtered_match["start_time"])
                        
                    predicted_match = self.is_valid_match(filtered_match)  
                else:
                    sys.exit(0)
                    
                return predicted_match
            else:
                logger.info("Skipped match id: %s", parent_match_id)
                return None
            
        except Exception as e:
            logger.error(e)
            return None
    
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
              
    def __call__(self):
        upcoming_match_ids = self.get_upcoming_match_ids(live=False)
        predicted_match_ids = self.db.fetch_predicted_match_ids()
        
        un_predicted_match_ids = upcoming_match_ids.difference(predicted_match_ids)
        
        predictions = 0
        for parent_match_id in upcoming_match_ids:
            predicted_match = self.predict_match(parent_match_id)
            if predicted_match:
                logger.info(predicted_match)
                self.db.insert_matches([predicted_match]) 
                predictions += 1
        
        if predictions>0:
            logger.info("Sending Notification to app users")
            OneSignal()(predictions)
        else:
            logger.warning("No matches predicted")
            
                        
if __name__ == "__main__":
    try: 
        Predict()()
    except Exception as e:
        logger.error(e)
        
