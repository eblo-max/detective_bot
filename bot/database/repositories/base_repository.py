from typing import TypeVar, Generic, Type, List, Optional, Any, Dict
from sqlalchemy.orm import Session
from sqlalchemy import select

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Базовый класс для всех репозиториев"""

    def __init__(self, session: Session, model: Type[T]):
        self.session = session
        self.model = model

    def get_all(self) -> List[T]:
        """Получить все записи"""
        return self.session.query(self.model).all()

    def get_by_id(self, id: int) -> Optional[T]:
        """Получить запись по ID"""
        return self.session.query(self.model).filter(self.model.id == id).first()

    def create(self, **kwargs: Any) -> T:
        """Создать новую запись"""
        instance = self.model(**kwargs)
        self.session.add(instance)
        self.session.commit()
        return instance

    def update(self, id: int, **kwargs: Any) -> Optional[T]:
        """Обновить запись"""
        instance = self.get_by_id(id)
        if instance:
            for key, value in kwargs.items():
                setattr(instance, key, value)
            self.session.commit()
        return instance

    def delete(self, id: int) -> bool:
        """Удалить запись"""
        instance = self.get_by_id(id)
        if instance:
            self.session.delete(instance)
            self.session.commit()
            return True
        return False
