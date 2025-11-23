import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any

import requests

logger = logging.getLogger(__name__)


class SportybetClient:
    BASE_URL = "https://www.sportybet.com/api/ke"

    def __init__(self) -> None:
        self.session = requests.Session()
        self._setup_headers()

    def _setup_headers(self) -> None:
        """Set realistic browser-like headers."""
        self.session.headers.update({
            "accept": "*/*",
            "content-type": "application/json",
            "origin": "https://www.sportybet.com",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/142.0.0.0 Safari/537.36"
            ),
        })

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[Any, Any]]:
        """Unified request handler with proper error logging."""
        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = self.session.request(method, url, timeout=10, **kwargs)

            if response.status_code == 403:
                logger.error("403 Forbidden - likely blocked by anti-bot protection")
                logger.debug("Response snippet: %s", response.text[:500])
                return None

            response.raise_for_status()
            data = response.json()
            return data.get("response", data)

        except requests.exceptions.HTTPError as e:
            logger.error("HTTP error for %s %s: %s", method.upper(), endpoint, e)
        except requests.exceptions.RequestException as e:
            logger.error("Network error for %s %s: %s", method.upper(), endpoint, e)
        except json.JSONDecodeError:
            logger.error("Invalid JSON received: %s", response.text[:500])
        except Exception as e:
            logger.error("Unexpected error during %s %s: %s", method.upper(), endpoint, e)

        return None

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        return self._request("GET", endpoint, params=params)

    def post(self, endpoint: str, payload: Dict) -> Optional[Dict]:
        return self._request("POST", endpoint, json=payload)  # Use json= for proper serialization

    def search_event(self, event: Dict) -> Optional[Dict[str, Any]]:
        """
        Search for a match on Sportybet and extract betting details.
        Returns enriched event dict if found, else None.
        """
        event["match_id"] = event["id"]
        event["parent_match_id"] = event["id"]
        event["prediction"] = "1X2" if event["bet_pick"] in ["1", "2", "3"] else "Over/Under" if event["bet_pick"] in "Over 2.5" else None
        event["sub_type_id"] = "0"
        event["special_bet_value"] = event["bet_pick"]
        event["outcome_id"] = event["bet_pick"] if event["bet_pick"] in ["1", "2", "3"] else "12" if event["bet_pick"] == "Over 2.5" else None
        event["bet_pick"] = (event["home_team"] if event["outcome_id"] == "1" else event["away_team"] if event["outcome_id"] == "2" else "Draw") if event["prediction"] == "1X2" else event["bet_pick"]
        
        home_team = event["home_team"].lower().replace(",", "").replace("-", " ").replace("/", " ")
        away_team = event["away_team"].lower().replace(",", "").replace("-", " ").replace("/", " ")
        target_date = event["start_time"][:10]  # Extract YYYY-MM-DD

        # Map bet_pick to outcome description
        outcome_map = {
            "1": "Home", 
            "2": "Away", 
            "X": "Draw",
            "12": "Over 2.5"
        }
        target_outcome = outcome_map.get(event["outcome_id"].upper())

        if not target_outcome:
            logger.warning("Invalid bet_pick: %s", event["outcome_id"])
            return None

        endpoint = "/factsCenter/event/firstSearch"
        params = {"pageSize": 20}

        for keyword in set(home_team.split() + away_team.split()):
            params["keyword"] = keyword
            data = self.get(endpoint, params)

            if not data or "data" not in data:
                continue

            for match in data["data"].get("preMatch", []):
                match_date = datetime.fromtimestamp(match["estimateStartTime"] / 1000).strftime("%Y-%m-%d")

                home_name = match.get("homeTeamName", "").lower().replace(",", "").replace("-", " ").replace("/", " ")
                away_name = match.get("awayTeamName", "").lower().replace(",", "").replace("-", " ").replace("/", " ")
                
                # Match conditions
                if (match_date == target_date
                    and any(k in home_name for k in set(home_team.split()))
                    and any(k in away_name for k in set(away_team.split()))
                    and event["category"] == match.get("sport", {}).get("category", {}).get("name")):

                    for market in match.get("markets"):
                        if market.get("name") != event["prediction"]:
                            continue
                        
                        for outcome in market.get("outcomes", []):
                            if outcome.get("desc") == target_outcome:
                                parent_match_id = match.get("eventId", "").replace("sr:match:", "")
                                event["parent_match_id"] = parent_match_id
                                event["sub_type_id"] = market.get("id")           
                                event["outcome_id"] = outcome.get("id")                          
                                event["category"] = f'{event["category"]} - {event["tournament"]}'
                                event["odd"] = outcome.get("odds")   

                                return event
                            
        logger.info("No matching sportybet event found for: %s vs %s on %s", event["home_team"], event["away_team"], target_date)
        
        event["category"] = f'{event["category"]} - {event["tournament"]}'
        return event

    def book_bet(self, events: List[Dict]) -> Optional[str]:
        """
        Book multiple selections and return share code.
        Each event must have _event_id, _market_id, _outcome_id.
        """
        selections = [
            {
                "eventId": f'sr:match:{ev["_event_id"]}',
                "marketId": str(ev["_market_id"]),
                "outcomeId": str(ev["_outcome_id"]),
            }
            for ev in events
            if all(k in ev for k in ("_event_id", "_market_id", "_outcome_id"))
        ]

        if not selections:
            logger.error("No valid selections to book")
            return None

        payload = {"selections": selections}
        response = self.post("/orders/share", payload)

        if response and "data" in response:
            return response["data"].get("shareCode")

        logger.error("Failed to book bet, response: %s", response)
        return None