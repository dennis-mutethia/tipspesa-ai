
import logging
import requests
import json

from datetime import datetime

logger = logging.getLogger(__name__)

class Sportybet:
    def __init__(self):
        self.base_url = "https://www.sportybet.com/api/ke"
        self.session = requests.Session()
        
        # Realistic browser headers
        self.session.headers.update({
            "accept": "*/*",
            "content-type": "application/json",
            "origin": "https://www.sportybet.com",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        })

    def get_data(self, endpoint, params=None):
        try:
            url = f"{self.base_url}{endpoint}"
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 403:
                logger.error("403 Forbidden - likely blocked by Cloudflare/anti-bot")
                logger.error("Response snippet: %s", response.text[:500])
                return None
                
            response.raise_for_status()
            return response.json().get("response", response.json())
        
        except requests.exceptions.HTTPError as http_err:
            logger.error("HTTP error: %s", http_err)
        except requests.exceptions.RequestException as req_err:
            logger.error("Request error: %s", req_err)
        except json.JSONDecodeError:
            logger.error("Invalid JSON response: %s", response.text[:500])
        except Exception as err:
            logger.error("Unexpected error: %s", err)
        return None
    
        
    def post_data(self, endpoint, payload):
        try:
            url = f"{self.base_url}{endpoint}"
            response = self.session.post(url, data=json.dumps(payload), timeout=10)
            
            if response.status_code == 403:
                logger.error("403 Forbidden - likely blocked by Cloudflare/anti-bot")
                logger.error("Response snippet: %s", response.text[:500])
                return None
                
            response.raise_for_status()
            return response.json().get("response", response.json())
        
        except requests.exceptions.HTTPError as http_err:
            logger.error("HTTP error: %s", http_err)
        except requests.exceptions.RequestException as req_err:
            logger.error("Request error: %s", req_err)
        except json.JSONDecodeError:
            logger.error("Invalid JSON response: %s", response.text[:500])
        except Exception as err:
            logger.error("Unexpected error: %s", err)
        return None
    

    def search_event(self, event):
        home_keywords = f"{event['home_team']}".split()
        away_keywords = f"{event['away_team']}".split()
        for keyword in (home_keywords + away_keywords):
            endpoint = "/factsCenter/event/firstSearch"
            params = {
                'keyword': keyword,
                'pageSize': 20                
            }
            response = self.get_data(endpoint, params)
            
            for datum in response.get('data', {}).get('preMatch'):
                estimated_start_date = datetime.fromtimestamp(datum.get("estimateStartTime") / 1000).strftime('%Y-%m-%d') 
                if estimated_start_date in event['start_time'] \
                    and any(word in home_keywords for word in datum.get('homeTeamName').replace(',', '').split()) \
                        and any(word in away_keywords for word in datum.get('awayTeamName').replace(',', '').split()) \
                            and event['category']==datum.get('sport').get('category').get('name') \
                                and event['tournament'] in datum.get('sport').get('category').get('tournament').get('name'):
                    #logger.info("Found event: %s", datum)  
                                                  
                    return {
                        '_event_id': datum.get('eventId'),
                        '_market_id': datum.get('markets')[0].get("id"),
                        '_outcome_id': "4" if event['bet_pick'] == "1" else "5" if event['bet_pick'] == "2" else "6"
                    }
        
        return None
    
    def book_bet(self, events):
        selections = []
        for event in events:
            selections.append({
                "eventId": event['_event_id'],
                "marketId": event['_market_id'],
                "outcomeId": event['_outcome_id']
            })
        
        if selections:
            endpoint = "/orders/share"
            payload = {
                "selections": selections
            }
                        
            response = self.post_data(endpoint, payload)
            return response.get('data').get('shareCode')
        
        return None
        
    
    
    

    

    