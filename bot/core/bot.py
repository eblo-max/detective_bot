"""Основной класс бота."""

import logging
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    CallbackQueryHandler,
    filters,
)

from bot.core.config import BotConfig
from bot.core.callbacks import handle_callback
from bot.handlers import commands, investigation
from bot.handlers.profile import register_profile_handlers, handle_profile_callback
from bot.handlers.news import register_news_handlers, read_news
from bot.database.db import SessionLocal, init_db
from bot.database.repositories.user_repository import UserRepository
from bot.database.repositories.case_repository import CaseRepository
from bot.database.repositories.investigation_repository import InvestigationRepository
from bot.database.repositories.news_repository import NewsRepository
from services.claude_service import ClaudeService

logger = logging.getLogger(__name__)


# Инициализация репозиториев
async def get_repositories():
    """Получение репозиториев с сессией базы данных."""
    session = SessionLocal()
    return {
        "user_repository": UserRepository(session),
        "case_repository": CaseRepository(session),
        "investigation_repository": InvestigationRepository(session),
        "news_repository": NewsRepository(session),
        "session": session,  # Сохраняем сессию для последующего закрытия
    }


class DetectiveBot:
    """Класс детективного бота."""

    def __init__(self, config: BotConfig):
        """
        Инициализация бота.

        Args:
            config: Конфигурация бота
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.application: Optional[Application] = None
        self.repositories = None
        self._session = None

        # Инициализация сервисов
        self.claude_service = ClaudeService()

    async def start(self):
        """Запуск бота."""
        self.logger.info("Инициализация бота...")

        # Инициализация базы данных
        await init_db()

        # Создание приложения
        self.application = (
            Application.builder().token(self.config.TELEGRAM_TOKEN).build()
        )

        # Получаем репозитории
        repositories = await get_repositories()
        self._session = repositories.pop("session")
        self.repositories = repositories

        # Добавляем данные в bot_data
        self.application.bot_data.update(
            {
                "user_repository": UserRepository(self._session),
                "case_repository": CaseRepository(self._session),
                "investigation_repository": InvestigationRepository(self._session),
                "news_repository": NewsRepository(self._session),
                "claude_service": self.claude_service,
            }
        )

        # Регистрация обработчиков
        self._register_handlers()

        # Запуск бота
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        self.logger.info("Бот успешно запущен")

    async def run_polling(self):
        """Запуск бота в режиме polling."""
        if not self.application:
            raise RuntimeError("Бот не был инициализирован. Вызовите метод start()")

        self.logger.info("Запуск бота в режиме polling...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        await self.application.updater.idle()

    async def stop(self):
        """Остановка бота."""
        try:
            if self.application and self.application.running:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            await self.cleanup()
        except Exception as e:
            self.logger.error(f"Ошибка при остановке бота: {e}")

    async def cleanup(self):
        """Очистка ресурсов бота."""
        if self._session:
            await self._session.close()
            self._session = None

    def _register_handlers(self):
        # Регистрация обработчиков команд
        self.application.add_handler(CommandHandler("start", commands.start))
        self.application.add_handler(CommandHandler("help", commands.help_command))
        self.application.add_handler(CommandHandler("cases", commands.cases))
        self.application.add_handler(CommandHandler("analyze", commands.analyze))

        # Регистрация обработчиков сообщений
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, commands.handle_message)
        )

        # Регистрация обработчиков расследований
        self.application.add_handler(investigation.investigation_handler)

        # Регистрация обработчиков профиля и новостей
        register_profile_handlers(self.application)
        register_news_handlers(self.application)

        # Регистрация обработчика callback-запросов
        self.application.add_handler(CallbackQueryHandler(handle_callback))


async def handle_investigation_callback(
    update: Update, context: CallbackContext, parts: list
) -> None:
    """Обработка callback-запросов для расследований"""
    sub_action = parts[1] if len(parts) > 1 else None
    if not sub_action:
        return

    handlers = {
        "cancel": investigation.cancel_investigation,
        "location": lambda u, c: investigation.investigate_location(
            u, c, parts[2] if len(parts) > 2 else None
        ),
        "suspect": lambda u, c: investigation.interrogate_suspect(
            u, c, parts[2] if len(parts) > 2 else None
        ),
        "evidence": lambda u, c: investigation.examine_evidence(
            u, c, parts[2] if len(parts) > 2 else None
        ),
        "decide": lambda u, c: investigation.make_decision(
            u, c, parts[2] if len(parts) > 2 else None
        ),
    }

    handler = handlers.get(sub_action)
    if handler:
        await handler(update, context)


async def process_profile_callback(
    update: Update, context: CallbackContext, parts: list
) -> None:
    """Обработка callback-запросов для профиля"""
    sub_action = parts[1] if len(parts) > 1 else None
    if not sub_action:
        return

    if sub_action in ["skills", "inventory", "achievements"]:
        await handle_profile_callback(update, context)


async def handle_news_callback(
    update: Update, context: CallbackContext, parts: list
) -> None:
    """Обработка callback-запросов для новостей"""
    news_id = parts[1] if len(parts) > 1 else None
    if news_id:
        await read_news(update, context, news_id)


async def handle_callback(update: Update, context: CallbackContext):
    """
    Обрабатывает все callback-запросы от inline кнопок
    """
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id

    # Разделяем callback data для определения действия
    parts = data.split(":")
    action = parts[0]

    # Подтверждаем получение callback запроса
    await query.answer()

    # Обработка различных типов callback-запросов
    handlers = {
        "investigation": handle_investigation_callback,
        "profile": process_profile_callback,
        "news": handle_news_callback,
    }

    handler = handlers.get(action)
    if handler:
        await handler(update, context, parts)

    # Обновляем состояние бота для пользователя
    await context.bot.send_chat_action(chat_id=user_id, action="typing")
