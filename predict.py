
from datetime import datetime
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

class Predict():
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
        query_dict = {
            "instruction": f"""
You are a soccer betting analyst. For the upcoming match provided in match_details, predict the most probable betting market with the highest implied probability (>75% if possible).
Step 1: Gather Data (Use your search tools)
Web Search: Query `{meta['home_team']} vs {meta['away_team']} preview stats H2H injuries` (top 10 results). Extract recent form (last 5 games), head-to-head (last 5), key injuries/suspensions, and average goals.
Betting Odds: Search `{meta['home_team']} vs {meta['away_team']} betting odds` from sites like Oddspedia/Bet365. List top markets with odds from 3+ bookies. Calculate implied probabilities (prob = 1/decimal odds; average and adjust for ~8% vig).
X/Tweets Search: Use semantic/keyword search for `{meta['home_team']} vs {meta['away_team']}` prediction OR tip OR bet` (latest 15-20 posts). Analyze sentiment (e.g., % favoring Legia win) from fans/pundits. Flag viral takes.
Pundits/Experts: Browse 2-3 sites:
Soccerway/Sofascore for previews.
Flashscore or Transfermarkt for lineups/predictions.
Search `{meta['home_team']} pundit prediction {meta['away_team']} experts` for opinions from Polish media.
Step 2: Analyze
Weigh factors: Home or Away advantage, team forms, H2H, weather/motivation.
Rank markets by probability: Use odds as base, adjust +5-10% for positive sentiment/expert consensus (e.g., if 70% tweets predict a particular market, boost it).
Identify the 'best' outcome: Highest prob market with value (prob > implied odds suggest).
Step 3: Output
Respond with ONLY the JSON object, with no additional text, prose, or explanation. The output must strictly adhere to the provided JSON schema for the 'expected_output_schema'.
Be data-driven, objective, and concise."            
            """,
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
                    "category": {
                        "type": "string",
                        "description": "Competition Category, as provided in the input match_details['category']"
                    },
                    "competition_name": {
                        "type": "string",
                        "description": "Competition Name, as provided in the input match_details['competition_name']"
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
        MIN_ODD, MAX_ODD, MIN_PROB = 1.10, 1.50, 80
        
        filtered_match = (
            filtered_match
                if filtered_match
                    and MIN_ODD <= filtered_match["odd"] <= MAX_ODD
                    and filtered_match["overall_prob"] >= MIN_PROB   
                    and filtered_match["bet_pick"].lower() != 'over 0.5'    #remove over 0.5 
                    and 'under' not in filtered_match["bet_pick"].lower()   #remove unders    
                    and int(filtered_match['sub_type_id']) != 10            #remove double chances       
            else None
        )                   
        
        #apply condition for each bet pick
        if filtered_match:
            filtered_match = (
                None 
                if (int(filtered_match['sub_type_id']) == 1  and int(filtered_match['outcome_id']) == 1 and filtered_match['odd'] >= 1.45)  #home win
                or (int(filtered_match['sub_type_id']) == 1  and int(filtered_match['outcome_id']) == 3 and filtered_match['odd'] <= 1.3)   #away win
                or (filtered_match["bet_pick"].lower() == 'over 1.5' and (filtered_match['odd'] <= 1.2 or filtered_match['odd'] >= 1.28))   #OV1.5
                or (filtered_match["bet_pick"].lower() == 'yes' and (filtered_match['odd'] < 1.3 or filtered_match['odd'] > 1.4))           #GG
                else filtered_match
            )
        
        #Map GG to OV1.5
        if filtered_match:
            if int(filtered_match['outcome_id']) == 74: 
                filtered_match['sub_type_id'] = '18'
                filtered_match['outcome_id'] = '12'
                filtered_match["prediction"] = 'TOTAL'
                filtered_match["bet_pick"] = 'over 1.5'
                filtered_match["special_bet_value"] = 'total=1.5'
                filtered_match['odd'] = (float(filtered_match['odd']) - 1)/2 + 1
        
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
    
    def get_upcoming_match_ids(self, live=False, last_prediction=None):    
        total = 1001
        limit = 1000
        page = 1
        matches = []
        while limit*page < total:
            total, page, events = self.betika.get_events(limit, page, live)
            
            matches.extend(
                {
                    "start_time": datetime.strptime(event.get('start_time'), '%Y-%m-%d %H:%M:%S'),
                    "parent_match_id": int(event.get('parent_match_id'))
                } for event in events
            ) 
            
        sorted_matches = sorted(matches, key=lambda m: m['start_time'])  # Use key access
        
        return [
            match['parent_match_id'] 
            for match in sorted_matches 
            if last_prediction is None or match['start_time'] >= last_prediction
        ]
              
    def __call__(self):
        predictions = 0
        try:
            last_prediction = self.db.fetch_last_prediction()
            upcoming_match_ids = self.get_upcoming_match_ids(live=False, last_prediction=last_prediction)
            predicted_match_ids = self.db.fetch_predicted_match_ids()
            
            un_predicted_match_ids = [
                match_id for match_id in upcoming_match_ids
                if match_id not in predicted_match_ids
            ]
            logger.info("Found %s new matches", len(un_predicted_match_ids))
            
            for parent_match_id in un_predicted_match_ids:
                predicted_match = self.predict_match(parent_match_id)
                if predicted_match:
                    logger.info(predicted_match)
                    self.db.insert_matches([predicted_match]) 
                    predictions += 1
        
        except Exception as e:
            logger.error(e)
                
        if predictions>0:
            logger.info("Sending Notification to app users")
            OneSignal()(predictions)
        else:
            logger.warning("No matches predicted")
            
                 
if __name__ == "__main__":
    logger.info('>>>>>>>> Starting Prediction task >>>>>>>>')
    try: 
        Predict()()
    except Exception as e:
        logger.error(e)
    logger.info('<<<<<<<< Prediction Task completed >>>>>>>>')