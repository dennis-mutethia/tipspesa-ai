import logging
import os
import uuid
from typing import List, Dict, Any, Set, Optional
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class Db:
    def __init__(self):
        load_dotenv()
        self.engine: Engine = create_engine(
            os.getenv("DATABASE_URL"),
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            echo=False  # Set to True for SQL logging during debug
        )

    def _get_connection(self):
        return self.engine.connect()

    def insert_matches(self, matches: List[Dict[str, Any]]) -> None:
        query = text("""
            INSERT INTO matches(
                match_id, kickoff, home_team, away_team, league, prediction, odd,
                overall_prob, parent_match_id, sub_type_id, bet_pick, special_bet_value, outcome_id
            )
            VALUES(
                :match_id, :kickoff, :home_team, :away_team, :league, :prediction, :odd,
                :overall_prob, :parent_match_id, :sub_type_id, :bet_pick, :special_bet_value, :outcome_id
            )
            ON CONFLICT (match_id) DO UPDATE SET
                prediction = EXCLUDED.prediction,
                odd = EXCLUDED.odd,
                overall_prob = EXCLUDED.overall_prob
        """)

        values = [
            {
                'match_id': str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{m['match_id']}{m['prediction']}")),
                'kickoff': m['start_time'],
                'home_team': m['home_team'].replace("'", "''"),
                'away_team': m['away_team'].replace("'", "''"),
                'league': m['category'].replace("'", "''"),
                'prediction': m['prediction'],
                'odd': m['odd'],
                'overall_prob': m['overall_prob'],
                'parent_match_id': m['parent_match_id'],
                'sub_type_id': m['sub_type_id'],
                'bet_pick': m['bet_pick'],
                'special_bet_value': m['special_bet_value'],
                'outcome_id': m['outcome_id']
            }
            for m in matches
        ]

        try:
            with self.engine.begin() as conn:  # Auto-commit + rollback on error
                conn.execute(query, values)
        except SQLAlchemyError as e:
            logger.error("Error inserting matches: %s", e)

    def fetch_matches(self, day: str, comparator: str, status: str, limit: int = 16) -> List[tuple]:
        query = text(f"""
            WITH m AS (
                SELECT * FROM matches
                WHERE kickoff::date {comparator} (CURRENT_TIMESTAMP + INTERVAL '3 hours')::date {day} {status}
                  AND overall_prob >= 80
                ORDER BY odd DESC, overall_prob DESC
                LIMIT :limit
            )
            SELECT * FROM m
            ORDER BY kickoff, overall_prob, odd, match_id
        """)

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, {'limit': limit})
                return result.fetchall()
        except SQLAlchemyError as e:
            logger.error("Error fetching matches: %s", e)
            return []

    def fetch_unplaced_matches(self, profile_id: str) -> List[Dict[str, Any]]:
        query = text("""
            WITH m AS (
                SELECT kickoff, home_team, away_team, odd, parent_match_id,
                       sub_type_id, bet_pick, special_bet_value, outcome_id
                FROM matches
                WHERE kickoff > (CURRENT_TIMESTAMP + INTERVAL '3 hours')
            ),
            placed AS (
                SELECT parent_match_id
                FROM betslips
                WHERE profile_id = :profile_id
            )
            SELECT m.*
            FROM m
            WHERE m.parent_match_id NOT IN (SELECT parent_match_id FROM placed WHERE parent_match_id IS NOT NULL)
            ORDER BY kickoff
        """)

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, {'profile_id': profile_id})
                matches = []
                for row in result:
                    matches.append({
                        'start_time': row[0],
                        'home_team': row[1],
                        'away_team': row[2],
                        'odd': row[3],
                        'parent_match_id': row[4],
                        'sub_type_id': row[5],
                        'bet_pick': row[6],
                        'special_bet_value': row[7],
                        'outcome_id': row[8]
                    })
                return matches
        except SQLAlchemyError as e:
            logger.error("Error fetching unplaced matches: %s", e)
            return []

    def fetch_predicted_match_ids(self) -> Set[str]:
        query = text("""
            SELECT parent_match_id
            FROM source_model
            WHERE kickoff > (CURRENT_TIMESTAMP + INTERVAL '3 hours')
        """)

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query)
                return {row[0] for row in result if row[0] is not None}
        except SQLAlchemyError as e:
            logger.error("Error fetching predicted match IDs: %s", e)
            return set()

    def fetch_last_prediction(self) -> Optional[datetime]:
        query = text("""
            SELECT MAX(kickoff)
            FROM source_model
            WHERE kickoff > (CURRENT_TIMESTAMP + INTERVAL '3 hours')
        """)

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query).fetchone()
                return result[0] if result else None
        except SQLAlchemyError as e:
            logger.error("Error fetching last prediction: %s", e)
            return None

    def add_bet_slip(self, profile_id: str, slips: List[Dict[str, Any]], code: str) -> None:
        query = text("""
            INSERT INTO betslips(code, profile_id, parent_match_id)
            VALUES(:code, :profile_id, :parent_match_id)
        """)

        values = [
            {
                'code': code,
                'profile_id': profile_id,
                'parent_match_id': slip['parent_match_id']
            }
            for slip in slips
        ]

        try:
            with self.engine.begin() as conn:
                conn.execute(query, values)
        except SQLAlchemyError as e:
            logger.error("Error adding bet slips: %s", e)

    def update_match_results(self, match_id: str, home_results: int, away_results: int, status: str) -> None:
        query = text("""
            UPDATE matches
            SET home_results = :home_results,
                away_results = :away_results,
                status = :status
            WHERE match_id = :match_id
        """)

        try:
            with self.engine.begin() as conn:
                conn.execute(query, {
                    'home_results': home_results,
                    'away_results': away_results,
                    'status': status,
                    'match_id': match_id
                })
        except SQLAlchemyError as e:
            logger.error("Error updating match results: %s", e)

    def get_active_profiles(self) -> List[tuple]:
        query = text("""
            SELECT phone, password
            FROM profiles
            WHERE is_active IS TRUE
        """)

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query)
                return result.fetchall()
        except SQLAlchemyError as e:
            logger.error("Error fetching active profiles: %s", e)
            return []

    def update_source_model(self, parent_match_id: str, model: str, kickoff: datetime) -> None:
        query = text("""
            INSERT INTO source_model(parent_match_id, model, kickoff)
            VALUES(:parent_match_id, :model, :kickoff)
        """)

        try:
            with self.engine.begin() as conn:
                conn.execute(query, {
                    'parent_match_id': parent_match_id,
                    'model': model,
                    'kickoff': kickoff
                })
        except SQLAlchemyError as e:
            logger.error("Error updating source model: %s", e)

    def insert_jackpot_match(self, match: Dict[str, Any], model: str, event_id: str, event_name: str, provider: str) -> None:
        query = text("""
            INSERT INTO jackpot_matches(
                provider, start_time, event_id, event_name, parent_match_id,
                home_team, away_team, sub_type_id, bet_pick, outcome_id, overall_prob, model
            )
            VALUES(
                :provider, :start_time, :event_id, :event_name, :parent_match_id,
                :home_team, :away_team, :sub_type_id, :bet_pick, :outcome_id, :overall_prob, :model
            )
            ON CONFLICT (parent_match_id, model) DO UPDATE SET
                bet_pick = EXCLUDED.bet_pick,
                outcome_id = EXCLUDED.outcome_id,
                overall_prob = EXCLUDED.overall_prob
        """)

        params = {
            'provider': provider,
            'start_time': match['start_time'],
            'event_id': event_id,
            'event_name': event_name,
            'parent_match_id': match['parent_match_id'],
            'home_team': match['home_team'],
            'away_team': match['away_team'],
            'sub_type_id': match['sub_type_id'],
            'bet_pick': match['bet_pick'],
            'outcome_id': match['outcome_id'],
            'overall_prob': match['overall_prob'],
            'model': model
        }

        try:
            with self.engine.begin() as conn:
                conn.execute(query, params)
        except SQLAlchemyError as e:
            logger.error("Error inserting jackpot match: %s", e)

    def insert_event(self, event: Dict[str, Any]) -> None:
        query = text("""
            INSERT INTO events(
                id, start_time, home_team, away_team, bet_pick, odd, odd_change,
                tournament, category, sport
            )
            VALUES(
                :id, :start_time, :home_team, :away_team, :bet_pick, :odd, :odd_change,
                :tournament, :category, :sport
            )
            ON CONFLICT (id) DO UPDATE SET
                bet_pick = EXCLUDED.bet_pick,
                odd = EXCLUDED.odd,
                odd_change = EXCLUDED.odd_change
        """)

        try:
            with self.engine.begin() as conn:
                conn.execute(query, {
                    'id': event['id'],
                    'start_time': event['start_time'],
                    'home_team': event['home_team'],
                    'away_team': event['away_team'],
                    'bet_pick': event['bet_pick'],
                    'odd': event['odd'],
                    'odd_change': event['odd_change'],
                    'tournament': event['tournament'],
                    'category': event['category'],
                    'sport': event['sport']
                })
        except SQLAlchemyError as e:
            logger.error("Error inserting event: %s", e)

    def get_started_events(self) -> List[Dict[str, Any]]:
        query = text("""
            SELECT id, bet_pick, start_time, CURRENT_TIMESTAMP
            FROM events
            WHERE start_time < CURRENT_TIMESTAMP + INTERVAL '3 hours'
              AND (status IS NULL OR status IN ('notstarted', 'inprogress'))
        """)

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query)
                events = []
                for row in result:
                    events.append({
                        'id': row[0],
                        'bet_pick': row[1]
                    })
                return events
        except SQLAlchemyError as e:
            logger.error("Error fetching started events: %s", e)
            return []

    def update_event_results(self, id: str, home_results: int, away_results: int, status: str) -> None:
        query = text("""
            UPDATE events
            SET home_results = :home_results,
                away_results = :away_results,
                status = :status
            WHERE id = :id
        """)

        try:
            with self.engine.begin() as conn:
                conn.execute(query, {
                    'home_results': home_results,
                    'away_results': away_results,
                    'status': status,
                    'id': id
                })
        except SQLAlchemyError as e:
            logger.error("Error updating event results: %s", e)