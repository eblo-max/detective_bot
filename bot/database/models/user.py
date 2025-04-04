from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Integer,
    BigInteger,
    String,
    Float,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.models.base import Base
from bot.database.models.achievement import Achievement, UserAchievement
from bot.database.models.relationship import Relationship
from bot.database.models.investigation import Investigation
from bot.database.models.case import UserCase

if TYPE_CHECKING:
    from bot.database.models.resources import Energy, Inventory, Reputation
    from bot.database.models.news import News
    from bot.database.models.skill import UserSkill


class UserStatus(str, Enum):
    """Статусы пользователя"""

    ACTIVE = "active"
    BANNED = "banned"
    DELETED = "deleted"


class UserStats(Base):
    """Модель статистики пользователя"""

    __tablename__ = "user_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), unique=True)
    level: Mapped[int] = mapped_column(Integer, default=1)
    experience: Mapped[int] = mapped_column(Integer, default=0)
    total_cases: Mapped[int] = mapped_column(Integer, default=0)
    solved_cases: Mapped[int] = mapped_column(Integer, default=0)
    failed_cases: Mapped[int] = mapped_column(Integer, default=0)
    total_evidence_found: Mapped[int] = mapped_column(Integer, default=0)
    total_suspects_interrogated: Mapped[int] = mapped_column(Integer, default=0)
    total_deductions: Mapped[int] = mapped_column(Integer, default=0)
    correct_deductions: Mapped[int] = mapped_column(Integer, default=0)
    wrong_deductions: Mapped[int] = mapped_column(Integer, default=0)
    success_rate: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Связь с пользователем
    user: Mapped["User"] = relationship("User", back_populates="stats")

    def to_dict(self) -> dict:
        """Преобразует объект в словарь"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "level": self.level,
            "experience": self.experience,
            "total_cases": self.total_cases,
            "solved_cases": self.solved_cases,
            "failed_cases": self.failed_cases,
            "total_evidence_found": self.total_evidence_found,
            "total_suspects_interrogated": self.total_suspects_interrogated,
            "total_deductions": self.total_deductions,
            "correct_deductions": self.correct_deductions,
            "wrong_deductions": self.wrong_deductions,
            "success_rate": self.success_rate,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def add_experience(self, amount: int) -> None:
        """Добавляет опыт и обновляет уровень"""
        self.experience += amount
        self.updated_at = datetime.utcnow()

    def update_success_rate(self) -> None:
        """Обновляет процент успешных расследований"""
        if self.total_cases > 0:
            self.success_rate = (self.solved_cases / self.total_cases) * 100
        self.updated_at = datetime.utcnow()


class User(Base):
    """Модель пользователя"""

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username: Mapped[str] = mapped_column(String(50))
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[UserStatus] = mapped_column(
        SQLAlchemyEnum(UserStatus), default=UserStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Связи с другими моделями
    stats: Mapped["UserStats"] = relationship(
        "UserStats", back_populates="user", uselist=False
    )
    energy: Mapped["Energy"] = relationship(
        "Energy", back_populates="user", uselist=False
    )
    inventory: Mapped["Inventory"] = relationship(
        "Inventory", back_populates="user", uselist=False
    )
    reputation: Mapped["Reputation"] = relationship(
        "Reputation", back_populates="user", uselist=False
    )
    achievements: Mapped[List["UserAchievement"]] = relationship(
        "UserAchievement", back_populates="user", cascade="all, delete-orphan"
    )
    outgoing_relationships: Mapped[List["Relationship"]] = relationship(
        "Relationship",
        back_populates="user",
        foreign_keys="[Relationship.user_id]",
        cascade="all, delete-orphan",
    )
    incoming_relationships: Mapped[List["Relationship"]] = relationship(
        "Relationship",
        back_populates="target",
        foreign_keys="[Relationship.target_id]",
        cascade="all, delete-orphan",
    )
    investigations: Mapped[List["Investigation"]] = relationship(
        "Investigation", back_populates="user"
    )
    cases: Mapped[List["UserCase"]] = relationship("UserCase", back_populates="user")
    news: Mapped[List["News"]] = relationship("News", back_populates="user")
    skills: Mapped[List["UserSkill"]] = relationship(
        "UserSkill", back_populates="user", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        """Преобразует объект в словарь"""
        return {
            "id": self.id,
            "telegram_id": self.telegram_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "stats": self.stats.to_dict() if self.stats else None,
            "energy": self.energy.to_dict() if self.energy else None,
            "inventory": self.inventory.to_dict() if self.inventory else None,
            "reputation": self.reputation.to_dict() if self.reputation else None,
            "outgoing_relationships": [
                r.to_dict() for r in self.outgoing_relationships
            ],
            "incoming_relationships": [
                r.to_dict() for r in self.incoming_relationships
            ],
            "investigations": [i.to_dict() for i in self.investigations],
            "skills": [s.to_dict() for s in self.skills] if self.skills else [],
        }

    def update_status(self, new_status: UserStatus) -> None:
        """Обновляет статус пользователя"""
        self.status = new_status
        self.updated_at = datetime.utcnow()

    def get_full_name(self) -> str:
        """Возвращает полное имя пользователя"""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    def get_username(self) -> str:
        """Возвращает имя пользователя"""
        return f"@{self.username}" if self.username else self.get_full_name()
