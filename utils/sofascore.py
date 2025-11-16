
import logging
import requests
import json

from datetime import datetime

logger = logging.getLogger(__name__)

class Sofascore:
    def __init__(self):
        self.base_url = "https://www.sofascore.com/api/v1"
        self.session = requests.Session()
        
        # Realistic browser headers
        self.session.headers.update({
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "sec-ch-ua": "\"Chromium\";v=\"142\", \"Brave\";v=\"142\", \"Not_A Brand\";v=\"99\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "sec-gpc": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "x-requested-with": "4b58a4"
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

    def get_latest_odds(self, event_id):
        endpoint = f"/event/{event_id}/odds/1/changes"
        changed_odds = self.get_data(endpoint).get("changedOdds", [])
        latest_odds = changed_odds[-1] if changed_odds else None
        if latest_odds:
            choice_1 = latest_odds.get("choice1")
            choice_2 = latest_odds.get("choice2")
            choice_3 = latest_odds.get("choice3")
            choice = None
            if choice_3:
                # Three-way market (e.g., Draw option)
                choices = [choice_1, choice_2, choice_3]
                choice = min(choices, key=lambda c: c.get("changeFromInitial", float('inf')))
            elif choice_1 and choice_2:
                print(choice_1, choice_2)
                # Two-way market
                choice = choice_1 if choice_1.get("changeFromInitial") < choice_2.get("changeFromInitial") else choice_2
            
            if choice:    
                bet_pick = choice.get("name", "N/A")
                fractional_value = choice.get("fractionalValue", "N/A")
                decimal_odds = round(int(fractional_value.split('/')[0]) / int(fractional_value.split('/')[1]) + 1, 2)
                odd_change = choice.get("changeFromInitial", 0)
                return bet_pick, decimal_odds, odd_change
                
        return None, None, None
    
    def get_dropping_odds(self, category="all"):
        endpoint = f"/odds/1/dropping/{category}"
        events = self.get_data(endpoint).get("events", [])
        matches = []
        for event in events:
            event_id = str(event.get("id", "N/A"))
            start_time = datetime.fromtimestamp(event.get("startTimestamp", "N/A")).strftime('%Y-%m-%d %H:%M:%S')
            home_team = event.get("homeTeam", {}).get("name", "N/A")
            away_team = event.get("awayTeam", {}).get("name", "N/A")
            tournament = event.get("tournament", {}).get("name", "N/A")
            category = event.get("tournament", {}).get("category", {}).get("name", "N/A")
            sport = event.get("tournament", {}).get("category", {}).get("sport", {}).get("name", "N/A")
            bet_pick, odd, odd_change = self.get_latest_odds(event_id)
            
            matches.append({
                "id": event_id,
                "start_time": start_time,
                "home_team": home_team,
                "away_team": away_team,
                "tournament": tournament,
                "category": category,
                "sport": sport,
                "bet_pick": bet_pick,
                "odd": odd,
                "odd_change": odd_change
            })
        
        return matches

    def get_results(self, event_id, bet_pick=None):
        endpoint = f"/event/{event_id}"
        event = self.get_data(endpoint).get("event", {})
        status = event.get("status", {}).get("type", None)
        if status:
            home_score = event.get("homeScore", {}).get("current", 0)
            away_score = event.get("awayScore", {}).get("current", 0)
            if status == "finished":
                winner_code = event.get("winnerCode", 0)
                status = "WON" if winner_code==bet_pick else "LOST"
                
            return {
                "status": status,
                "home_score": home_score,
                "away_score": away_score
            }
        return None
