import logging
import os
import uuid
from typing import List, Dict, Any, Set, Optional, Tuple
from datetime import datetime

from sqlalchemy import (
    create_engine, String, Integer, Float, DateTime, Boolean,
    text, insert, update, select, and_, not_, func, UniqueConstraint,
    ForeignKey
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, relationship
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import insert as pg_insert
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


# =========================
# ORM MODELS
# =========================

class Base(DeclarativeBase):
    pass


class Match(Base):
    __tablename__ = "matches"

    match_id: Mapped[str] = mapped_column(String, primary_key=True)
    kickoff: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    home_team: Mapped[str] = mapped_column(String, nullable=False)
    away_team: Mapped[str] = mapped_column(String, nullable=False)
    league: Mapped[str] = mapped_column(String, nullable=False)
    prediction: Mapped[str] = mapped_column(String, nullable=False)
    odd: Mapped[float] = mapped_column(Float, nullable=False)
    overall_prob: Mapped[float] = mapped_column(Float, nullable=False)
    parent_match_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sub_type_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bet_pick: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    special_bet_value: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    outcome_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    home_results: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    away_results: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class Betslip(Base):
    __tablename__ = "betslips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String, nullable=False)
    profile_id: Mapped[str] = mapped_column(String, ForeignKey("profiles.id"), nullable=False)
    parent_match_id: Mapped[str] = mapped_column(String, nullable=False)

    profile: Mapped["Profile"] = relationship("Profile", back_populates="betslips")


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    betslips: Mapped[List["Betslip"]] = relationship("Betslip", back_populates="profile")


class SourceModel(Base):
    __tablename__ = "source_model"
    __table_args__ = (UniqueConstraint("parent_match_id", "model", name="uq_parent_model"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_match_id: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    kickoff: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class JackpotMatch(Base):
    __tablename__ = "jackpot_matches"
    __table_args__ = (
        UniqueConstraint("parent_match_id", "model", name="uq_jackpot_parent_model"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    event_id: Mapped[str] = mapped_column(String, nullable=False)
    event_name: Mapped[str] = mapped_column(String, nullable=False)
    parent_match_id: Mapped[str] = mapped_column(String, nullable=False)
    home_team: Mapped[str] = mapped_column(String, nullable=False)
    away_team: Mapped[str] = mapped_column(String, nullable=False)
    sub_type_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bet_pick: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    outcome_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    overall_prob: Mapped[float] = mapped_column(Float, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    home_team: Mapped[str] = mapped_column(String, nullable=False)
    away_team: Mapped[str] = mapped_column(String, nullable=False)
    bet_pick: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    odd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    odd_change: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tournament: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    sport: Mapped[str] = mapped_column(String, nullable=False)
    home_results: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    away_results: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)


# =========================
# DB CLASS (ORM)
# =========================

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
                    .where(Match.kickoff > func.now() + text("INTERVAL '3 hours'"))
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
                    .where(SourceModel.kickoff > func.now() + text("INTERVAL '3 hours'"))
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
                    .where(SourceModel.kickoff > func.now() + text("INTERVAL '3 hours'"))
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
                    .where(Event.start_time < func.now())
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