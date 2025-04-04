from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Table, Column, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.models.base import Base

if TYPE_CHECKING:
    from bot.database.models.user import User


class NewsCategory(str, Enum):
    """Категории новостей"""

    CRIME = "crime"  # Преступления
    INVESTIGATION = "investigation"  # Расследования
    CITY = "city"  # Городские новости
    POLICE = "police"  # Полицейские новости
    OTHER = "other"  # Прочее


class NewsTag(Base):
    """Модель тегов новостей"""

    __tablename__ = "news_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    news: Mapped[List["News"]] = relationship(
        "News", secondary="news_tags_association", back_populates="tags"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
        }


# Таблица связи новостей и тегов
news_tags_association = Table(
    "news_tags_association",
    Base.metadata,
    Column("news_id", Integer, ForeignKey("news.id")),
    Column("tag_id", Integer, ForeignKey("news_tags.id")),
)


class News(Base):
    """Модель новостей"""

    __tablename__ = "news"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[NewsCategory] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("user.id"), nullable=True)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="news")
    tags: Mapped[List[NewsTag]] = relationship(
        NewsTag, secondary=news_tags_association, back_populates="news"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь"""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "category": self.category,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "user_id": self.user_id,
            "tags": [tag.to_dict() for tag in self.tags],
        }
