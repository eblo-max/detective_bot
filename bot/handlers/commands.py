"""Обработчики команд бота."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.keyboards.common_keyboard import create_main_menu_keyboard
from bot.keyboards.investigation import (
    InvestigationKeyboards,
    create_investigation_keyboard,
)
from bot.keyboards.profile_keyboard import create_profile_keyboard
from bot.utils.formatters import format_message, format_profile
from bot.core.config import config
from bot.database.repositories.case_repository import CaseRepository
from bot.database.repositories.investigation_repository import InvestigationRepository
from bot.database.repositories.news_repository import NewsRepository
from bot.database.repositories.user_repository import UserRepository
from game.player.achievements import check_achievements
from services.claude_service.claude_service import ClaudeService
from bot.database.db import get_db
from game.player.skills import SkillType
from game.investigation.case import Case, CaseStatus

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
ANALYZING, CONFIRMING = range(2)
(CHOOSING_CASE, ANALYZING_TEXT) = range(2)

# Создаем экземпляр клавиатуры расследований
investigation_keyboards = InvestigationKeyboards()

# Константы для сообщений
PROFILE_NOT_FOUND_MESSAGE = (
    "❌ Профиль не найден. Используйте /start для создания профиля."
)
BOT_INIT_ERROR_MESSAGE = (
    "❌ Произошла ошибка при инициализации бота.\n" + "Пожалуйста, попробуйте позже."
)
REPOSITORIES_NOT_INITIALIZED_MESSAGE = (
    "❌ Произошла ошибка при инициализации бота.\n" + "Пожалуйста, попробуйте позже."
)
NEWS_HEADER_MESSAGE = "📰 *Последние новости:*\n\n"
NO_NEWS_MESSAGE = "📰 В данный момент нет новых сообщений.\n" + "Попробуйте позже."
USER_NOT_FOUND_MESSAGE = (
    "❌ Пользователь не найден.\n" + "Используйте /start для регистрации."
)


# Инициализация репозиториев
async def get_repositories():
    """Получение репозиториев с сессией"""
    session = await get_db()
    return {
        "user_repository": UserRepository(session),
        "case_repository": CaseRepository(session),
        "investigation_repository": InvestigationRepository(session),
        "news_repository": NewsRepository(session),
    }


# Глобальные переменные для репозиториев
user_repository = None
case_repository = None
investigation_repository = None
news_repository = None


async def init_repositories(context=None):
    """Инициализация репозиториев"""
    global user_repository, case_repository, investigation_repository, news_repository
    repos = await get_repositories()
    user_repository = repos["user_repository"]
    case_repository = repos["case_repository"]
    investigation_repository = repos["investigation_repository"]
    news_repository = repos["news_repository"]


async def handle_analysis_confirmation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Обработчик подтверждения анализа.

    Args:
        update: Объект обновления
        context: Контекст

    Returns:
        int: Следующее состояние разговора
    """
    try:
        user = await user_repository.get_user_by_telegram_id(update.effective_user.id)
        if not user:
            await update.message.reply_text(USER_NOT_FOUND_MESSAGE)
            return ConversationHandler.END

        answer = update.message.text.lower()
        if answer == "да":
            # Получаем текст для анализа из контекста
            text_to_analyze = context.user_data.get("text_to_analyze")
            if not text_to_analyze:
                await update.message.reply_text(
                    "❌ Не найден текст для анализа. Попробуйте снова."
                )
                return ConversationHandler.END

            # Анализируем текст
            claude_service = ClaudeService()
            analysis_result = await claude_service.analyze_text(text_to_analyze)

            # Отправляем результат
            await update.message.reply_text(
                f"📝 *Результат анализа:*\n\n{analysis_result}",
                parse_mode="Markdown",
                reply_markup=await create_main_menu_keyboard(),
            )

            logger.info(f"User {user.id} confirmed text analysis")
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                "❌ Анализ отменен.",
                reply_markup=await create_main_menu_keyboard(),
            )
            return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error in handle_analysis_confirmation: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обработке подтверждения.\n"
            "Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END


