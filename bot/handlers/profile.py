"""Обработчики команд профиля"""

import logging
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes, Application, CommandHandler, ConversationHandler

from bot.keyboards.profile_keyboard import create_profile_keyboard
from bot.utils.formatters import format_profile
from bot.database.repositories.user_repository import UserRepository
from bot.handlers.states import States
from bot.database.db import SessionLocal
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

# Глобальные переменные для репозиториев
user_repository = None


async def init_repository(context: CallbackContext) -> None:
    """Инициализация репозитория."""
    session = SessionLocal()
    context.bot_data["user_repository"] = UserRepository(session)


async def show_profile(update: Update, context: CallbackContext) -> None:
    """Показывает профиль пользователя"""
    try:
        user = update.effective_user
        profile = await context.bot_data["user_repository"].get_user_by_telegram_id(
            user.id
        )

        if not profile:
            await update.message.reply_text(
                "Профиль не найден. Используйте /start для регистрации.",
                reply_markup=await create_profile_keyboard(),
            )
            return

        await update.message.reply_text(
            await format_profile(profile), reply_markup=await create_profile_keyboard()
        )

    except Exception as e:
        logger.error(f"Ошибка при показе профиля: {e}")
        await update.message.reply_text("Произошла ошибка при получении профиля")


async def show_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает достижения пользователя"""
    try:
        if user_repository is None:
            await init_repository()

        user = await user_repository.get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text("Профиль не найден")
            return

        achievements = await user_repository.get_user_achievements(user.id)
        if not achievements:
            await update.message.reply_text("У вас пока нет достижений")
            return

        achievements_text = "🏆 *Ваши достижения:*\n\n"
        for achievement in achievements:
            title = achievement.get("title", "Без названия")
            description = achievement.get("description", "Описание отсутствует")
            achievements_text += f"• {title}\n"
            achievements_text += f"  {description}\n\n"

        await update.message.reply_text(
            achievements_text,
            parse_mode="Markdown",
            reply_markup=create_profile_keyboard(),
        )

    except Exception as e:
        logger.error(f"Ошибка при показе достижений: {e}")
        await update.message.reply_text("Произошла ошибка при получении достижений")


async def show_skills(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает навыки пользователя"""
    try:
        if user_repository is None:
            await init_repository()

        user = await user_repository.get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text("Профиль не найден")
            return

        skills = await user_repository.get_user_skills(user.id)
        if not skills:
            await update.message.reply_text("У вас пока нет навыков")
            return

        skills_text = "🎯 *Ваши навыки:*\n\n"
        for skill in skills:
            name = skill.get("name", "Без названия")
            level = skill.get("level", 0)
            description = skill.get("description", "Описание отсутствует")
            skills_text += f"• {name} (Уровень {level})\n"
            skills_text += f"  {description}\n\n"

        await update.message.reply_text(
            skills_text,
            parse_mode="Markdown",
            reply_markup=create_profile_keyboard(),
        )

    except Exception as e:
        logger.error(f"Ошибка при показе навыков: {e}")
        await update.message.reply_text("Произошла ошибка при получении навыков")


async def handle_profile_callback(update: Update, context: CallbackContext) -> None:
    """Обрабатывает callback-запросы профиля"""
    query = update.callback_query
    await query.answer()

    if query.data == "profile_skills":
        await show_skills(update, context)
    elif query.data == "profile_achievements":
        await show_achievements(update, context)
    else:
        await show_profile(update, context)


# Создаем ConversationHandler для профиля
profile_handler = ConversationHandler(
    entry_points=[CommandHandler("profile", show_profile)],
    states={
        States.VIEWING_PROFILE: [
            CommandHandler("achievements", show_achievements),
            CommandHandler("skills", show_skills),
        ],
    },
    fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
)


def register_profile_handlers(application: Application) -> None:
    """
    Регистрирует обработчики профиля в приложении.

    Args:
        application: Экземпляр Application для регистрации обработчиков
    """
    # Инициализируем репозиторий при запуске
    application.job_queue.run_once(init_repository, 0)

    # Регистрируем обработчик профиля
    application.add_handler(profile_handler)

    logger.info("Profile handlers registered successfully")
