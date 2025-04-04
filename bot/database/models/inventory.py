from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.models.base import Base
from bot.database.models.user import User


class Inventory(Base):
    """Модель инвентаря пользователя"""

    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    items: Mapped[Dict[str, int]] = mapped_column(
        JSON, nullable=False, default=dict
    )  # {item_id: quantity}
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship("User", back_populates="inventory")

    def add_item(self, item_id: str, quantity: int = 1) -> bool:
        """
        Добавляет предмет в инвентарь.

        Args:
            item_id: ID предмета
            quantity: Количество предметов

        Returns:
            bool: True если предмет добавлен, False если инвентарь полон
        """
        current_items = sum(self.items.values())
        if current_items + quantity > self.capacity:
            return False

        self.items[item_id] = self.items.get(item_id, 0) + quantity
        self.updated_at = datetime.utcnow()
        return True

    def remove_item(self, item_id: str, quantity: int = 1) -> bool:
        """
        Удаляет предмет из инвентаря.

        Args:
            item_id: ID предмета
            quantity: Количество предметов

        Returns:
            bool: True если предмет удален, False если предмета нет или недостаточно
        """
        if item_id not in self.items or self.items[item_id] < quantity:
            return False

        self.items[item_id] -= quantity
        if self.items[item_id] == 0:
            del self.items[item_id]
        self.updated_at = datetime.utcnow()
        return True

    def has_item(self, item_id: str) -> bool:
        """
        Проверяет наличие предмета в инвентаре.

        Args:
            item_id: ID предмета

        Returns:
            bool: True если предмет есть, False если нет
        """
        return item_id in self.items and self.items[item_id] > 0

    def get_item_quantity(self, item_id: str) -> int:
        """
        Возвращает количество предметов в инвентаре.

        Args:
            item_id: ID предмета

        Returns:
            int: Количество предметов
        """
        return self.items.get(item_id, 0)

    def update_capacity(self, new_capacity: int) -> None:
        """
        Обновляет вместимость инвентаря.

        Args:
            new_capacity: Новая вместимость
        """
        self.capacity = new_capacity
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "items": self.items,
            "capacity": self.capacity,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