async def handle_evidence_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Обработчик выбора улики.

    Args:
        update: Объект обновления
        context: Контекст
    """
    try:
        # Получаем ID улики из текста сообщения
        evidence_id = int(update.message.text.split("#")[1])

        # Получаем пользователя
        user = await user_repository.get_user_by_telegram_id(update.effective_user.id)
        if not user:
            await update.message.reply_text(USER_NOT_FOUND_MESSAGE)
            return

        # Получаем текущее расследование
        active_case = await case_repository.get_active_case(user.id)
        if not active_case:
            await update.message.reply_text(
                "❌ У вас нет активного расследования.\n"
                "Используйте /newcase для начала нового расследования."
            )
            return

        # Анализируем улику
        case = Case(active_case, investigation_repository, ClaudeService())
        result = await case.collect_evidence(evidence_id)

        # Отправляем результат
        await update.message.reply_text(
            result["description"],
            reply_markup=InvestigationKeyboards.create_evidence_menu(),
        )

        logger.info(f"User {user.id} analyzed evidence #{evidence_id}")

    except ValueError:
        await update.message.reply_text("❌ Неверный формат номера улики.")
    except Exception as e:
        logger.error(f"Error in handle_evidence_selection: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при анализе улики.\n", "Пожалуйста, попробуйте позже."
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /start.
    Приветствует пользователя и регистрирует его, если он новый.
    """
    try:
        user = update.effective_user
        user_repository = context.bot_data.get("user_repository")

        if not user_repository:
            logger.error("user_repository не инициализирован")
            await update.message.reply_text(REPOSITORIES_NOT_INITIALIZED_MESSAGE)
            return

        # Проверяем, существует ли пользователь
        db_user = await user_repository.get_user_by_telegram_id(user.id)
        if not db_user:
            # Создаем нового пользователя
            db_user = await user_repository.create_user(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
            )
            logger.info(f"Created new user: {db_user.id}")

        # Отправляем приветственное сообщение
        welcome_text = (
            f"👋 Привет, {user.first_name}!\n\n"
            "Я бот-детектив, который поможет тебе раскрывать загадочные дела. "
            "Используй команду /help, чтобы узнать, что я умею."
        )
        await update.message.reply_text(
            welcome_text,
            reply_markup=await create_main_menu_keyboard(),
        )

        logger.info(f"User {db_user.id} started the bot")

    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при запуске бота.\n", "Пожалуйста, попробуйте позже."
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /help.
    Показывает справку по доступным командам.
    """
    try:
        help_text = (
            "🔍 *Доступные команды:*\n\n"
            "/start - Начать работу с ботом\n"
            "/help - Показать это сообщение\n"
            "/profile - Просмотр профиля\n"
            "/cases - Список расследований\n"
            "/newcase - Начать новое расследование\n"
            "/news - Последние новости\n"
            "/analyze [текст] - Анализ текста\n\n"
            "Для начала расследования используйте /newcase"
        )

        await update.message.reply_text(
            help_text,
            parse_mode="Markdown",
            reply_markup=await create_main_menu_keyboard(),
        )

        logger.info(f"User {update.effective_user.id} requested help")

    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при показе справки.\n", "Пожалуйста, попробуйте позже."
        )


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /profile.
    Показывает профиль игрока с его статистикой и прогрессом.
    """
    try:
        user_repository = context.bot_data.get("user_repository")
        if not user_repository:
            logger.error("user_repository не инициализирован")
            await update.message.reply_text(REPOSITORIES_NOT_INITIALIZED_MESSAGE)
            return

        user = await user_repository.get_user_by_telegram_id(update.effective_user.id)
        if not user:
            await update.message.reply_text(USER_NOT_FOUND_MESSAGE)
            return

        profile_text = await format_profile(user)
        keyboard = await create_profile_keyboard()
        await update.message.reply_text(
            profile_text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

        logger.info(f"User {user.id} viewed their profile")

    except Exception as e:
        logger.error(f"Error in profile command: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при показе профиля.\n"
            + "Пожалуйста, попробуйте позже."
        )


async def cases_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /cases.
    Показывает список доступных и активных расследований.
    """
    try:
        user_repository = context.bot_data.get("user_repository")
        case_repository = context.bot_data.get("case_repository")

        if not user_repository or not case_repository:
            logger.error("Репозитории не инициализированы")
            await update.message.reply_text(REPOSITORIES_NOT_INITIALIZED_MESSAGE)
            return

        user = await user_repository.get_user_by_telegram_id(update.effective_user.id)
        if not user:
            await update.message.reply_text(USER_NOT_FOUND_MESSAGE)
            return

        # Получаем активные и доступные расследования
        active_cases = await case_repository.get_user_active_cases(user.id)
        available_cases = await case_repository.get_available_cases(user.id)

        cases_text = (
            "🔍 *Список расследований*\n\n"
            f"*Активные расследования:* {len(active_cases)}\n"
            f"*Доступные расследования:* {len(available_cases)}\n\n"
            "Выберите действие:"
        )

        keyboard = InvestigationKeyboards.create_main_menu()
        await update.message.reply_text(
            cases_text, parse_mode="Markdown", reply_markup=keyboard
        )

        logger.info(f"User {user.id} viewed cases list")

    except Exception as e:
        logger.error(f"Error in cases command: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при показе списка расследований.\n"
            + "Пожалуйста, попробуйте позже."
        )


async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /news.
    Показывает последние новости и события в игре.
    """
    try:
        user_repository = context.bot_data.get("user_repository")
        news_repository = context.bot_data.get("news_repository")

        if not user_repository or not news_repository:
            logger.error("Репозитории не инициализированы")
            await update.message.reply_text(REPOSITORIES_NOT_INITIALIZED_MESSAGE)
            return

        user = await user_repository.get_user_by_telegram_id(update.effective_user.id)
        if not user:
            await update.message.reply_text(USER_NOT_FOUND_MESSAGE)
            return

        latest_news = await news_repository.get_latest_news(limit=5)
        if not latest_news:
            await update.message.reply_text(NO_NEWS_MESSAGE)
            return

        news_text = NEWS_HEADER_MESSAGE
        for news in latest_news:
            news_text += f"*{news.title}*\n{news.content}\n\n"

        keyboard = await create_main_menu_keyboard()
        await update.message.reply_text(
            news_text, parse_mode="Markdown", reply_markup=keyboard
        )

        logger.info(f"User {user.id} viewed news")

    except Exception as e:
        logger.error(f"Error in news command: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при показе новостей.\n"
            + "Пожалуйста, попробуйте позже."
        )


async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обработчик команды /analyze.
    Анализирует предоставленный текст с помощью психологического профилирования.
    """
    try:
        if not context.args:
            await update.message.reply_text(
                "❌ Пожалуйста, укажите текст для анализа.\n"
                "Пример: /analyze Текст для анализа"
            )
            return ConversationHandler.END

        user_repository = context.bot_data.get("user_repository")
        claude_service = context.bot_data.get("claude_service")

        if not user_repository or not claude_service:
            logger.error("Сервисы не инициализированы")
            await update.message.reply_text(BOT_INIT_ERROR_MESSAGE)
            return ConversationHandler.END

        user = await user_repository.get_user_by_telegram_id(update.effective_user.id)
        if not user:
            await update.message.reply_text(USER_NOT_FOUND_MESSAGE)
            return ConversationHandler.END

        # Проверяем уровень навыка психологии
        if user.psychology_skill < 3:
            await update.message.reply_text(
                "❌ Ваш уровень навыка психологии слишком низкий для анализа.\n"
                "Повысьте уровень навыка для использования этой функции."
            )
            return ConversationHandler.END

        text = " ".join(context.args)

        # Получаем анализ от Claude
        analysis = await claude_service.analyze_text(
            text=text,
            context={
                "user_level": user.level,
                "psychology_skill": user.psychology_skill,
            },
        )

        await update.message.reply_text(
            f"🧠 *Анализ текста:*\n\n{analysis}",
            parse_mode="Markdown",
            reply_markup=await create_main_menu_keyboard(),
        )

        logger.info(f"User {user.id} analyzed text")
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error in analyze command: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при анализе текста.\n", "Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END


# Создаем ConversationHandler для команды analyze
analyze_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("analyze", analyze_command)],
    states={
        ANALYZING: [
            MessageHandler(filters.Regex(r"^Улика #\d+"), handle_evidence_selection)
        ],
        CONFIRMING: [
            MessageHandler(filters.Regex(r"^(да|нет)$"), handle_analysis_confirmation)
        ],
    },
    fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
)


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /profile.
    Показывает профиль игрока с его статистикой и прогрессом.
    """
    try:
        user_repository = context.bot_data["user_repository"]
        user = await user_repository.get_user(update.effective_user.id)

        if not user:
            await update.message.reply_text(USER_NOT_FOUND_MESSAGE)
            return

        # Обновляем энергию перед показом профиля
        user.update_energy()

        profile_text = await format_profile(user)
        await update.message.reply_text(
            profile_text,
            parse_mode="Markdown",
            reply_markup=await create_profile_keyboard(),
        )

        logger.info(f"User {user.id} viewed their profile")

    except Exception as e:
        logger.error(f"Error in profile command: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при показе профиля.\n"
            + "Пожалуйста, попробуйте позже."
        )


async def cases(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /cases.
    Показывает список доступных и активных расследований.
    """
    try:
        user_repository = context.bot_data["user_repository"]
        case_repository = context.bot_data["case_repository"]

        user = await user_repository.get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text(USER_NOT_FOUND_MESSAGE)
            return

        # Получаем активные и доступные расследования
        active_cases = await case_repository.get_user_active_cases(user.id)
        available_cases = await case_repository.get_available_cases(user.id)

        cases_text = (
            "🔍 *Список расследований*\n\n"
            f"*Активные расследования:* {len(active_cases)}\n"
            f"*Доступные расследования:* {len(available_cases)}\n\n"
            "Выберите действие:"
        )

        await update.message.reply_text(
            cases_text,
            parse_mode="Markdown",
            reply_markup=await create_investigation_keyboard(),
        )

        logger.info(f"User {user.id} viewed cases list")

    except Exception as e:
        logger.error(f"Error in cases command: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при показе списка расследований.\n"
            + "Пожалуйста, попробуйте позже."
        )


async def newcase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /newcase.
    Начинает новое расследование.
    """
    user = update.effective_user
    logger.info(f"Пользователь {user.id} запросил новое расследование")

    try:
        # Проверяем энергию пользователя
        if user.energy < config.ENERGY_COST_NEW_CASE:
            await update.message.reply_text(
                f"У вас недостаточно энергии для начала нового расследования.\n"
                f"Требуется: {config.ENERGY_COST_NEW_CASE} энергии\n"
                f"У вас: {user.energy} энергии"
            )
            return

        # Получаем шаблон расследования
        template = await investigation_repository.get_template_by_level(user.level)
        if not template:
            await update.message.reply_text(
                "К сожалению, сейчас нет доступных расследований для вашего уровня."
            )
            return

        # Создаем новое расследование
        investigation = await investigation_repository.create_investigation(
            user_id=user.id,
            template_id=template.id,
            title=template.title,
            description=template.description,
            difficulty=template.difficulty,
        )

        # Обновляем статус пользователя
        await user_repository.update_user_status(
            user_id=user.id, current_investigation_id=investigation.id
        )

        # Списываем энергию
        await user_repository.update_energy(
            user_id=user.id, energy_change=-config.ENERGY_COST_NEW_CASE
        )

        # Создаем клавиатуру с действиями
        keyboard = await create_investigation_keyboard()

        # Отправляем сообщение с описанием дела
        await update.message.reply_text(
            f"🔍 Новое расследование: {investigation.title}\n\n"
            f"{investigation.description}\n\n"
            f"Сложность: {investigation.difficulty}\n"
            f"Текущее местоположение: {investigation.current_location.name}",
            reply_markup=keyboard,
        )

        logger.info(
            f"Пользователь {user.id} начал новое расследование {investigation.id}"
        )

    except Exception as e:
        logger.error(f"Ошибка при создании нового расследования: {e}")
        await update.message.reply_text(
            "Произошла ошибка при создании нового расследования. Попробуйте позже."
        )


async def news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /news.
    Показывает последние новости и обновления.
    """
    try:
        news_repository = context.bot_data["news_repository"]
        user_repository = context.bot_data["user_repository"]

        user = await user_repository.get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text(USER_NOT_FOUND_MESSAGE)
            return

        # Получаем последние новости
        latest_news = await news_repository.get_latest_news(limit=5)

        if not latest_news:
            await update.message.reply_text(NO_NEWS_MESSAGE)
            return

        news_text = NEWS_HEADER_MESSAGE
        for news in latest_news:
            news_text += f"*{news.title}*\n{news.content}\n\n"

        await update.message.reply_text(
            news_text,
            parse_mode="Markdown",
            reply_markup=await create_main_menu_keyboard(),
        )

        logger.info(f"User {user.id} viewed news")

    except Exception as e:
        logger.error(f"Error in news command: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при показе новостей.\n"
            + "Пожалуйста, попробуйте позже."
        )


async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обработчик команды /analyze.
    Анализирует предоставленный текст с помощью психологического профилирования.
    """
    try:
        if not context.args:
            await update.message.reply_text(
                "❌ Пожалуйста, укажите текст для анализа.\n"
                "Пример: /analyze Текст для анализа"
            )
            return ConversationHandler.END

        user_repository = context.bot_data["user_repository"]
        claude_service = context.bot_data["claude_service"]

        user = await user_repository.get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text(USER_NOT_FOUND_MESSAGE)
            return ConversationHandler.END

        # Проверяем уровень навыка психологии
        if user.psychology_skill < 3:
            await update.message.reply_text(
                "❌ Ваш уровень навыка психологии слишком низкий для анализа.\n"
                "Повысьте уровень навыка для использования этой функции."
            )
            return ConversationHandler.END

        text = " ".join(context.args)

        # Получаем анализ от Claude
        analysis = await claude_service.analyze_text(
            text=text,
            context={
                "user_level": user.level,
                "psychology_skill": user.psychology_skill,
            },
        )

        await update.message.reply_text(
            f"🧠 *Анализ текста:*\n\n{analysis}",
            parse_mode="Markdown",
            reply_markup=await create_main_menu_keyboard(),
        )

        logger.info(f"User {user.id} analyzed text")
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error in analyze command: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при анализе текста.\n", "Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END


async def format_user_profile(user) -> str:
    """
    Форматирует профиль пользователя для отображения.

    Args:
        user: Объект пользователя

    Returns:
        str: Отформатированный текст профиля
    """
    profile_text = f"👤 *Профиль детектива*\n\n" f"🆔 ID: `{user.telegram_id}`"
    return profile_text
