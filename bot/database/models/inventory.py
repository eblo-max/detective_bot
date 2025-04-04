from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.models.base import Base
from bot.database.models.user import User


class Inventory(Base):
    """Модель инвентаря пользователя"""

    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    items: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship("User", back_populates="inventory")

    def add_item(self, item: Dict[str, Any]) -> None:
        """
        Добавляет предмет в инвентарь.

        Args:
            item: Словарь с информацией о предмете
        """
        self.items.append(item)
        self.updated_at = datetime.now(timezone.utc)

    def remove_item(self, item_id: str) -> bool:
        """
        Удаляет предмет из инвентаря.

        Args:
            item_id: ID предмета для удаления

        Returns:
            bool: True если предмет найден и удален, False если не найден
        """
        for i, item in enumerate(self.items):
            if item.get("id") == item_id:
                self.items.pop(i)
                self.updated_at = datetime.now(timezone.utc)
                return True
        return False

    def update_item(self, item_id: str, new_data: Dict[str, Any]) -> bool:
        """
        Обновляет информацию о предмете.

        Args:
            item_id: ID предмета для обновления
            new_data: Новые данные предмета

        Returns:
            bool: True если предмет найден и обновлен, False если не найден
        """
        for item in self.items:
            if item.get("id") == item_id:
                item.update(new_data)
                self.updated_at = datetime.now(timezone.utc)
                return True
        return False

    def has_item(self, item_id: str) -> bool:
        """
        Проверяет наличие предмета в инвентаре.

        Args:
            item_id: ID предмета

        Returns:
            bool: True если предмет есть, False если нет
        """
        return any(item.get("id") == item_id for item in self.items)

    def get_item_quantity(self, item_id: str) -> int:
        """
        Возвращает количество предметов в инвентаре.

        Args:
            item_id: ID предмета

        Returns:
            int: Количество предметов
        """
        return sum(1 for item in self.items if item.get("id") == item_id)

    def update_capacity(self, new_capacity: int) -> None:
        """
        Обновляет вместимость инвентаря.

        Args:
            new_capacity: Новая вместимость
        """
        self.capacity = new_capacity
        self.updated_at = datetime.now(timezone.utc)

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
