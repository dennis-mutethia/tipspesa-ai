
from typing import Optional
from datetime import datetime

from sqlalchemy import String, Integer, Float, DateTime, Boolean, UniqueConstraint, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

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


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


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
