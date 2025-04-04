import asyncio
import hashlib
import json
import logging
import string
import os
import anthropic
from collections import deque
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass

import aiohttp
import numpy as np
from anthropic import AsyncAnthropic
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from tenacity import retry, stop_after_attempt, wait_exponential

from bot.core.config import config
from services.claude_service.cache import AsyncTTLCache
from services.claude_service.templates import PROMPT_TEMPLATES
from services.claude_service.templates import get_system_prompt

logger = logging.getLogger(__name__)


class ClaudeAPIError(Exception):
    """Базовый класс для ошибок Claude API"""

    pass


@dataclass
class RequestBatch:
    """Пакет запросов к API."""

    requests: List[Dict[str, Any]]
    max_tokens: int
    temperature: float
    created_at: datetime


@dataclass
class ClaudeResponse:
    """Класс для хранения ответов от Claude"""

    content: str
    timestamp: datetime
    # ... другие поля ...


class RateLimiter:
    """Ограничитель скорости запросов."""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = deque(maxlen=requests_per_minute)
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Получение разрешения на запрос."""
        async with self.lock:
            now = datetime.now()
            # Удаляем старые запросы
            while self.requests and (now - self.requests[0]) > timedelta(minutes=1):
                self.requests.popleft()

            if len(self.requests) >= self.requests_per_minute:
                # Ждем, пока не освободится слот
                wait_time = 60 - (now - self.requests[0]).total_seconds()
                if wait_time > 0:
                    await asyncio.sleep(wait_time)

            self.requests.append(now)


class SemanticCache:
    """Семантическое кэширование запросов."""

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self.cache: Dict[str, Tuple[str, datetime]] = {}
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.embeddings: Dict[str, np.ndarray] = {}

    def _get_embedding(self, text: str) -> np.ndarray:
        """Получение эмбеддинга текста."""
        if text not in self.embeddings:
            self.embeddings[text] = self.model.encode(text)
        return self.embeddings[text]

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Расчет косинусного сходства между текстами."""
        emb1 = self._get_embedding(text1)
        emb2 = self._get_embedding(text2)
        return cosine_similarity([emb1], [emb2])[0][0]

    def get(self, query: str) -> Optional[str]:
        """Получение кэшированного ответа."""
        for cached_query, (response, timestamp) in self.cache.items():
            if (
                self._calculate_similarity(query, cached_query)
                >= self.similarity_threshold
            ):
                return response
        return None

    def set(self, query: str, response: str) -> None:
        """Сохранение ответа в кэш."""
        self.cache[query] = (response, datetime.now())


class TokenOptimizer:
    """Оптимизация использования токенов."""

    @staticmethod
    def optimize_prompt(prompt: str, context: Dict[str, Any]) -> str:
        """Оптимизация промпта."""
        # Удаляем неиспользуемые поля из контекста
        optimized_context = {k: v for k, v in context.items() if k in prompt}

        # Сокращаем длинные тексты
        for k, v in optimized_context.items():
            if isinstance(v, str) and len(v) > 500:
                optimized_context[k] = v[:500] + "..."

        return prompt.format(**optimized_context)

    @staticmethod
    def reuse_previous_response(
        current_prompt: str, previous_response: str, similarity_threshold: float = 0.7
    ) -> Optional[str]:
        """Повторное использование частей предыдущего ответа."""
        # TODO: Реализовать логику повторного использования
        return None


