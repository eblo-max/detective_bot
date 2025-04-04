"""Модуль для кэширования запросов к Claude API."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, Optional


class AsyncTTLCache:
    """Асинхронный кэш с временем жизни записей."""

    def __init__(self, ttl: int = 3600):
        """
        Инициализация кэша.

        Args:
            ttl: Время жизни записей в секундах (по умолчанию 1 час)
        """
        self.ttl = ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """
        Получение значения из кэша.

        Args:
            key: Ключ для поиска

        Returns:
            Any: Значение из кэша или None, если ключ не найден или истек срок жизни
        """
        async with self.lock:
            if key not in self.cache:
                return None

            entry = self.cache[key]
            if datetime.now() - entry["timestamp"] > timedelta(seconds=self.ttl):
                del self.cache[key]
                return None

            return entry["value"]

    async def set(self, key: str, value: Any) -> None:
        """
        Сохранение значения в кэш.

        Args:
            key: Ключ для сохранения
            value: Значение для сохранения
        """
        async with self.lock:
            self.cache[key] = {
                "value": value,
                "timestamp": datetime.now(),
            }

    async def delete(self, key: str) -> None:
        """
        Удаление значения из кэша.

        Args:
            key: Ключ для удаления
        """
        async with self.lock:
            if key in self.cache:
                del self.cache[key]

    async def clear(self) -> None:
        """Очистка всего кэша."""
        async with self.lock:
            self.cache.clear()

    async def cleanup(self) -> None:
        """Удаление устаревших записей."""
        async with self.lock:
            now = datetime.now()
            expired_keys = [
                key
                for key, entry in self.cache.items()
                if now - entry["timestamp"] > timedelta(seconds=self.ttl)
            ]
            for key in expired_keys:
                del self.cache[key]
