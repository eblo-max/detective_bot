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
from bot.keyboards.investigation import InvestigationKeyboards
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
            await update.message.reply_text(
                "❌ Профиль не найден. Используйте /start для создания профиля."
            )
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
            await update.message.reply_text(
                "❌ Профиль не найден. Используйте /start для создания профиля."
            )
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
            "❌ Произошла ошибка при анализе улики.\n" "Пожалуйста, попробуйте позже."
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
            await update.message.reply_text(
                "❌ Произошла ошибка при инициализации бота.\n"
                "Пожалуйста, попробуйте позже."
            )
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
            "❌ Произошла ошибка при запуске бота.\n" "Пожалуйста, попробуйте позже."
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
            "❌ Произошла ошибка при показе справки.\n" "Пожалуйста, попробуйте позже."
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
            await update.message.reply_text(
                "❌ Произошла ошибка при инициализации бота.\n"
                "Пожалуйста, попробуйте позже."
            )
            return

        user = await user_repository.get_user_by_telegram_id(update.effective_user.id)
        if not user:
            await update.message.reply_text(
                "❌ Профиль не найден. Используйте /start для создания профиля."
            )
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
            "❌ Произошла ошибка при показе профиля.\n" "Пожалуйста, попробуйте позже."
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
            await update.message.reply_text(
                "❌ Произошла ошибка при инициализации бота.\n"
                "Пожалуйста, попробуйте позже."
            )
            return

        user = await user_repository.get_user_by_telegram_id(update.effective_user.id)
        if not user:
            await update.message.reply_text(
                "❌ Профиль не найден. Используйте /start для создания профиля."
            )
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
            "Пожалуйста, попробуйте позже."
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
            await update.message.reply_text(
                "❌ Произошла ошибка при инициализации бота.\n"
                "Пожалуйста, попробуйте позже."
            )
            return

        user = await user_repository.get_user_by_telegram_id(update.effective_user.id)
        if not user:
            await update.message.reply_text(
                "❌ Профиль не найден. Используйте /start для создания профиля."
            )
            return

        latest_news = await news_repository.get_latest_news(limit=5)
        if not latest_news:
            await update.message.reply_text(
                "📰 В данный момент нет новых сообщений.\nПопробуйте позже."
            )
            return

        news_text = "📰 *Последние новости:*\n\n"
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
            "❌ Произошла ошибка при показе новостей.\n" "Пожалуйста, попробуйте позже."
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
            await update.message.reply_text(
                "❌ Произошла ошибка при инициализации бота.\n"
                "Пожалуйста, попробуйте позже."
            )
            return ConversationHandler.END

        user = await user_repository.get_user_by_telegram_id(update.effective_user.id)
        if not user:
            await update.message.reply_text(
                "❌ Профиль не найден. Используйте /start для создания профиля."
            )
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
            "❌ Произошла ошибка при анализе текста.\n" "Пожалуйста, попробуйте позже."
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
            await update.message.reply_text(
                "❌ Пользователь не найден.\n" "Используйте /start для регистрации."
            )
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
            "❌ Произошла ошибка при показе профиля.\n" "Пожалуйста, попробуйте позже."
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
            await update.message.reply_text(
                "❌ Пользователь не найден.\n" "Используйте /start для регистрации."
            )
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
            "Пожалуйста, попробуйте позже."
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
        keyboard = await create_investigation_keyboard(
            investigation.current_location.actions
        )

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
            await update.message.reply_text(
                "❌ Пользователь не найден.\n" "Используйте /start для регистрации."
            )
            return

        # Получаем последние новости
        latest_news = await news_repository.get_latest_news(limit=5)

        if not latest_news:
            await update.message.reply_text(
                "📰 В данный момент нет новых сообщений.\n" "Попробуйте позже."
            )
            return

        news_text = "📰 *Последние новости:*\n\n"
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
            "❌ Произошла ошибка при показе новостей.\n" "Пожалуйста, попробуйте позже."
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
            await update.message.reply_text(
                "❌ Пользователь не найден.\n" "Используйте /start для регистрации."
            )
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
            "❌ Произошла ошибка при анализе текста.\n" "Пожалуйста, попробуйте позже."
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
    profile_text = (
        f"👤 *Профиль детектива*\n\n"
        f"🆔 ID: `{user.telegram_id}`\n"
        f"👤 Имя: {user.username or 'Не указано'}\n"
        f"📊 Уровень: {user.stats.level}\n"
        f"⭐ Опыт: {user.stats.experience}/{user._calculate_required_exp(user.stats.level + 1)}\n"
        f"💪 Энергия: {user.stats.energy}/{user.stats.max_energy}\n"
        f"🔍 Решенных дел: {user.stats.cases_solved}\n"
        f"✨ Идеальных дел: {user.stats.perfect_cases}\n\n"
        f"🎯 Навыки:\n"
    )

    for skill_name, skill in user.skills.items():
        profile_text += (
            f"• {skill_name.title()}: {skill.level} "
            f"({skill.experience}/{user._calculate_required_exp(skill.level + 1)})\n"
        )

    return profile_text


