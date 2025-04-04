"""Модель дела."""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional, TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.models.base import Base

if TYPE_CHECKING:
    from bot.database.models.user import User


class CaseStatus(Enum):
    """Статусы дела"""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    SOLVED = "solved"
    CLOSED = "closed"


class Case(Base):
    """Модель дела в базе данных."""

    __tablename__ = "case"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[CaseStatus] = mapped_column(
        SQLAlchemyEnum(CaseStatus), nullable=False, default=CaseStatus.OPEN
    )
    difficulty: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )  # от 1 до 5
    reward: Mapped[int] = mapped_column(Integer, nullable=False)  # награда за решение
    evidence: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )  # список улик
    suspects: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )  # список подозреваемых
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    def add_evidence(self, evidence: Dict[str, Any]) -> None:
        """
        Добавляет улику в дело.

        Args:
            evidence: Словарь с информацией об улике
        """
        self.evidence.append(evidence)
        self.updated_at = datetime.now(timezone.utc)

    def add_suspect(self, suspect: Dict[str, Any]) -> None:
        """
        Добавляет подозреваемого в дело.

        Args:
            suspect: Словарь с информацией о подозреваемом
        """
        self.suspects.append(suspect)
        self.updated_at = datetime.now(timezone.utc)

    def update_status(self, new_status: CaseStatus) -> None:
        """
        Обновляет статус дела.

        Args:
            new_status: Новый статус
        """
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)

    def get_evidence(self) -> List[Dict[str, Any]]:
        """
        Возвращает список улик.

        Returns:
            List[Dict[str, Any]]: Список улик
        """
        return self.evidence

    def get_suspects(self) -> List[Dict[str, Any]]:
        """
        Возвращает список подозреваемых.

        Returns:
            List[Dict[str, Any]]: Список подозреваемых
        """
        return self.suspects

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "difficulty": self.difficulty,
            "reward": self.reward,
            "evidence": self.evidence,
            "suspects": self.suspects,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class UserCase(Base):
    """Модель связи пользователя с делом"""

    __tablename__ = "user_case"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="in_progress")
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc)
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="cases")
    case: Mapped["Case"] = relationship("Case")

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "case_id": self.case_id,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }
