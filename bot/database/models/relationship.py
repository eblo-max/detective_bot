from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Enum as SQLAlchemyEnum,
    Float,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.models.base import Base

if TYPE_CHECKING:
    from bot.database.models.user import User


class RelationshipStatus(str, Enum):
    """Статусы отношений между пользователями"""

    NEUTRAL = "neutral"
    FRIENDLY = "friendly"
    RIVAL = "rival"


class Relationship(Base):
    """Модель отношений между пользователями"""

    __tablename__ = "relationship"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    target_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    status: Mapped[RelationshipStatus] = mapped_column(
        String, nullable=False, default=RelationshipStatus.NEUTRAL
    )
    trust_level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # от -100 до 100
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship(
        "User", foreign_keys=[user_id], back_populates="outgoing_relationships"
    )
    target: Mapped["User"] = relationship(
        "User", foreign_keys=[target_id], back_populates="incoming_relationships"
    )

    def update_trust(self, amount: int) -> None:
        """
        Обновляет уровень доверия в отношениях.

        Args:
            amount: Количество очков доверия (положительное или отрицательное)
        """
        self.trust_level = max(-100, min(100, self.trust_level + amount))
        self._update_status()
        self.updated_at = datetime.utcnow()

    def _update_status(self) -> None:
        """
        Обновляет статус отношений на основе уровня доверия.
        """
        if self.trust_level >= 50:
            self.status = RelationshipStatus.FRIENDLY
        elif self.trust_level <= -50:
            self.status = RelationshipStatus.RIVAL
        else:
            self.status = RelationshipStatus.NEUTRAL

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "target_id": self.target_id,
            "status": self.status.value,
            "trust_level": self.trust_level,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
