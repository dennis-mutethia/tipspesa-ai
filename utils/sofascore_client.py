import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any

import requests
from dotenv import load_dotenv
from unidecode import unidecode

load_dotenv()

logger = logging.getLogger(__name__)

# Load sports from .env (e.g., "football,basketball,tennis")
SOFASCORE_SPORTS: List[str] = [
    sport.strip().lower() for sport in os.getenv("SOFASCORE_SPORTS", "football").split(",")
]


class SofascoreClient:
    BASE_URL = "https://www.sofascore.com/api/v1"

    def __init__(self) -> None:
        self.session = requests.Session()
        self._setup_headers()

    def _setup_headers(self) -> None:
        """Realistic headers to mimic Brave/Chrome browser."""
        self.session.headers.update({
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "referer": "https://www.sofascore.com/betting-tips-today",
            "sec-ch-ua": '"Chromium";v="142", "Brave";v="142", "Not_A Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "sec-gpc": "1",
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/142.0.0.0 Safari/537.36"
            ),
        })

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Centralized GET request with error handling."""
        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=12)

            if response.status_code == 403:
                logger.warning("403 Forbidden – possible bot detection")
                return None

            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error("HTTP error on %s: %s", endpoint, e)
        except requests.exceptions.RequestException as e:
            logger.error("Request failed on %s: %s", endpoint, e)
        except Exception as e:
            logger.error("Unexpected error on %s: %s", endpoint, e)

        return None

    def _fractional_to_decimal(self, fractional: str) -> float:
        """Convert '4/1' → 5.0"""
        try:
            num, den = map(int, fractional.split("/"))
            return round(num / den + 1, 2)
        except (ValueError, ZeroDivisionError):
            return 0.0

    def get_latest_odds(self, event_id: str) -> Tuple[Optional[str], Optional[float], float]:
        """
        Returns: (bet_pick_name, decimal_odd, change_from_initial)
        
        If no dropping odd found → (None, None, 0)
        """
        data = self._get(f"/event/{event_id}/odds/1/changes")
        if not data:
            return None, None, 0.0

        changed_odds = data.get("changedOdds", [])
        if not changed_odds:
            return None, None, 0.0

        latest = changed_odds[-1]
        choices = []

        # Collect available choices
        for key in ("choice1", "choice2", "choice3"):
            choice = latest.get(key)
            if choice:
                choices.append(choice)

        if not choices:
            return None, None, 0.0

        # Pick the one with the biggest drop (most negative change)
        best = min(choices, key=lambda c: c.get("changeFromInitial", 0))

        change = best.get("changeFromInitial", 0)
        if change >= 0:
            return None, None, 0.0  # Only return if actually dropping

        fractional = best.get("fractionalValue", "0/1")
        return (
            best.get("name"),
            self._fractional_to_decimal(fractional),
            change
        )

    def get_dropping_odds(self) -> List[Dict[str, Any]]:
        """Fetch all currently dropping 1X2 odds across configured sports."""
        matches = []

        for sport in SOFASCORE_SPORTS:
            logger.info("Fetching dropping odds for %s", sport.capitalize())
            data = self._get(f"/odds/1/dropping/{sport}")
            if not data or "events" not in data:
                logger.warning("No dropping odds data for %s", sport)
                continue

            for event in data["events"]:
                event_id = str(event.get("id", ""))
                start_ts = event.get("startTimestamp")
                if not start_ts or not event_id:
                    continue

                start_time = datetime.fromtimestamp(start_ts).strftime("%Y-%m-%d %H:%M:%S")
                home_team = event.get("homeTeam", {}).get("name", "Unknown")
                away_team = event.get("awayTeam", {}).get("name", "Unknown")
                tournament = event.get("tournament", {}).get("name", "Unknown")
                category = event.get("tournament", {}).get("category", {}).get("name", "Unknown")

                bet_pick, odd, change = self.get_latest_odds(event_id)

                if odd and change < 0 and bet_pick=="1":  # Only include actual dropping odds
                    matches.append({
                        "id": event_id,
                        "start_time": start_time,
                        "home_team": unidecode(home_team),
                        "away_team": unidecode(away_team),
                        "tournament": unidecode(tournament),
                        "category": unidecode(category),
                        "sport": sport.capitalize(),
                        "bet_pick": bet_pick or "Unknown",
                        "odd": odd,
                        "odd_change": round(change, 2),
                        "overall_prob": round(change, 2) 
                    })

        logger.info("Found %d dropping odds matches", len(matches))
        return matches

    def get_winning_odds(self) -> List[Dict[str, Any]]:
        """Fetch 'Winning Odds' (high confidence tips from Sofascore)."""
        matches = []

        for sport in SOFASCORE_SPORTS:
            logger.info("Fetching winning odds for %s", sport.capitalize())
            data = self._get(f"/odds/1/winning/{sport}")
            if not data:
                continue

            events = data.get("events", [])
            winning_map = data.get("winningOddsMap", {})
            odds_map = data.get("oddsMap", {})

            for event in events:
                event_id = str(event.get("id"))
                if not event_id or event_id not in winning_map:
                    continue

                win_info = winning_map[event_id]
                if win_info.get("actual", 0) < 75:  # Confidence threshold
                    continue

                start_time = datetime.fromtimestamp(event.get("startTimestamp", 0)).strftime("%Y-%m-%d %H:%M:%S")
                home_team = event.get("homeTeam", {}).get("name", "Unknown")
                away_team = event.get("awayTeam", {}).get("name", "Unknown")
                tournament = event.get("tournament", {}).get("name", "Unknown")
                category = event.get("tournament", {}).get("category", {}).get("name", "Unknown")

                market_choices = odds_map.get(event_id, {}).get("choices", [])
                target_fractional = win_info.get("fractionalValue")

                for choice in market_choices:
                    if choice.get("initialFractionalValue") == target_fractional:
                        matches.append({
                            "id": event_id,
                            "start_time": start_time,
                            "home_team": home_team,
                            "away_team": away_team,
                            "tournament": tournament,
                            "category": category,
                            "sport": sport.capitalize(),
                            "prediction": odds_map.get(event_id, {}).get("marketGroup", "1X2"),
                            "bet_pick": choice.get("name"),
                            "odd": self._fractional_to_decimal(target_fractional or "1/1"),
                            "overall_prob": win_info.get("actual", 0),
                            "odd_change": win_info.get("actual", 0),
                        })
                        break  # only one winning tip per match

        logger.info("Found %d winning odds", len(matches))
        return matches

    def get_match_result(self, event_id: str, outcome_id: int = None) -> Optional[Dict]:
        """Check if match is finished and return result + win/loss."""
        data = self._get(f"/event/{event_id}")
        if not data:
            return None

        event = data.get("event", {})
        status_type = event.get("status", {}).get("type")

        if status_type != "finished":
            return {
                "status": "LIVE" if status_type in ("live", "inprogress") else "STARTING",
                "home_score": event.get("homeScore", {}).get("current"),
                "away_score": event.get("awayScore", {}).get("current"),
            }
            
        home_team = event.get("homeTeam", {}).get("name")
        away_team = event.get("awayTeam", {}).get("name")
        home_score = event.get("homeScore", {}).get("current", 0)
        away_score = event.get("awayScore", {}).get("current", 0)
        winner_code = event.get("winnerCode")

        return {
            "home_team": home_team,
            "away_team": away_team,
            "home_score": home_score,
            "away_score": away_score,
            "status": "WON" if winner_code == outcome_id else "LOST"
        }