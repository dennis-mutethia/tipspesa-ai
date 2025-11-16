import logging
import os
import uuid
from typing import List, Dict, Any, Set, Optional, Tuple
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import create_engine, func, text, insert, update, select, and_
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import insert as pg_insert

from utils.models import Match, Betslip, Profile, SourceModel, JackpotMatch, Event

logger = logging.getLogger(__name__)


class Db:
    def __init__(self):
        load_dotenv()
        self.engine = create_engine(
            os.getenv('DATABASE_URL'),
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            echo=False
        )
        # Optional: Create tables if not exist
        # Base.metadata.create_all(self.engine)

    def _session(self):
        return Session(self.engine)

    def insert_matches(self, matches: List[Dict[str, Any]]) -> None:
        stmt = pg_insert(Match).values([
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
                'outcome_id': m['outcome_id'],
            }
            for m in matches
        ])

        stmt = stmt.on_conflict_do_update(
            index_elements=['match_id'],
            set_={
                'prediction': stmt.excluded.prediction,
                'odd': stmt.excluded.odd,
                'overall_prob': stmt.excluded.overall_prob
            }
        )

        try:
            with self._session() as session:
                session.execute(stmt)
                session.commit()
        except SQLAlchemyError as e:
            logger.error("Error inserting matches: %s", e)

    def fetch_matches(self, day: str, comparator: str, status: str, limit: int = 16) -> List[Tuple]:
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
        try:
            with self._session() as session:
                placed_subq = select(Betslip.parent_match_id).where(Betslip.profile_id == profile_id).scalar_subquery()
                matches = session.execute(
                    select(
                        Match.kickoff,
                        Match.home_team,
                        Match.away_team,
                        Match.odd,
                        Match.parent_match_id,
                        Match.sub_type_id,
                        Match.bet_pick,
                        Match.special_bet_value,
                        Match.outcome_id
                    )
                    .where(Match.kickoff > datetime.now())
                    .where(Match.parent_match_id.not_in(placed_subq))
                    .order_by(Match.kickoff)
                )

                result = []
                for row in matches:
                    result.append({
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
                return result
        except SQLAlchemyError as e:
            logger.error("Error fetching unplaced matches: %s", e)
            return []

    def fetch_predicted_match_ids(self) -> Set[str]:
        try:
            with self._session() as session:
                result = session.execute(
                    select(SourceModel.parent_match_id)
                    .where(SourceModel.kickoff > datetime.now())
                )
                return {row[0] for row in result if row[0]}
        except SQLAlchemyError as e:
            logger.error("Error fetching predicted match IDs: %s", e)
            return set()

    def fetch_last_prediction(self) -> Optional[datetime]:
        try:
            with self._session() as session:
                result = session.execute(
                    select(func.max(SourceModel.kickoff))
                    .where(SourceModel.kickoff > datetime.now())
                ).scalar()
                return result
        except SQLAlchemyError as e:
            logger.error("Error fetching last prediction: %s", e)
            return None

    def add_bet_slip(self, profile_id: str, slips: List[Dict[str, Any]], code: str) -> None:
        try:
            with self._session() as session:
                session.execute(
                    insert(Betslip),
                    [
                        {
                            'code': code,
                            'profile_id': profile_id,
                            'parent_match_id': slip['parent_match_id']
                        }
                        for slip in slips
                    ]
                )
                session.commit()
        except SQLAlchemyError as e:
            logger.error("Error adding bet slips: %s", e)

    def update_match_results(self, match_id: str, home_results: int, away_results: int, status: str) -> None:
        try:
            with self._session() as session:
                session.execute(
                    update(Match)
                    .where(Match.match_id == match_id)
                    .values(
                        home_results=home_results,
                        away_results=away_results,
                        status=status
                    )
                )
                session.commit()
        except SQLAlchemyError as e:
            logger.error("Error updating match results: %s", e)

    def get_active_profiles(self) -> List[Tuple[str, str]]:
        try:
            with self._session() as session:
                result = session.execute(
                    select(Profile.phone, Profile.password)
                    .where(Profile.is_active.is_(True))
                )
                return result.fetchall()
        except SQLAlchemyError as e:
            logger.error("Error fetching active profiles: %s", e)
            return []

    def update_source_model(self, parent_match_id: str, model: str, kickoff: datetime) -> None:
        try:
            with self._session() as session:
                session.execute(
                    insert(SourceModel).values(
                        parent_match_id=parent_match_id,
                        model=model,
                        kickoff=kickoff
                    )
                )
                session.commit()
        except SQLAlchemyError as e:
            logger.error("Error updating source model: %s", e)

    def insert_jackpot_match(self, match: Dict[str, Any], model: str, event_id: str, event_name: str, provider: str) -> None:
        stmt = pg_insert(JackpotMatch).values(
            provider=provider,
            start_time=match['start_time'],
            event_id=event_id,
            event_name=event_name,
            parent_match_id=match['parent_match_id'],
            home_team=match['home_team'],
            away_team=match['away_team'],
            sub_type_id=match['sub_type_id'],
            bet_pick=match['bet_pick'],
            outcome_id=match['outcome_id'],
            overall_prob=match['overall_prob'],
            model=model
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=['parent_match_id', 'model'],
            set_={
                'bet_pick': stmt.excluded.bet_pick,
                'outcome_id': stmt.excluded.outcome_id,
                'overall_prob': stmt.excluded.overall_prob
            }
        )

        try:
            with self._session() as session:
                session.execute(stmt)
                session.commit()
        except SQLAlchemyError as e:
            logger.error("Error inserting jackpot match: %s", e)

    def insert_event(self, event: Dict[str, Any]) -> None:
        stmt = pg_insert(Event).values(
            id=event['id'],
            start_time=event['start_time'],
            home_team=event['home_team'],
            away_team=event['away_team'],
            bet_pick=event['bet_pick'],
            odd=event['odd'],
            odd_change=event['odd_change'],
            tournament=event['tournament'],
            category=event['category'],
            sport=event['sport']
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=['id'],
            set_={
                'bet_pick': stmt.excluded.bet_pick,
                'odd': stmt.excluded.odd,
                'odd_change': stmt.excluded.odd_change
            }
        )

        try:
            with self._session() as session:
                session.execute(stmt)
                session.commit()
        except SQLAlchemyError as e:
            logger.error("Error inserting event: %s", e)

    def get_started_events(self) -> List[Dict[str, Any]]:
        try:
            with self._session() as session:
                result = session.execute(
                    select(Event.id, Event.bet_pick)
                    #.where(Event.start_time < datetime.now())
                    .where(
                        and_(
                            Event.status.is_(None),
                            Event.status.in_(['notstarted', 'inprogress'])
                        )
                    )
                )
                return [{'id': row[0], 'bet_pick': row[1]} for row in result]
        except SQLAlchemyError as e:
            logger.error("Error fetching started events: %s", e)
            return []

    def update_event_results(self, id: str, home_results: int, away_results: int, status: str) -> None:
        try:
            with self._session() as session:
                session.execute(
                    update(Event)
                    .where(Event.id == id)
                    .values(
                        home_results=home_results,
                        away_results=away_results,
                        status=status
                    )
                )
                session.commit()
        except SQLAlchemyError as e:
            logger.error("Error updating event results: %s", e)