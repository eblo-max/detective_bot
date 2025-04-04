from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional

from sqlalchemy import (
    DateTime,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Integer,
    String,
    Float,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.models.base import Base
from bot.database.models.user import User


class SkillType(str, Enum):
    """Типы навыков"""

    OBSERVATION = "observation"
    DEDUCTION = "deduction"
    INTERROGATION = "interrogation"
    FORENSICS = "forensics"
    PSYCHOLOGY = "psychology"


class Skill(Base):
    """Модель навыка"""

    __tablename__ = "skill"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[SkillType] = mapped_column(SQLAlchemyEnum(SkillType), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.type.value,
            "created_at": self.created_at.isoformat(),
        }


class UserSkill(Base):
    """Модель связи пользователя с навыком"""

    __tablename__ = "user_skill"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skill.id"), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    experience: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship("User", back_populates="skills")
    skill: Mapped["Skill"] = relationship("Skill")

    def add_experience(self, amount: int) -> bool:
        """
        Добавляет опыт навыку.

        Args:
            amount: Количество опыта

        Returns:
            bool: True если уровень повышен
        """
        self.experience += amount
        return self.check_level_up()

    def check_level_up(self) -> bool:
        """
        Проверяет, нужно ли повысить уровень навыка.

        Returns:
            bool: True если уровень повышен
        """
        required_exp = (
            self.level * 1000
        )  # Простая формула: каждый уровень требует на 1000 опыта больше
        if self.experience >= required_exp:
            self.level += 1
            self.experience -= required_exp
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "skill_id": self.skill_id,
            "level": self.level,
            "experience": self.experience,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
