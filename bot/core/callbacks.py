"""Обработка callback-запросов."""

import logging
from typing import Any

from telegram import Update
from telegram.ext import CallbackContext
from bot.keyboards.case_keyboard import create_case_actions_keyboard
from bot.handlers.investigation import (
    show_investigation_status,
    examine_evidence,
    interrogate_suspect,
    solve_investigation,
)
from bot.handlers.news import read_news

logger = logging.getLogger(__name__)


async def handle_callback(update: Update, context: CallbackContext) -> None:
    """
    Обработчик callback-запросов.

    Args:
        update: Объект обновления
        context: Контекст callback
    """
    try:
        query = update.callback_query
        if not query:
            return

        await query.answer()

        # Получаем данные из callback
        data = query.data
        if not data:
            return

        # Обрабатываем callback в зависимости от типа
        if data.startswith("case_"):
            await handle_case_callback(query, context)
        elif data.startswith("investigation_"):
            await handle_investigation_callback(query, context)
        elif data.startswith("news_"):
            await handle_news_callback(query, context)
        else:
            logger.warning(f"Unknown callback type: {data}")

    except Exception as e:
        logger.error(f"Error handling callback: {e}")


async def handle_case_callback(query: Any, context: CallbackContext) -> None:
    """Обработка callback-запросов, связанных с делами."""
    try:
        # Получаем данные из callback
        data = query.data
        parts = data.split("_")

        if len(parts) < 2:
            await query.message.edit_text("❌ Некорректный формат callback-данных")
            return

        case_id = parts[1]
        case_repository = context.bot_data.get("case_repository")

        if not case_repository:
            await query.message.edit_text(
                "❌ Ошибка: репозиторий дел не инициализирован"
            )
            return

        case = await case_repository.get_case_by_id(case_id)
        if not case:
            await query.message.edit_text("❌ Дело не найдено")
            return

        # Формируем текст с информацией о деле
        case_text = (
            f"📁 *Дело №{case.id}*\n\n"
            f"Название: {case.title}\n"
            f"Статус: {case.status}\n"
            f"Сложность: {'⭐' * case.difficulty}\n\n"
            f"Описание: {case.description}\n\n"
            "Выберите действие:"
        )

        # Отправляем информацию о деле
        await query.message.edit_text(
            case_text,
            parse_mode="Markdown",
            reply_markup=await create_case_actions_keyboard(case),
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке callback дела: {e}")
        await query.message.edit_text("❌ Произошла ошибка при обработке запроса")


async def handle_investigation_callback(query: Any, context: CallbackContext) -> None:
    """Обработка callback-запросов, связанных с расследованиями."""
    try:
        # Получаем данные из callback
        data = query.data
        parts = data.split("_")

        if len(parts) < 2:
            await query.message.edit_text("❌ Некорректный формат callback-данных")
            return

        action = parts[1]
        investigation_repository = context.bot_data.get("investigation_repository")

        if not investigation_repository:
            await query.message.edit_text(
                "❌ Ошибка: репозиторий расследований не инициализирован"
            )
            return

        # Обрабатываем различные действия расследования
        if action == "start":
            # Начало нового расследования
            investigation = await investigation_repository.create_investigation(
                user_id=query.from_user.id, case_id=parts[2] if len(parts) > 2 else None
            )
            await show_investigation_status(query, investigation)

        elif action == "examine":
            # Осмотр места/улики
            evidence_id = parts[2] if len(parts) > 2 else None
            await examine_evidence(query, context, evidence_id)

        elif action == "interrogate":
            # Допрос подозреваемого
            suspect_id = parts[2] if len(parts) > 2 else None
            await interrogate_suspect(query, context, suspect_id)

        elif action == "solve":
            # Завершение расследования
            investigation_id = parts[2] if len(parts) > 2 else None
            await solve_investigation(query, context, investigation_id)

        else:
            await query.message.edit_text("❌ Неизвестное действие расследования")

    except Exception as e:
        logger.error(f"Ошибка при обработке callback расследования: {e}")
        await query.message.edit_text("❌ Произошла ошибка при обработке запроса")


async def handle_news_callback(query: Any, context: CallbackContext) -> None:
    """Обработка callback-запросов, связанных с новостями."""
    try:
        # Получаем данные из callback
        data = query.data
        parts = data.split("_")

        if len(parts) < 2:
            await query.message.edit_text("❌ Некорректный формат callback-данных")
            return

        news_id = parts[1]
        await read_news(query, context, news_id)

    except Exception as e:
        logger.error(f"Ошибка при обработке новостного callback: {e}")
        await query.message.edit_text("❌ Произошла ошибка при обработке запроса")
