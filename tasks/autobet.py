import concurrent.futures
import logging
import time
from typing import List, Dict, Tuple, Optional

from tasks.withdraw import Withdraw
from utils.betika import Betika
from utils.helper import Helper
from utils.db import Db


logger = logging.getLogger(__name__)

# Constants for configurability
MIN_BALANCE = 1.0
DEFAULT_BET_SIZE = 4
MIN_GROUP_SIZE = DEFAULT_BET_SIZE // 2 + 1  # e.g., >2 for bet_size=4
BET_DELAY_SECONDS = 2


class Autobet:
    """
    Main class for automated betting logic using Betika API and database.
    Handles market availability checks, bet placement, and parallel execution across profiles.
    """

    def __init__(self) -> None:
        self.betika = Betika()
        self.db = Db()
        self.withdraw = Withdraw()

    def is_market_available(self, match: Dict) -> Optional[Dict]:
        """
        Check if the market for the given match is available via Betika API.
        Updates the match dict with the current odd if found.

        :param match: Dict containing 'parent_match_id', 'sub_type_id', 'bet_pick'
        :return: Updated match dict if available, else None
        """
        try:
            url = f"https://api.betika.com/v1/uo/match?parent_match_id={match['parent_match_id']}"
            match_details = self.betika.get_data(url)
            if not match_details or not match_details.get('data'):
                logger.warning("No match details found for parent_match_id: %s", match['parent_match_id'])
                return None

            target_sub_type_id = match['sub_type_id']
            target_bet_pick = match['bet_pick']

            for datum in match_details['data']:
                if int(datum.get('sub_type_id', 0)) == target_sub_type_id:
                    for odd in datum.get('odds', []):
                        if odd.get('odd_key') == target_bet_pick:
                            match['odd'] = odd.get('odd_value')
                            logger.debug("Market available for match: %s, odd: %s", match['parent_match_id'],  match['odd'])
                            return match

            logger.debug("No matching odd found for sub_type_id: %s, bet_pick: %s", target_sub_type_id, target_bet_pick)
            return None

        except KeyError as e:
            logger.error("Missing required key in match dict: %s", e)
            return None
        except Exception as e:
            logger.error("Error checking market availability for match %s: %s", match.get('parent_match_id', 'unknown'), e)
            return None

    def _place_bets_for_group(
        self, helper: Helper, matches: List[Dict], stake: int
    ) -> None:
        """Place bets for a group of matches with a delay between each."""
        for match in matches:
            try:
                helper.auto_bet([match], max(1, stake))  # Pass as list for consistency
                logger.info("Placed bet for match %s on profile %s", match['parent_match_id'], helper.betika.phone)
                time.sleep(BET_DELAY_SECONDS)
            except Exception as e:
                logger.error("Failed to place bet for match %s: %s", match.get('parent_match_id', 'unknown'), e)

    def bet(self, profile: Tuple[str, str], bet_size: int = DEFAULT_BET_SIZE) -> None:
        """
        Execute betting logic for a single profile.

        :param profile: Tuple of (phone, password)
        :param bet_size: Number of matches per bet group
        """
        try:
            helper = Helper(phone=profile[0], password=profile[1])
            balance = helper.betika.balance

            if balance < MIN_BALANCE:
                logger.info("Insufficient balance for profile %s: %s", profile[0], balance)
                return

            unplaced_matches = self.db.fetch_unplaced_matches(helper.betika.profile_id)
            if not unplaced_matches:
                logger.info("No unplaced matches for profile %s", profile[0])
                return

            # Filter available matches
            available_matches = [
                self.is_market_available(match) for match in unplaced_matches
            ]
            available_matches = [m for m in available_matches if m is not None]

            if not available_matches:
                logger.info("No available markets for profile %s", profile[0])
                return

            # Group matches into chunks of bet_size
            grouped_matches = [
                available_matches[i : i + bet_size]
                for i in range(0, len(available_matches), bet_size)
            ]
            # Filter groups with sufficient size
            grouped_matches = [
                group for group in grouped_matches if len(group) >= MIN_GROUP_SIZE
            ]

            if not grouped_matches:
                logger.info("No viable groups (min %s matches) for profile %s", MIN_GROUP_SIZE, profile[0])
                return

            # Withdraw before betting
            self.withdraw.withdraw(profile)
            logger.info("Withdrawn funds for profile %s", profile[0])

            # Calculate stake per group (integer division)
            num_groups = len(grouped_matches)
            stake_per_group = int(balance / num_groups)

            # Place bets for each group
            for group in grouped_matches:
                self._place_bets_for_group(helper, group, stake_per_group)

            logger.info("Betting completed for profile %s: %s matches in %s groups", profile[0], len(available_matches), num_groups)

        except IndexError:
            logger.error("Invalid profile format: %s (expected [phone, password])", profile)
        except Exception as e:
            logger.error("Unexpected error in bet for profile %s: %s", profile[0] if len(profile) > 0 else 'unknown', e)

    def __call__(self) -> None:
        """
        Entry point: Fetch active profiles and bet in parallel using threads.
        """
        active_profiles = self.db.get_active_profiles()
        if not active_profiles:
            logger.info("No active profiles found")
            return

        logger.info("Starting autobet for %s profiles", len(active_profiles))

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.bet, profile) for profile in active_profiles]
            concurrent.futures.wait(futures)

        logger.info("Autobet execution completed")