class ClaudeService:
    """Сервис для работы с Claude API."""

    def __init__(self, api_key=None):
        """Инициализация сервиса Claude."""
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = AsyncAnthropic(api_key=self.api_key)
        self.rate_limiter = RateLimiter(requests_per_minute=60)
        self.semantic_cache = SemanticCache()
        self.token_optimizer = TokenOptimizer()
        self.batch_size = 5
        self.request_queue: List[RequestBatch] = []
        self.processing = False
        self._model = "claude-3-sonnet-20240229"
        self.cache = AsyncTTLCache()
        self.api_calls = 0
        self.last_reset = datetime.utcnow()
        self.cost_tracker = {
            "total": 0.0,
            "daily": 0.0,
            "last_reset": datetime.utcnow(),
        }
        self.model = "claude-3-opus-20240229"

    async def init_job_queue(self):
        """Асинхронная инициализация job_queue"""
        if hasattr(self.client, "job_queue"):

            async def init_wrapper():
                await self.init_repositories()

            await self.client.job_queue.run_once(init_wrapper, when=1)

    async def _make_request(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        cache_key: Optional[str] = None,
    ) -> str:
        """
        Базовый метод для отправки запросов к Claude API с кэшированием,
        отслеживанием расходов и повторными попытками
        """
        # Проверка лимитов
        await self._check_rate_limits()

        # Проверка кэша
        if cache_key and (cached := await self.cache.get(cache_key)):
            logger.debug(f"Cache hit for key: {cache_key}")
            return cached

        try:
            response = await self.client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.content[0].text

            # Кэширование результата
            if cache_key:
                await self.cache.set(cache_key, content)

            # Обновление статистики
            self._update_usage_stats(response)

            return content

        except Exception as e:
            logger.error(f"Error making Claude API request: {e}")
            raise ClaudeAPIError(f"Failed to get response from Claude: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
    )
    async def generate_investigation_step(
        self, context: Dict[str, Any], action: str
    ) -> str:
        """
        Генерирует следующий шаг расследования на основе контекста и действия игрока.

        Args:
            context: Контекст расследования
            action: Действие игрока

        Returns:
            str: Сгенерированный ответ
        """
        prompt = self._create_investigation_prompt(context, action)

        try:
            response = await self.client.messages.create(
                model=self._model,
                max_tokens=1000,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}],
            )

            self._logger.info(f"Получен ответ от Claude для действия '{action}'")

            return response.content[0].text

        except Exception as e:
            self._logger.error(f"Ошибка при генерации шага расследования: {e}")
            raise

    def _create_investigation_prompt(self, context: Dict[str, Any], action: str) -> str:
        """
        Создает структурированный промпт для генерации шага расследования.

        Args:
            context: Контекст расследования
            action: Действие игрока

        Returns:
            str: Сформированный промпт
        """
        # Формируем описание текущего состояния
        state_description = self._format_investigation_state(context)

        # Формируем описание действия игрока
        action_description = self._format_player_action(action)

        # Формируем описание навыков и ограничений
        skills_description = self._format_player_skills(context)

        # Собираем промпт
        prompt = f"""
        Ты - система генерации шагов расследования для детективной игры.
        
        Текущее состояние расследования:
        {state_description}
        
        Действие игрока:
        {action_description}
        
        Навыки и ограничения игрока:
        {skills_description}
        
        Сгенерируй ответ на действие игрока, учитывая:
        1. Логическую последовательность событий
        2. Навыки и ограничения игрока
        3. Реалистичность и детализацию
        4. Возможные последствия действий
        
        Ответ должен быть в формате JSON:
        {{
            "description": "подробное описание результата действия",
            "new_evidence": ["новые улики"],
            "new_clues": ["новые подсказки"],
            "consequences": ["последствия действия"],
            "next_actions": ["возможные следующие действия"]
        }}
        """

        return prompt

    def _format_investigation_state(self, context: Dict[str, Any]) -> str:
        """
        Форматирует текущее состояние расследования.

        Args:
            context: Контекст расследования

        Returns:
            str: Отформатированное описание состояния
        """
        state = []

        # Основная информация
        state.append(f"Название дела: {context.get('title', 'Неизвестно')}")
        state.append(f"Текущая локация: {context.get('location', 'Неизвестно')}")
        state.append(f"Сложность: {context.get('difficulty', 'Неизвестно')}")

        # Собранные улики
        if "evidence" in context:
            state.append("\nСобранные улики:")
            for evidence in context["evidence"]:
                state.append(f"- {evidence}")

        # Подозреваемые
        if "suspects" in context:
            state.append("\nПодозреваемые:")
            for suspect in context["suspects"]:
                state.append(f"- {suspect}")

        # Прогресс
        if "progress" in context:
            state.append("\nПрогресс расследования:")
            for key, value in context["progress"].items():
                state.append(f"- {key}: {value}")

        return "\n".join(state)

    def _format_player_action(self, action: str) -> str:
        """
        Форматирует описание действия игрока.

        Args:
            action: Действие игрока

        Returns:
            str: Отформатированное описание действия
        """
        return f"Игрок выполняет действие: {action}"

    def _format_player_skills(self, context: Dict[str, Any]) -> str:
        """
        Форматирует описание навыков и ограничений игрока.

        Args:
            context: Контекст расследования

        Returns:
            str: Отформатированное описание навыков
        """
        skills = []

        # Базовые навыки
        if "skills" in context:
            skills.append("Навыки игрока:")
            for skill, level in context["skills"].items():
                skills.append(f"- {skill}: {level}")

        # Временные бонусы
        if "temporary_bonuses" in context:
            skills.append("\nВременные бонусы:")
            for bonus in context["temporary_bonuses"]:
                skills.append(f"- {bonus}")

        # Ограничения
        if "restrictions" in context:
            skills.append("\nОграничения:")
            for restriction in context["restrictions"]:
                skills.append(f"- {restriction}")

        return "\n".join(skills)

    async def generate_profile(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Генерирует психологический профиль на основе контекста.

        Args:
            context: Контекст для генерации профиля

        Returns:
            Dict[str, Any]: Сгенерированный профиль
        """
        prompt = self._create_profile_prompt(context)

        try:
            response = await self.client.messages.create(
                model=self._model,
                max_tokens=1000,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}],
            )

            self._logger.info("Получен ответ от Claude для генерации профиля")

            return json.loads(response.content[0].text)

        except Exception as e:
            self._logger.error(f"Ошибка при генерации профиля: {e}")
            raise

    def _create_profile_prompt(self, context: Dict[str, Any]) -> str:
        """
        Создает промпт для генерации психологического профиля.

        Args:
            context: Контекст для генерации профиля

        Returns:
            str: Сформированный промпт
        """
        return f"""
        Сгенерируй психологический профиль на основе следующего контекста:
        {json.dumps(context, ensure_ascii=False, indent=2)}
        
        Ответ должен быть в формате JSON:
        {{
            "personality_traits": ["черты характера"],
            "behavior_patterns": ["паттерны поведения"],
            "motivations": ["возможные мотивы"],
            "risk_factors": ["факторы риска"],
            "recommendations": ["рекомендации по взаимодействию"]
        }}
        """

    async def generate_news(
        self,
        count: int = 1,
        context: Optional[Dict[str, Any]] = None,
        category: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Генерирует новости с помощью Claude API.

        Args:
            count: Количество новостей для генерации
            context: Контекст для генерации
            category: Категория новостей
            prompt: Пользовательский промпт

        Returns:
            List[Dict[str, Any]]: Список сгенерированных новостей
        """
        if not prompt:
            prompt = self._create_news_prompt(count, context, category)

        try:
            response = await self.client.messages.create(
                model=self._model,
                max_tokens=1000,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}],
            )

            self._logger.info(f"Получен ответ от Claude для генерации {count} новостей")

            return json.loads(response.content[0].text)

        except Exception as e:
            self._logger.error(f"Ошибка при генерации новостей: {e}")
            raise

    def _create_news_prompt(
        self,
        count: int,
        context: Optional[Dict[str, Any]] = None,
        category: Optional[str] = None,
    ) -> str:
        """
        Создает промпт для генерации новостей.

        Args:
            count: Количество новостей
            context: Контекст для генерации
            category: Категория новостей

        Returns:
            str: Сформированный промпт
        """
        prompt = f"Сгенерируй {count} новостей"

        if category:
            prompt += f" в категории '{category}'"

        if context:
            prompt += f" с учетом следующего контекста:\n{json.dumps(context, ensure_ascii=False, indent=2)}"

        prompt += """
        
        Ответ должен быть в формате JSON:
        [
            {
                "title": "заголовок новости",
                "content": "содержание новости",
                "category": "категория",
                "tags": ["теги"],
                "metadata": {
                    "relevance": "релевантность",
                    "impact": "влияние на игровой процесс"
                }
            }
        ]
        """

        return prompt

    async def _check_rate_limits(self) -> None:
        """Проверяет лимиты API и при необходимости ожидает"""
        now = datetime.utcnow()

        # Сброс счетчиков при необходимости
        if (now - self.last_reset) > timedelta(minutes=1):
            self.api_calls = 0
            self.last_reset = now

        if self.api_calls >= config.CLAUDE_RATE_LIMIT:
            wait_time = 60 - (now - self.last_reset).seconds
            logger.warning(f"Rate limit reached, waiting {wait_time} seconds")
            await asyncio.sleep(wait_time)
            self.api_calls = 0
            self.last_reset = datetime.utcnow()

        self.api_calls += 1

    def _update_usage_stats(self, response: anthropic.types.Message) -> None:
        """Обновляет статистику использования API"""
        # Примерная стоимость за 1K токенов
        cost_per_1k = config.CLAUDE_COST_PER_1K_TOKENS
        tokens_used = len(response.content[0].text.split()) / 0.75  # примерная оценка
        cost = (tokens_used / 1000) * cost_per_1k

        self.cost_tracker["total"] += cost
        self.cost_tracker["daily"] += cost

        # Сброс дневной статистики
        now = datetime.utcnow()
        if (now - self.cost_tracker["last_reset"]).days > 0:
            self.cost_tracker["daily"] = cost
            self.cost_tracker["last_reset"] = now

        if self.cost_tracker["daily"] > config.CLAUDE_DAILY_BUDGET:
            logger.warning("Daily budget exceeded!")

    def _create_prompt(self, template: str, context: Dict[str, Any]) -> str:
        """
        Создает промпт на основе шаблона и контекста.

        Args:
            template: Шаблон промпта с плейсхолдерами
            context: Словарь с данными для подстановки

        Returns:
            str: Готовый промпт

        Raises:
            ValueError: Если в контексте отсутствуют необходимые данные
        """
        try:
            # Проверяем наличие всех необходимых ключей в контексте
            required_keys = [
                key[1]
                for key in string.Formatter().parse(template)
                if key[1] is not None
            ]
            missing_keys = [key for key in required_keys if key not in context]

            if missing_keys:
                raise ValueError(f"Missing required keys in context: {missing_keys}")

            return template.format(**context)
        except Exception as e:
            logger.error(f"Error creating prompt: {e}")
            raise ValueError(f"Failed to create prompt: {e}")

    def _handle_api_error(self, error: Exception) -> None:
        """
        Обрабатывает ошибки API и логирует их.

        Args:
            error: Исключение, возникшее при работе с API

        Raises:
            ClaudeAPIError: Если ошибка связана с API
        """
        if isinstance(error, anthropic.RateLimitError):
            logger.warning("Rate limit exceeded. Waiting before retry...")
            raise ClaudeAPIError("Rate limit exceeded")
        elif isinstance(error, anthropic.AuthenticationError):
            logger.error("Authentication failed. Check API key.")
            raise ClaudeAPIError("Invalid API key")
        elif isinstance(error, anthropic.APIError):
            logger.error(f"Claude API error: {error}")
            raise ClaudeAPIError(f"API error: {error}")
        else:
            logger.error(f"Unexpected error: {error}")
            raise ClaudeAPIError(f"Unexpected error: {error}")

    async def generate_story(self, title: str, difficulty: int) -> Dict[str, Any]:
        """Генерирует новую детективную историю"""
        prompt = PROMPT_TEMPLATES["story_generation"].format(
            title=title, difficulty=difficulty
        )

        response = await self._make_request(
            prompt,
            max_tokens=2000,
            temperature=0.8,
            cache_key=f"story_{title}_{difficulty}",
        )

        return json.loads(response)

    def get_usage_stats(self) -> Dict[str, Any]:
        """Возвращает статистику использования API"""
        return {
            "total_cost": self.cost_tracker["total"],
            "daily_cost": self.cost_tracker["daily"],
            "api_calls_minute": self.api_calls,
            "last_reset": self.last_reset.isoformat(),
            "daily_budget_remaining": config.CLAUDE_DAILY_BUDGET
            - self.cost_tracker["daily"],
        }

    async def process_batch(self) -> None:
        """Обработка пакета запросов."""
        if not self.request_queue or self.processing:
            return

        self.processing = True
        try:
            batch = self.request_queue.pop(0)

            # Группируем запросы по токенам
            grouped_requests = self._group_requests_by_tokens(batch.requests)

            for group in grouped_requests:
                await self.rate_limiter.acquire()

                # Отправляем запросы пакетом
                responses = await self.client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=batch.max_tokens,
                    temperature=batch.temperature,
                    messages=group,
                )

                # Обрабатываем ответы
                for response in responses:
                    await self._handle_response(response)

        finally:
            self.processing = False

    def _group_requests_by_tokens(
        self, requests: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """Группировка запросов по токенам."""
        groups = []
        current_group = []
        current_tokens = 0

        for request in requests:
            estimated_tokens = self._estimate_tokens(request)
            if current_tokens + estimated_tokens > 8000:  # Максимальный контекст
                groups.append(current_group)
                current_group = []
                current_tokens = 0

            current_group.append(request)
            current_tokens += estimated_tokens

        if current_group:
            groups.append(current_group)

        return groups

    def _estimate_tokens(self, request: Dict[str, Any]) -> int:
        """Оценка количества токенов в запросе."""
        # Простая оценка: ~4 токена на слово
        text = str(request)
        return len(text.split()) * 4

    async def _handle_response(self, response: Any) -> None:
        """Обработка ответа от API."""
        # TODO: Реализовать обработку ответа
        pass

    async def generate_investigation_step(
        self, context: Dict[str, Any], action: str
    ) -> str:
        """
        Генерирует следующий шаг расследования.

        Args:
            context: Контекст расследования
            action: Действие игрока

        Returns:
            str: Сгенерированный ответ
        """
        # Проверяем семантический кэш
        query = self._create_investigation_prompt(context, action)
        cached_response = self.semantic_cache.get(query)
        if cached_response:
            return cached_response

        # Оптимизируем промпт
        optimized_prompt = self.token_optimizer.optimize_prompt(
            self._get_investigation_prompt_template(), context
        )

        # Добавляем запрос в очередь
        self.request_queue.append(
            RequestBatch(
                requests=[{"role": "user", "content": optimized_prompt}],
                max_tokens=1000,
                temperature=0.7,
                created_at=datetime.now(),
            )
        )

        # Запускаем обработку пакета
        await self.process_batch()

        # TODO: Получить и вернуть ответ
        return ""

    @lru_cache(maxsize=10)
    def _get_investigation_prompt_template(self) -> str:
        """Получение шаблона промпта для расследования."""
        return """
        Текущее состояние расследования:
        {current_state}
        
        Действие игрока: {action}
        
        Навыки игрока:
        - Детектив: {detective_skill}
        - Криминалистика: {forensic_skill}
        - Психология: {psychology_skill}
        
        Собранные улики: {evidence}
        
        Допрошенные подозреваемые: {suspects}
        
        Сгенерируй ответ на действие игрока, учитывая его навыки и текущее состояние расследования.
        """

    async def generate_psychological_profile(self, suspect_data: Dict[str, Any]) -> str:
        """
        Генерирует психологический профиль подозреваемого.

        Args:
            suspect_data: Данные подозреваемого

        Returns:
            str: Сгенерированный профиль
        """
        # Проверяем семантический кэш
        query = self._create_profile_prompt(suspect_data)
        cached_response = self.semantic_cache.get(query)
        if cached_response:
            return cached_response

        # Оптимизируем промпт
        optimized_prompt = self.token_optimizer.optimize_prompt(
            self._get_profile_prompt_template(), suspect_data
        )

        # Добавляем запрос в очередь
        self.request_queue.append(
            RequestBatch(
                requests=[{"role": "user", "content": optimized_prompt}],
                max_tokens=800,
                temperature=0.7,
                created_at=datetime.now(),
            )
        )

        # Запускаем обработку пакета
        await self.process_batch()

        # TODO: Получить и вернуть ответ
        return ""

    def _create_profile_prompt(self, suspect_data: Dict[str, Any]) -> str:
        """Создание промпта для профиля."""
        template = self._get_profile_prompt_template()
        return template.format(**suspect_data)

    @lru_cache(maxsize=10)
    def _get_profile_prompt_template(self) -> str:
        """Получение шаблона промпта для профиля."""
        return """
        Анализ личности подозреваемого:
        
        Имя: {name}
        Возраст: {age}
        Профессия: {occupation}
        
        Известная информация:
        {known_info}
        
        Поведение:
        {behavior}
        
        Сгенерируй психологический профиль подозреваемого, включая:
        1. Основные черты характера
        2. Мотивацию
        3. Возможные психологические проблемы
        4. Рекомендации по допросу
        """

    async def generate_news(
        self,
        count: int = 1,
        context: Optional[Dict[str, Any]] = None,
        category: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Генерирует новости.

        Args:
            count: Количество новостей
            context: Контекст для генерации
            category: Категория новостей
            prompt: Пользовательский промпт

        Returns:
            List[Dict[str, Any]]: Сгенерированные новости
        """
        # Проверяем семантический кэш
        query = self._create_news_prompt(count, context, category, prompt)
        cached_response = self.semantic_cache.get(query)
        if cached_response:
            return json.loads(cached_response)

        # Оптимизируем промпт
        optimized_prompt = self.token_optimizer.optimize_prompt(
            prompt or self._get_news_prompt_template(category), context or {}
        )

        # Добавляем запрос в очередь
        self.request_queue.append(
            RequestBatch(
                requests=[{"role": "user", "content": optimized_prompt}],
                max_tokens=1000,
                temperature=0.8,
                created_at=datetime.now(),
            )
        )

        # Запускаем обработку пакета
        await self.process_batch()

        # TODO: Получить и вернуть ответ
        return []

    def _create_news_prompt(
        self,
        count: int,
        context: Optional[Dict[str, Any]],
        category: Optional[str],
        prompt: Optional[str],
    ) -> str:
        """Создание промпта для новостей."""
        if prompt:
            return prompt.format(**(context or {}))

        template = self._get_news_prompt_template(category)
        return template.format(count=count, **(context or {}))

    @lru_cache(maxsize=10)
    def _get_news_prompt_template(self, category: Optional[str] = None) -> str:
        """Получение шаблона промпта для новостей."""
        if category == "crime":
            return """
            Сгенерируй {count} новостей о преступлениях в формате JSON:
            [
                {{
                    "title": "Заголовок",
                    "content": "Содержание",
                    "category": "crime",
                    "tags": ["теги"],
                    "metadata": {{
                        "location": "место",
                        "severity": "уровень",
                        "hints": ["подсказки"]
                    }}
                }}
            ]
            """
        else:
            return """
            Сгенерируй {count} новостей в формате JSON:
            [
                {{
                    "title": "Заголовок",
                    "content": "Содержание",
                    "category": "general",
                    "tags": ["теги"]
                }}
            ]
            """

    async def get_embedding(self, text: str) -> List[float]:
        """Получает embedding для текста"""
        try:
            response = await self.client.embeddings.create(model=self.model, input=text)
            return response.embeddings[0]
        except Exception as e:
            logger.error(f"Ошибка при получении embedding: {e}")
            return []

    def calculate_similarity_score(
        self, embedding1: List[float], embedding2: List[float]
    ) -> float:
        """Вычисляет score схожести между двумя embedding"""
        if not embedding1 or not embedding2:
            return 0.0
        try:
            # Используем косинусное сходство
            similarity_score = np.dot(embedding1, embedding2) / (
                np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
            )
            return float(similarity_score)
        except Exception as e:
            logger.error(f"Ошибка при вычислении similarity score: {e}")
            return 0.0

    async def check_similarity(
        self, current_prompt, previous_response, similarity_threshold=0.85
    ):
        """Проверяет схожесть текущего промпта с предыдущим ответом"""
        current_embedding = await self.get_embedding(current_prompt)
        previous_embedding = await self.get_embedding(previous_response)
        similarity_score = self.calculate_similarity_score(
            current_embedding, previous_embedding
        )
        return similarity_score > similarity_threshold

    async def create_completion(self, prompt, system_prompt=None, temperature=0.7):
        """Создает завершение с помощью API Claude"""
        try:
            # ... existing code ...
            timestamp = datetime.now(timezone.utc)
            # ... existing code ...

            response = self.client.messages.create(
                model="claude-3-opus-20240229",
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=4096,
            )

            # ... existing code ...
            return response.content
        except anthropic.APIError as e:
            logging.error(f"Claude API error: {str(e)}")
        except anthropic.APIConnectionError as e:
            logging.error(f"Connection error: {str(e)}")
        except anthropic.RateLimitError as e:
            logging.error(f"Rate limit error: {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error in Claude API: {str(e)}")

        return "Извините, я не смог обработать ваш запрос."