async def format_user_achievements(user) -> str:
    """
    Форматирует список достижений пользователя.

    Args:
        user: Объект пользователя

    Returns:
        str: Отформатированный текст достижений
    """
    achievements_text = "🏆 *Достижения*\n\n"

    if user.achievements:
        for achievement in user.achievements:
            achievements_text += (
                f"*{achievement.id}*\n"
                f"📅 Получено: {achievement.unlocked_at.strftime('%d.%m.%Y')}\n"
                f"📊 Прогресс: {achievement.progress or '100%'}\n"
                f"🎯 Требования: {achievement.required}\n\n"
            )
    else:
        achievements_text += "У вас пока нет достижений.\n"
        achievements_text += "Выполняйте расследования и получайте награды!"

    return achievements_text


async def format_user_stats(user) -> str:
    """
    Форматирует статистику пользователя.

    Args:
        user: Объект пользователя

    Returns:
        str: Отформатированный текст статистики
    """
    stats_text = (
        "📊 *Подробная статистика*\n\n"
        f"🎯 Всего опыта: {user.stats.experience}\n"
        f"📈 Уровень: {user.stats.level}\n"
        f"🔍 Решено дел: {user.stats.cases_solved}\n"
        f"✨ Идеальных дел: {user.stats.perfect_cases}\n"
        f"💪 Энергия: {user.stats.energy}/{user.stats.max_energy}\n"
        f"⏰ Последнее обновление энергии: {user.stats.last_energy_update.strftime('%H:%M:%S')}\n"
    )

    return stats_text


async def format_user_skills(user) -> str:
    """
    Форматирует информацию о навыках пользователя.

    Args:
        user: Объект пользователя

    Returns:
        str: Отформатированный текст навыков
    """
    skills_text = "🎯 *Навыки*\n\n"

    for skill_name, skill in user.skills.items():
        skills_text += (
            f"*{skill_name.title()}*\n"
            f"📊 Уровень: {skill.level}\n"
            f"⭐ Опыт: {skill.experience}/{user._calculate_required_exp(skill.level + 1)}\n"
            f"🎯 Способности: {', '.join(skill.abilities) or 'Нет'}\n\n"
        )

    return skills_text


async def create_back_to_profile_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопкой возврата в профиль.

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой возврата
    """
    keyboard = [
        [InlineKeyboardButton("◀️ Назад к профилю", callback_data="back_to_profile")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def create_profile_keyboard() -> InlineKeyboardMarkup:
    """
    Создает основную клавиатуру профиля.

    Returns:
        InlineKeyboardMarkup: Клавиатура профиля
    """
    keyboard = [
        [InlineKeyboardButton("🏆 Достижения", callback_data="profile_achievements")],
        [InlineKeyboardButton("📊 Статистика", callback_data="profile_stats")],
        [InlineKeyboardButton("🎯 Навыки", callback_data="profile_skills")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def handle_profile_callback(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает нажатия кнопок в профиле.

    Args:
        update: Объект обновления
        context: Контекст бота
    """
    query = update.callback_query
    await query.answer()  # Отвечаем на колбэк, чтобы убрать "часики" у кнопки

    user_repository = UserRepository()
    user = await user_repository.get_user_by_telegram_id(query.from_user.id)

    if not user:
        await query.edit_message_text(
            "Произошла ошибка. Используйте /start для регистрации."
        )
        return

    callback_data = query.data

    if callback_data == "profile_achievements":
        achievements_text = await format_user_achievements(user)
        keyboard = await create_back_to_profile_keyboard()
        await query.edit_message_text(
            achievements_text, reply_markup=keyboard, parse_mode="Markdown"
        )

    elif callback_data == "profile_stats":
        stats_text = await format_user_stats(user)
        keyboard = await create_back_to_profile_keyboard()
        await query.edit_message_text(
            stats_text, reply_markup=keyboard, parse_mode="Markdown"
        )

    elif callback_data == "profile_skills":
        skills_text = await format_user_skills(user)
        keyboard = await create_back_to_profile_keyboard()
        await query.edit_message_text(
            skills_text, reply_markup=keyboard, parse_mode="Markdown"
        )

    elif callback_data == "back_to_profile":
        profile_text = await format_user_profile(user)
        keyboard = await create_profile_keyboard()
        await query.edit_message_text(
            profile_text, reply_markup=keyboard, parse_mode="Markdown"
        )

    logger.info(
        f"Пользователь {query.from_user.id} просматривает {callback_data} в профиле"
    )


