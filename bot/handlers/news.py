"""Обработчики команд новостей"""

import logging
from typing import List

from telegram import Update
from telegram.ext import ContextTypes, Application, CommandHandler, ConversationHandler

from bot.utils.formatters import format_news
from bot.database.repositories.news_repository import NewsRepository
from bot.handlers.states import States
from bot.database.db import SessionLocal

logger = logging.getLogger(__name__)

# Глобальные переменные для репозиториев
news_repository = None


async def init_repository(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Инициализация репозитория."""
    session = SessionLocal()
    context.bot_data["news_repository"] = NewsRepository(session)


async def read_news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает последние новости"""
    try:
        if news_repository is None:
            await init_repository(context)

        news = await news_repository.get_latest_news()
        if not news:
            await update.message.reply_text("Новостей пока нет")
            return

        for item in news:
            await update.message.reply_text(
                format_news(item),
                parse_mode="Markdown",
            )

    except Exception as e:
        logger.error(f"Ошибка при показе новостей: {e}")
        await update.message.reply_text("Произошла ошибка при получении новостей")


async def show_city_map(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает карту города"""
    try:
        if news_repository is None:
            await init_repository(context)

        map_data = await news_repository.get_city_map()
        if not map_data:
            await update.message.reply_text("Карта города недоступна")
            return

        description = map_data.get("description", "Описание карты недоступно")
        await update.message.reply_text(
            f"🗺️ *Карта города*\n\n{description}",
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error(f"Ошибка при показе карты города: {e}")
        await update.message.reply_text("Произошла ошибка при получении карты города")


# Создаем ConversationHandler для новостей
news_handler = ConversationHandler(
    entry_points=[CommandHandler("news", read_news)],
    states={
        States.VIEWING_NEWS: [
            CommandHandler("map", show_city_map),
        ],
    },
    fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
)


def register_news_handlers(application: Application) -> None:
    """
    Регистрирует обработчики новостей в приложении.

    Args:
        application: Экземпляр Application для регистрации обработчиков
    """
    # Инициализируем репозиторий при запуске
    application.job_queue.run_once(init_repository, 0)

    # Регистрируем обработчик новостей
    application.add_handler(news_handler)

    logger.info("News handlers registered successfully")


__all__ = ["read_news", "register_news_handlers"]
