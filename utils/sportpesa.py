
import logging
import requests
import json

logger = logging.getLogger(__name__)

class Sportpesa:
    def __init__(self):
        self.base_url = "https://jackpot-offer-api.ke.sportpesa.com/api"
        self.session = requests.Session()
        
        # Realistic browser headers
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.ke.sportpesa.com/",
            "Origin": "https://www.ke.sportpesa.com",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            # Remove Host header - let requests set it
        })

    def get_data(self, endpoint, params=None):
        try:
            url = f"{self.base_url}{endpoint}"
            logger.info("Fetching: %s", url)
            response = self.session.get(url, params=params, timeout=10)
            logger.info("Status: %s", response.status_code)
            
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

    def get_active_jackpot_matches(self):
        endpoint = "/jackpots/active"
        jackpot = self.get_data(endpoint)
        event_id = None
        matches = []
        if jackpot:
            event_id = jackpot.get("humanId", None)
            for event in jackpot.get("events", []):
                competitors = event.get("competitors", [])
                parent_match_id = event.get("id", "N/A").replace("sr:match:", "")
                home_team = next((c.get("competitorName") for c in competitors if c.get("isHome")), "N/A")
                away_team = next((c.get("competitorName") for c in competitors if not c.get("isHome")), "N/A")
                match_details = {
                    "parent_match_id": parent_match_id,
                    "start_time": event.get("utcKickOffTime"),
                    "home_team": home_team,
                    "away_team": away_team,
                    "odds": [
                        {
                            "sub_type_id": 1,
                            "odd_key": home_team,
                            "outcome_id": 1
                        },
                        {
                            "sub_type_id": 1,
                            "odd_key": "draw",
                            "outcome_id": 2
                        },
                        {
                            "sub_type_id": 1,
                            "odd_key": away_team,
                            "outcome_id": 3
                        }
                    ]
                }
                
                matches.append(match_details)
            
        else:
            logger.warning("Failed to retrieve jackpots.")
        
        return event_id, matches