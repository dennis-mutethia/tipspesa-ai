
import json
import logging
import time

from utils.azure_models import AzureModels
from utils.betika import Betika
from utils.db import Db
from utils.gemini import Gemini
from utils.github_models import GithubModels


logger = logging.getLogger(__name__)

class PredictJackpot():
    """
        main class
    """
    def __init__(self):
        self.betika = Betika()
        self.gemini = Gemini()
        self.github_models = GithubModels()
        self.azure_models = AzureModels()
        self.db = Db()
    
    def prepare_query(self, match_details):
        logger.info("Preparing query for match id: %s", match_details['parent_match_id'])
        
        markets = []
        for market in match_details['odds']:
            if int(market["sub_type_id"]) in [1, 2, 3]:
                markets.append({
                    "sub_type_id": market["sub_type_id"],
                    "odd_key": market["odd_key"],
                    "outcome_id": market["outcome_id"]
                })
                 
        query_dict = {
            "instruction": f"""
You are a soccer betting analyst. For the upcoming match provided in match_details, predict the most probable betting market with the highest implied probability (>75% if possible).
Step 1: Gather Data (Use your search tools)
Web Search: Query `{match_details['home_team']} vs {match_details['away_team']} preview stats H2H injuries` (top 10 results). Extract recent form (last 5 games), head-to-head (last 5), key injuries/suspensions, and average goals.
Betting Odds: Search `{match_details['home_team']} vs {match_details['away_team']} betting odds` from sites like Oddspedia/Bet365. List top markets with odds from 3+ bookies. Calculate implied probabilities (prob = 1/decimal odds; average and adjust for ~8% vig).
X/Tweets Search: Use semantic/keyword search for `{match_details['home_team']} vs {match_details['away_team']}` prediction OR tip OR bet` (latest 15-20 posts). Analyze sentiment (e.g., % favoring Legia win) from fans/pundits. Flag viral takes.
Pundits/Experts: Browse 2-3 sites:
Soccerway/Sofascore for previews.
Flashscore or Transfermarkt for lineups/predictions.
Search `{match_details['home_team']} pundit prediction {match_details['away_team']} experts` for opinions from Polish media.
Step 2: Analyze
Weigh factors: Home or Away advantage, team forms, H2H, weather/motivation.
Rank markets by probability: Use odds as base, adjust +5-10% for positive sentiment/expert consensus (e.g., if 70% tweets predict a particular market, boost it).
Identify the 'best' outcome: Highest prob market with value (prob > implied odds suggest).
Step 3: Output
Respond with ONLY the JSON object, with no additional text, prose, or explanation. The output must strictly adhere to the provided JSON schema for the 'expected_output_schema'.
Be data-driven, objective, and concise."            
            """,
            "match_details": match_details,
            "markets": markets,
            "expected_output_schema": {
                "type": "object",
                "properties": {
                    "parent_match_id": {
                        "type": "string",
                        "description": "Unique identifier for the match, as provided in the input match_details['parent_match_id']"
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
                    "bet_pick": {
                        "type": "string",
                        "description": "The predicted outcome display value as provided in the input markets[i]['odd_key']"
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

    def predict_match(self, match_details, event_id):   
        try:     
            query = self.prepare_query(match_details)
            if query:
                logger.info("Predicting match id: %s - Invoking AI Agents...", match_details['parent_match_id'])
                response, model = self.github_models.get_response(query) 
                if response:
                    time.sleep(6) #10 requests per minute
                else:
                    response, model = self.gemini.get_response(query)   
                    if response:
                        time.sleep(30) #2 requests per minute
                    
                if response:                 
                    marker = '```json'
                    index = response.find(marker)
                    clean_response = response[index + len(marker):].strip('```') if index != -1 else response.replace(marker, '').strip('```')
                    predicted_match = json.loads(clean_response) 
                    logger.info(predicted_match)
                       
                    if predicted_match:
                        self.db.insert_jackpot_match(match=predicted_match, model=model, event_id=event_id)    
                    
                    return predicted_match
            else:
                logger.info("Skipped match id: %s", match_details['parent_match_id'])
            
        except Exception as e:
            logger.error(e)
        
        return None
    
            
    def __call__(self):
        try:
            for jackpot_id in self.betika.get_jackpot_ids():            
                matches = self.betika.get_jackpot_matches(jackpot_id)
                for match_details in matches:
                    predicted_match = self.predict_match(match_details, event_id=jackpot_id)
                    if predicted_match:
                        logger.info(predicted_match)   
        
        except Exception as e:
            logger.error(e)
                
        
            