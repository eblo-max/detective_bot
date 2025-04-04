from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime

from bot.database.db import Base

# Связующая таблица для отношения many-to-many между User и Case
user_cases = Table(
    "user_cases",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("case_id", Integer, ForeignKey("cases.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Игровые характеристики
    level = Column(Integer, default=1)
    experience = Column(Integer, default=0)
    energy = Column(Integer, default=100)
    psychology_skill = Column(Integer, default=1)
    investigation_skill = Column(Integer, default=1)
    deduction_skill = Column(Integer, default=1)

    # Отношения
    user_achievements = relationship(
        "UserAchievement", back_populates="user", cascade="all, delete-orphan"
    )
    active_cases = relationship(
        "Case", secondary=user_cases, back_populates="investigators"
    )


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    achievement_id = Column(Integer, ForeignKey("achievements.id"))
    unlocked_at = Column(DateTime, default=datetime.utcnow)

    # Отношения
    user = relationship("User", back_populates="user_achievements")
    achievement = relationship("Achievement")


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String)
    difficulty = Column(Integer, default=1)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Отношения
    investigators = relationship(
        "User", secondary=user_cases, back_populates="active_cases"
    )


class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String)
    condition = Column(String)
    points = Column(Integer, default=0)
