from datetime import datetime, timezone
from typing import Dict, Any, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.models.base import Base
from bot.database.models.user import User


class UserStats(Base):
    """Модель статистики пользователя"""

    __tablename__ = "user_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    experience: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    solved_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    perfect_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_reward: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cases_solved: Mapped[int] = mapped_column(Integer, default=0)
    cases_failed: Mapped[int] = mapped_column(Integer, default=0)
    evidence_found: Mapped[int] = mapped_column(Integer, default=0)
    suspects_interrogated: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship("User", back_populates="stats")

    def add_experience(self, amount: int) -> None:
        """
        Добавляет опыт и проверяет повышение уровня.

        Args:
            amount: Количество опыта
        """
        self.experience += amount
        self._check_level_up()
        self.updated_at = datetime.now(timezone.utc)

    def _check_level_up(self) -> None:
        """
        Проверяет повышение уровня.
        """
        required_exp = self.level * 1000  # Каждые 1000 опыта = новый уровень
        while self.experience >= required_exp:
            self.level += 1
            self.experience -= required_exp
            required_exp = self.level * 1000

    def add_solved_case(self, reward: int, is_perfect: bool = False) -> None:
        """
        Добавляет решенное дело.

        Args:
            reward: Награда за дело
            is_perfect: Является ли решение идеальным
        """
        self.solved_cases += 1
        if is_perfect:
            self.perfect_cases += 1
        self.total_reward += reward
        self.updated_at = datetime.now(timezone.utc)

    def add_failed_case(self) -> None:
        """
        Добавляет проваленное дело.
        """
        self.failed_cases += 1
        self.updated_at = datetime.now(timezone.utc)

    def add_evidence(self) -> None:
        """Добавляет найденную улику"""
        self.evidence_found += 1
        self.updated_at = datetime.now(timezone.utc)

    def add_interrogation(self) -> None:
        """Добавляет допрошенного подозреваемого"""
        self.suspects_interrogated += 1
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "level": self.level,
            "experience": self.experience,
            "solved_cases": self.solved_cases,
            "perfect_cases": self.perfect_cases,
            "failed_cases": self.failed_cases,
            "total_reward": self.total_reward,
            "cases_solved": self.cases_solved,
            "cases_failed": self.cases_failed,
            "evidence_found": self.evidence_found,
            "suspects_interrogated": self.suspects_interrogated,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
