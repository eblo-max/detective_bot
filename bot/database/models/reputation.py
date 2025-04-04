from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.models.base import Base
from bot.database.models.user import User


class Reputation(Base):
    """Модель репутации пользователя"""

    __tablename__ = "reputation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rank: Mapped[str] = mapped_column(String, nullable=False, default="Новичок")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship("User", back_populates="reputation")

    def add_points(self, amount: int) -> None:
        """
        Добавляет очки репутации.

        Args:
            amount: Количество очков
        """
        self.points += amount
        self._update_level()
        self._update_rank()
        self.updated_at = datetime.utcnow()

    def _update_level(self) -> None:
        """
        Обновляет уровень репутации.
        """
        self.level = self.points // 1000  # Каждые 1000 очков = новый уровень

    def _update_rank(self) -> None:
        """
        Обновляет ранг пользователя.
        """
        ranks = {
            0: "Новичок",
            1: "Начинающий детектив",
            2: "Опытный детектив",
            3: "Профессиональный детектив",
            4: "Мастер детектив",
            5: "Легендарный детектив",
        }
        self.rank = ranks.get(self.level, "Легендарный детектив")

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "level": self.level,
            "points": self.points,
            "rank": self.rank,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
