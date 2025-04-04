from datetime import datetime
from typing import Dict, Any, Optional, TYPE_CHECKING, List

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.models.base import Base

if TYPE_CHECKING:
    from bot.database.models.user import User


class Achievement(Base):
    """Модель достижения"""

    __tablename__ = "achievement"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user_achievements: Mapped[List["UserAchievement"]] = relationship(
        "UserAchievement", back_populates="achievement", cascade="all, delete-orphan"
    )

    def unlock(self) -> None:
        """
        Разблокирует достижение.
        """
        if not self.is_unlocked:
            self.is_unlocked = True
            self.unlocked_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class UserAchievement(Base):
    """Промежуточная таблица для связи User и Achievement"""

    __tablename__ = "user_achievement"

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), primary_key=True)
    achievement_id: Mapped[int] = mapped_column(
        ForeignKey("achievement.id"), primary_key=True
    )
    unlocked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="achievements")
    achievement: Mapped["Achievement"] = relationship(
        "Achievement", back_populates="user_achievements"
    )

    def is_unlocked(self) -> bool:
        """
        Проверяет, разблокировано ли достижение.

        Returns:
            bool: True если достижение разблокировано
        """
        return self.unlocked_at is not None

    def unlock(self) -> None:
        """
        Разблокирует достижение.
        """
        self.unlocked_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            "user_id": self.user_id,
            "achievement_id": self.achievement_id,
            "unlocked_at": self.unlocked_at.isoformat(),
        }