async def format_case_description(case) -> str:
    """
    Форматирует описание дела для отображения.

    Args:
        case: Объект дела

    Returns:
        str: Отформатированное описание дела
    """
    return (
        f"🔍 *{case.title}*\n"
        f"📊 Сложность: {case.difficulty}\n"
        f"📅 Начато: {case.created_at.strftime('%d.%m.%Y')}\n"
        f"🎯 Прогресс: {case.progress}%\n\n"
    )


async def format_news() -> str:
    """
    Форматирует новости для отображения.

    Returns:
        str: Отформатированный текст новостей
    """
    news_text = "📰 *Последние новости:*\n\n"
    latest_news = await news_repository.get_latest_news(limit=5)

    if not latest_news:
        return "📰 В данный момент нет новых сообщений.\nПопробуйте позже."

    for news in latest_news:
        news_text += f"*{news.title}*\n{news.content}\n\n"

    return news_text


async def format_evidence_analysis(evidence) -> str:
    """
    Форматирует анализ улики для отображения.

    Args:
        evidence: Объект улики

    Returns:
        str: Отформатированный текст анализа улики
    """
    return (
        f"🔍 *Анализ улики #{evidence.id}*\n\n"
        f"📝 Описание: {evidence.description}\n"
        f"📊 Тип: {evidence.type}\n"
        f"🎯 Важность: {evidence.importance}\n"
        f"📅 Найдено: {evidence.found_at.strftime('%d.%m.%Y')}\n\n"
        f"Анализ:\n{evidence.analysis or 'Анализ пока не проведен'}"
    )


async def create_investigation_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для расследования"""
    return investigation_keyboards.create_main_menu()


def register_command_handlers(application: Application) -> None:
    """
    Регистрирует все обработчики команд в приложении.

    Args:
        application: Экземпляр Application для регистрации обработчиков
    """
    # Инициализируем репозитории при запуске
    application.job_queue.run_once(init_repositories, 0)

    # Регистрируем простые команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("cases", cases_command))
    application.add_handler(CommandHandler("news", news_command))

    # Регистрируем команды с ConversationHandler
    application.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("newcase", newcase)],
            states={CHOOSING_CASE: [CallbackQueryHandler(newcase, pattern="^case_")]},
            fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        )
    )

    application.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("analyze", analyze)],
            states={
                ANALYZING_TEXT: [CallbackQueryHandler(analyze, pattern="^analyze_")]
            },
            fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        )
    )

    logger.info("Command handlers registered successfully")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик текстовых сообщений.

    Args:
        update: Объект обновления
        context: Контекст
    """
    try:
        user = await user_repository.get_user_by_telegram_id(update.effective_user.id)
        if not user:
            await update.message.reply_text(
                "❌ Профиль не найден. Используйте /start для создания профиля."
            )
            return

        # Здесь можно добавить обработку различных текстовых сообщений
        await update.message.reply_text(
            "Я понимаю только команды. Используйте /help для просмотра списка доступных команд."
        )

    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обработке сообщения.\n"
            "Пожалуйста, попробуйте позже."
        )
