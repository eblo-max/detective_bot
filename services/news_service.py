import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union

from services.claude_service.claude_service import ClaudeService
from bot.core.config import config
from bot.database.models.investigation import Investigation
from bot.database.models.news import News, NewsCategory, NewsTag
from bot.database.models.user import User
from bot.database.repositories.news_repository import NewsRepository
from game.player.skills import SkillType

logger = logging.getLogger(__name__)


class NewsCategory(Enum):
    """Категории новостей"""

    CRIME_NEWS = auto()
    SCIENCE_NEWS = auto()
    PSYCHOLOGY_NEWS = auto()
    SPECIAL_NEWS = auto()


@dataclass
class NewsContext:
    """Контекст для генерации новостей"""

    player_level: int
    player_skills: Dict[SkillType, int]
    active_cases: List[str]
    recent_news: List[str]
    player_interests: List[str]


class NewsService:
    """Сервис для работы с новостями."""

    def __init__(self):
        """Инициализация сервиса."""
        self.repository = NewsRepository()
        self.claude_service = ClaudeService()
        self._generation_task: Optional[asyncio.Task] = None

        # Шаблоны промптов для разных категорий
        self._prompt_templates = {
            NewsCategory.CRIME_NEWS: """
            Сгенерируй новость о громком преступлении в формате JSON:
            {{
                "title": "Заголовок новости",
                "content": "Подробное описание",
                "category": "crime",
                "tags": ["теги"],
                "metadata": {{
                    "location": "место преступления",
                    "severity": "уровень серьезности",
                    "hints": ["подсказки для расследования"]
                }}
            }}
            """,
            NewsCategory.SCIENCE_NEWS: """
            Сгенерируй новость о научном открытии в криминалистике в формате JSON:
            {{
                "title": "Заголовок новости",
                "content": "Подробное описание",
                "category": "science",
                "tags": ["теги"],
                "metadata": {{
                    "field": "область науки",
                    "impact": "влияние на расследования",
                    "bonuses": ["временные бонусы к навыкам"]
                }}
            }}
            """,
            NewsCategory.PSYCHOLOGY_NEWS: """
            Сгенерируй новость о психологических аспектах расследований в формате JSON:
            {{
                "title": "Заголовок новости",
                "content": "Подробное описание",
                "category": "psychology",
                "tags": ["теги"],
                "metadata": {{
                    "topic": "тема",
                    "insights": ["психологические инсайты"],
                    "skill_boost": "бонус к навыку психологии"
                }}
            }}
            """,
            NewsCategory.SPECIAL_NEWS: """
            Сгенерируй специальную новость, связанную с игровыми событиями в формате JSON:
            {{
                "title": "Заголовок новости",
                "content": "Подробное описание",
                "category": "special",
                "tags": ["теги"],
                "metadata": {{
                    "event_type": "тип события",
                    "rewards": ["награды"],
                    "special_conditions": ["особые условия"]
                }}
            }}
            """,
        }

    async def get_latest_news(self, limit: int = 5) -> List[News]:
        """
        Получение последних новостей.

        Args:
            limit: Количество новостей для получения

        Returns:
            List[News]: Список последних новостей
        """
        try:
            return await self.repository.get_latest_news(limit)
        except Exception as e:
            logger.error(f"Ошибка при получении новостей: {e}")
            return []

    async def generate_news(self) -> Optional[News]:
        """
        Генерация новой новости с помощью Claude.

        Returns:
            Optional[News]: Сгенерированная новость или None в случае ошибки
        """
        try:
            # Генерируем новость с помощью Claude
            news_data = await self.claude_service.generate_news()

            if not news_data:
                return None

            # Создаем новость в базе данных
            news = await self.repository.create_news(
                title=news_data["title"],
                content=news_data["content"],
                importance=news_data.get("importance", "normal"),
                created_at=datetime.utcnow(),
            )

            return news

        except Exception as e:
            logger.error(f"Ошибка при генерации новости: {e}")
            return None

    async def mark_news_as_read(self, user_id: int, news_id: int) -> bool:
        """
        Отметить новость как прочитанную.

        Args:
            user_id: ID пользователя
            news_id: ID новости

        Returns:
            bool: True если операция успешна, False в противном случае
        """
        try:
            return await self.repository.mark_news_as_read(user_id, news_id)
        except Exception as e:
            logger.error(f"Ошибка при отметке новости как прочитанной: {e}")
            return False

    async def get_unread_news(self, user_id: int) -> List[News]:
        """
        Получение непрочитанных новостей пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            List[News]: Список непрочитанных новостей
        """
        try:
            return await self.repository.get_unread_news(user_id)
        except Exception as e:
            logger.error(f"Ошибка при получении непрочитанных новостей: {e}")
            return []

    async def generate_daily_news(self) -> List[News]:
        """
        Генерирует ежедневные новости для всех категорий.

        Returns:
            List[News]: Список сгенерированных новостей
        """
        news_list = []

        for category in NewsCategory:
            try:
                news = await self._generate_news_for_category(category)
                if news:
                    news_list.append(news)
            except Exception as e:
                logger.error(f"Ошибка при генерации новости категории {category}: {e}")
                continue

        return news_list

    async def get_news_by_category(
        self, category: NewsCategory, limit: int = 5
    ) -> List[News]:
        """
        Получает новости по указанной категории.

        Args:
            category: Категория новостей
            limit: Количество новостей

        Returns:
            List[News]: Список новостей
        """
        return await self.repository.get_news_by_category(category, limit)

    async def generate_personalized_news(self, user: User) -> List[News]:
        """
        Генерирует персонализированные новости для пользователя.

        Args:
            user: Пользователь

        Returns:
            List[News]: Список персонализированных новостей
        """
        # Получаем активное расследование пользователя
        current_investigation = await self._get_user_investigation(user)

        # Формируем контекст для генерации
        context = self._create_news_context(user, current_investigation)

        # Генерируем персонализированные новости
        news = await self.claude_service.generate_news(
            count=3, context=context, category=NewsCategory.SPECIAL_NEWS
        )

        return news

    async def start_periodic_generation(self, interval_hours: int = 24) -> None:
        """
        Запускает периодическую генерацию новостей.

        Args:
            interval_hours: Интервал генерации в часах
        """
        if self._generation_task and not self._generation_task.done():
            logger.warning("Периодическая генерация уже запущена")
            return

        self._generation_task = asyncio.create_task(
            self._periodic_generation(interval_hours)
        )

    async def stop_periodic_generation(self) -> None:
        """Останавливает периодическую генерацию новостей."""
        if self._generation_task and not self._generation_task.done():
            self._generation_task.cancel()
            try:
                await self._generation_task
            except asyncio.CancelledError:
                pass
            self._generation_task = None

    async def _generate_news_for_category(
        self, category: NewsCategory
    ) -> Optional[News]:
        """
        Генерирует новость для указанной категории.

        Args:
            category: Категория новостей

        Returns:
            Optional[News]: Сгенерированная новость
        """
        prompt = self._prompt_templates[category]
        response = await self.claude_service.generate_news(
            count=1, prompt=prompt, category=category
        )

        if not response:
            return None

        news_data = response[0]
        news = News(
            title=news_data["title"],
            content=news_data["content"],
            category=news_data["category"],
            tags=news_data["tags"],
            metadata=news_data["metadata"],
            status="draft",
        )

        await self.repository.save(news)
        return news

    async def _periodic_generation(self, interval_hours: int) -> None:
        """
        Периодически генерирует новости.

        Args:
            interval_hours: Интервал генерации в часах
        """
        while True:
            try:
                await self.generate_daily_news()
                await asyncio.sleep(interval_hours * 3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка при периодической генерации: {e}")
                await asyncio.sleep(300)  # Ждем 5 минут перед повторной попыткой

    async def _get_user_investigation(self, user: User) -> Optional[Investigation]:
        """
        Получает активное расследование пользователя.

        Args:
            user: Пользователь

        Returns:
            Optional[Investigation]: Активное расследование
        """
        if not user.current_investigation_id:
            return None

        return await self.repository.get_by_id(user.current_investigation_id)

    def _create_news_context(
        self, user: User, investigation: Optional[Investigation]
    ) -> Dict[str, Any]:
        """
        Создает контекст для генерации персонализированных новостей.

        Args:
            user: Пользователь
            investigation: Активное расследование

        Returns:
            Dict[str, Any]: Контекст для генерации
        """
        context = {
            "user": {
                "level": user.level,
                "skills": {
                    "detective": user.detective_skill,
                    "forensic": user.forensic_skill,
                    "psychology": user.psychology_skill,
                },
                "achievements": user.stats.get("achievements", []),
            }
        }

        if investigation:
            context["investigation"] = {
                "title": investigation.title,
                "difficulty": investigation.difficulty,
                "current_location": investigation.current_location,
                "progress": investigation.progress,
            }

        return context

    async def _apply_news_effects(self, news: News, user: User) -> None:
        """
        Применяет эффекты новости к пользователю.

        Args:
            news: Новость
            user: Пользователь
        """
        metadata = news.metadata

        # Применяем подсказки для расследования
        if "hints" in metadata:
            await self._apply_investigation_hints(user, metadata["hints"])

        # Применяем бонусы к навыкам
        if "bonuses" in metadata:
            await self._apply_skill_bonuses(user, metadata["bonuses"])

        # Применяем особые условия
        if "special_conditions" in metadata:
            await self._apply_special_conditions(user, metadata["special_conditions"])

    async def _apply_investigation_hints(self, user: User, hints: List[str]) -> None:
        """
        Применяет подсказки к активному расследованию.

        Args:
            user: Пользователь
            hints: Список подсказок
        """
        if not user.current_investigation_id:
            return

        investigation = await self.repository.get_by_id(user.current_investigation_id)
        if not investigation:
            return

        # Добавляем подсказки к прогрессу расследования
        if "hints" not in investigation.progress:
            investigation.progress["hints"] = []

        investigation.progress["hints"].extend(hints)
        await self.repository.save(investigation)

    async def _apply_skill_bonuses(
        self, user: User, bonuses: List[Dict[str, Any]]
    ) -> None:
        """
        Применяет временные бонусы к навыкам.

        Args:
            user: Пользователь
            bonuses: Список бонусов
        """
        if "skill_bonuses" not in user.stats:
            user.stats["skill_bonuses"] = []

        for bonus in bonuses:
            user.stats["skill_bonuses"].append(
                {
                    "skill": bonus["skill"],
                    "amount": bonus["amount"],
                    "expires_at": (
                        datetime.utcnow() + timedelta(hours=bonus["duration"])
                    ).isoformat(),
                }
            )

        await self.repository.save(user)

    async def _apply_special_conditions(
        self, user: User, conditions: List[Dict[str, Any]]
    ) -> None:
        """
        Применяет особые условия из новости.

        Args:
            user: Пользователь
            conditions: Список условий
        """
        if "special_conditions" not in user.stats:
            user.stats["special_conditions"] = []

        for condition in conditions:
            user.stats["special_conditions"].append(
                {
                    "type": condition["type"],
                    "effect": condition["effect"],
                    "expires_at": (
                        datetime.utcnow() + timedelta(hours=condition["duration"])
                    ).isoformat(),
                }
            )

        await self.repository.save(user)

    async def format_news_for_telegram(self, news: News) -> str:
        """Форматирование новости для Telegram"""
        # Форматируем заголовок
        title = f"📰 {news.title}\n\n"

        # Форматируем контент
        content = news.content

        # Добавляем теги
        tags = " ".join(f"#{tag.name}" for tag in news.tags)

        # Добавляем релевантность
        relevance = f"\n\n📊 Релевантность: {int(news.relevance_score * 100)}%"

        return f"{title}{content}{relevance}\n\n{tags}"

    async def get_personalized_news(self, user_id: int, limit: int = 5) -> List[News]:
        """Получение персонализированных новостей для пользователя"""
        # Получаем контекст пользователя
        context = await self._get_user_context(user_id)

        # Получаем новости из базы
        news_items = await self.repository.get_recent_news(limit=limit * 2)

        # Сортируем по релевантности
        for news in news_items:
            news.relevance_score = self._calculate_relevance(
                {"content": news.content, "title": news.title}, context
            )

        # Сортируем и возвращаем самые релевантные
        return sorted(news_items, key=lambda x: x.relevance_score, reverse=True)[:limit]

    async def _get_user_context(self, user_id: int) -> NewsContext:
        """Получение контекста пользователя"""
        # TODO: Реализовать получение контекста из базы данных
        return NewsContext(
            player_level=1,
            player_skills={},
            active_cases=[],
            recent_news=[],
            player_interests=[],
        )

    def _calculate_relevance(
        self, content: Dict, context: Optional[NewsContext]
    ) -> float:
        """Расчет релевантности новости"""
        if not context:
            return 0.5

        relevance = 0.0

        # Релевантность по навыкам
        for skill_type, level in context.player_skills.items():
            if skill_type.value in content["content"].lower():
                relevance += min(level / 10, 0.3)

        # Релевантность по активным расследованиям
        for case in context.active_cases:
            if case.lower() in content["content"].lower():
                relevance += 0.2

        # Релевантность по интересам
        for interest in context.player_interests:
            if interest.lower() in content["content"].lower():
                relevance += 0.1

        return min(relevance, 1.0)
