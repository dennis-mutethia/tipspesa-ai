import time
import concurrent.futures
import logging
from typing import List, Tuple
from utils.betika import Betika
from utils.helper import Helper
from utils.db import Db

# Set up logging for GitHub Actions
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Results():
    def __init__(self):
        self.betika = Betika()
        self.helper = Helper()
        self.db = Db()

    def get_status(self, home_score, away_score, match):
        """Determine the match status based on scores and bet pick."""
        
        # Handle 1x2 bets
        if int(match.sub_type_id) == 1:
            if (match.outcome_id == 1 and home_score < away_score) or \
                (match.outcome_id == 2 and home_score != away_score) or \
                (match.outcome_id == 3 and home_score > away_score):
                    return ''
        
        # Handle double chances        
        if int(match.sub_type_id) == 10:
            if (match.outcome_id == 9 and away_score < home_score) or \
                (match.outcome_id == 10 and home_score == away_score) or \
                (match.outcome_id == 11 and home_score > away_score):
                    return ''   
                
        # Handle overs/unders goals      
        if int(match.sub_type_id) == 18:
            if (match.bet_pick == 'over 0.5' and home_score + away_score < 1) or \
                (match.bet_pick == 'over 1.5' and home_score + away_score < 2) or \
                (match.bet_pick == 'over 2.5' and home_score + away_score < 3) or \
                (match.bet_pick == 'over 3.5' and home_score + away_score < 4) or \
                (match.bet_pick == 'under 3.5' and home_score + away_score > 3) or \
                (match.bet_pick == 'under 4.5' and home_score + away_score > 4) or \
                (match.bet_pick == 'under 5.5' and home_score + away_score > 5):
                    return ''
        
        # Handle both teams to score      
        if int(match.sub_type_id) == 29:
            if (match.bet_pick == 'yes' and (home_score == 0 or away_score == 0)) or \
                (match.bet_pick == 'no' and (home_score > 0 and away_score > 0)):
                    return ''   
        
        # Handle corner bets
        if int(match.sub_type_id) == 166:
            if (match.bet_pick == 'over 6.5' and home_score + away_score < 7) or \
                (match.bet_pick == 'over 7.5' and home_score + away_score < 8) or \
                (match.bet_pick == 'over 8.5' and home_score + away_score < 9) or \
                (match.bet_pick == 'over 8.5' and home_score + away_score < 9) or \
                (match.bet_pick == 'under 9.5' and home_score + away_score > 9) or \
                (match.bet_pick == 'under 10.5' and home_score + away_score > 10) or \
                (match.bet_pick == 'under 11.5' and home_score + away_score > 11):
                    return ''
        
        # Handle goal ranges
        if '-' in match.bet_pick:
            bet_pick = match.bet_pick.split('-')
            if (home_score+away_score) not in range(int(bet_pick[0]), int(bet_pick[1])+1):
                return ''
            
        return 'WON'    

    def process_match(self, match: object) -> Tuple[str, int, int, str]:
        """
        Process a single match: fetch details, calculate status, and update DB.
        Returns (match_id, home_score, away_score, status) for logging.
        """
        try:
            match_details = self.betika.get_match_details(match.parent_match_id, live=True)
            if not match_details:
                logger.info('No match details for match %s', match.match_id)
                return match.match_id, None, None, 'No match details'

            meta = match_details.get("meta", {})
            event_status = meta.get("event_status")
            match_time = meta.get("match_time") #22:50
            current_score = meta.get("current_score")
            if match_time and current_score and event_status in ["1st half", "2nd half"]:
                mins = int(match_time.split(':')[0])
                scores = current_score.split(':')
                home_score, away_score = int(scores[0]), int(scores[1])    
                home_corners = meta.get("home_corners", 0)
                away_corners = meta.get("away_corners", 0)
                home_score = home_corners if match.sub_type_id == 166 else home_score
                away_score = away_corners if match.sub_type_id == 166 else away_score
                status = self.get_status(home_score, away_score, match)
                status = status if mins >= 90 or (('over' in match.bet_pick or match.bet_pick == 'yes') and status == 'WON') else f"{mins} mins"
                if home_score is not None and away_score is not None:
                    logger.info('%s vs %s [%s] = %d:%d - %s', match.home_team, match.away_team, match.bet_pick, home_score, away_score, status)
                
                self.db.update_match_results(match.match_id, home_score, away_score, status)
                return match.match_id, home_score, away_score, status
            else:
                # logger.info('No current score for match %s vs %s', match.home_team, match.away_team)
                return match.match_id, None, None, None
        except Exception as e:
            logger.error('Error processing match %s: %s', match.match_id, e)
            return match.match_id, None, None, 'Error: %s' % e

    def __call__(self, matches) -> List[Tuple[str, int, int, str]]:
        """
        Fetch matches and process them concurrently.
        Returns list of (match_id, home_score, away_score, status) for each match.
        """

        results = []
        # Use ThreadPoolExecutor for concurrent processing
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Map process_match to each match concurrently
            futures = [executor.submit(self.process_match, match) for match in matches]
            # Collect results as they complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    match_id, home_score, away_score, status = result
                    if home_score is not None and away_score is not None:
                        results.append(result)
                except Exception as e:
                    logger.error('Error in concurrent processing: %s', e)
                    results.append((None, None, None, 'Error: %s' % e))

        return results


if __name__ == "__main__":
    logger.info('>>>>>>>> Starting Results task >>>>>>>>')
    try:
        results_processor = Results()
        matches = results_processor.helper.fetch_matches('', '=', '', limit=1000)
        logger.info('Fetched %d matches to process', len(matches))    
        results = results_processor(matches)
        logger.info('Updated %d matches updated', len(results))        
    except Exception as e:
        logger.error('Error in cycle: %s', e)
        
    logger.info('<<<<<<<< Results Task completed >>>>>>>>')