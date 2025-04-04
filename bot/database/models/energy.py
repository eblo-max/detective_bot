from datetime import datetime, timezone
from typing import Dict, Any, Optional

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.models.base import Base
from bot.database.models.user import User


class Energy(Base):
    """Модель энергии пользователя"""

    __tablename__ = "energy"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    current: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    max_energy: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    last_update: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship("User", back_populates="energy")

    def consume(self, amount: int) -> bool:
        """
        Потребляет энергию.

        Args:
            amount: Количество энергии для потребления

        Returns:
            bool: True если энергии достаточно, False если нет
        """
        if self.current >= amount:
            self.current -= amount
            self.updated_at = datetime.now(timezone.utc)
            return True
        return False

    def restore(self, amount: int) -> None:
        """
        Восстанавливает энергию.

        Args:
            amount: Количество энергии для восстановления
        """
        self.current = min(self.max_energy, self.current + amount)
        self.updated_at = datetime.now(timezone.utc)

    def update_max_energy(self, new_max: int) -> None:
        """
        Обновляет максимальное количество энергии.

        Args:
            new_max: Новое максимальное значение энергии
        """
        self.max_energy = new_max
        self.current = min(self.current, new_max)
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "current": self.current,
            "max_energy": self.max_energy,
            "last_update": self.last_update.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
