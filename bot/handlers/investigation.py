"""Обработчики для расследований."""

import logging
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union

from telegram import InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    Application,
)

from bot.handlers.states import States
from bot.keyboards.investigation import InvestigationKeyboards
from bot.keyboards.common_keyboard import create_main_menu_keyboard
from bot.utils.formatters import format_investigation_response
from bot.core.config import config
from bot.database.models.case import Case
from bot.database.models.investigation import Investigation
from bot.database.models.user import User
from bot.database.repositories.case_repository import CaseRepository
from bot.database.repositories.investigation_repository import InvestigationRepository
from bot.database.repositories.user_repository import UserRepository
from game.investigation.case import Case
from game.player.energy import EnergyManager
from game.player.skills import SkillType
from services.claude_service.claude_service import ClaudeService
from bot.database.db import get_db

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Типы действий в расследовании"""

    EXAMINE = "examine"
    INTERROGATE = "interrogate"
    ANALYZE = "analyze"
    MAKE_DEDUCTION = "deduction"
    BACK = "back"


class ButtonData:
    """Данные для кнопок в клавиатуре"""

    def __init__(self, action: str, target_id: Optional[str] = None):
        self.action = action
        self.target_id = target_id

    def __str__(self) -> str:
        if self.target_id:
            return f"{self.action}_{self.target_id}"
        return self.action


# Глобальные переменные для репозиториев и менеджеров
case_repository = None
user_repository = None
investigation_repository = None
energy_manager = EnergyManager()
claude_service = ClaudeService()

# Создаем экземпляр клавиатуры расследований
investigation_keyboards = InvestigationKeyboards()


async def init_repositories():
    """Инициализация репозиториев"""
    global case_repository, user_repository, investigation_repository
    session = await get_db()
    case_repository = CaseRepository(session)
    user_repository = UserRepository(session)
    investigation_repository = InvestigationRepository(session)


async def start_investigation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Начало расследования"""
    try:
        if case_repository is None or user_repository is None:
            await init_repositories()

        user_id = update.effective_user.id

        # Проверяем энергию игрока
        user = await user_repository.get_user_by_telegram_id(user_id)
        if not user or user.energy.current < 10:
            await update.message.reply_text(
                "❌ У вас недостаточно энергии для начала расследования.\n"
                "Подождите, пока энергия восстановится."
            )
            return ConversationHandler.END

        # Получаем доступные расследования
        available_cases = await case_repository.get_available_cases(user_id)
        if not available_cases:
            await update.message.reply_text(
                "❌ В данный момент нет доступных расследований.\n" "Попробуйте позже."
            )
            return ConversationHandler.END

        # Создаем клавиатуру с доступными расследованиями
        keyboard = InvestigationKeyboards.create_main_menu()
        await update.message.reply_text(
            "🔍 Выберите расследование для начала:", reply_markup=keyboard
        )

        # Сохраняем состояние
        context.user_data["state"] = States.MAIN_MENU
        return States.MAIN_MENU

    except Exception as e:
        logger.error(f"Error starting investigation: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при начале расследования.\n" "Попробуйте позже."
        )
        return ConversationHandler.END


async def handle_main_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка основных действий в меню расследования"""
    try:
        query = update.callback_query
        await query.answer()

        case_id = context.user_data.get("case_id")
        if not case_id:
            await query.message.edit_text("❌ Ошибка: расследование не найдено")
            return ConversationHandler.END

        action_type = query.data.split("_")[0]

        if action_type == "examine":
            await query.message.edit_text(
                "🔍 Выберите объект для осмотра:",
                reply_markup=await create_investigation_actions_keyboard(
                    await get_examineable_objects(case_id)
                ),
            )
            return States.EXAMINING_SCENE

        elif action_type == "interrogate":
            await query.message.edit_text(
                "👥 Выберите персонажа для допроса:",
                reply_markup=await create_investigation_actions_keyboard(
                    await get_available_witnesses(case_id)
                ),
            )
            return States.INTERVIEWING_WITNESS

        elif action_type == "analyze":
            await query.message.edit_text(
                "🔬 Выберите улику для анализа:",
                reply_markup=await create_investigation_actions_keyboard(
                    await get_available_evidence(case_id)
                ),
            )
            return States.ANALYZING_EVIDENCE

        elif action_type == "deduction":
            await query.message.edit_text(
                "🧠 Выберите версию для проверки:",
                reply_markup=await create_investigation_actions_keyboard(
                    await get_available_theories(case_id)
                ),
            )
            return States.MAKING_DEDUCTION

        elif action_type == "skill":
            await query.message.edit_text(
                "✨ Выберите навык для использования:",
                reply_markup=await create_investigation_actions_keyboard(
                    await get_available_skills(update.effective_user.id)
                ),
            )
            return States.ANALYZING

        elif action_type == "decide":
            await query.message.edit_text(
                "⚖️ Выберите ваше решение:",
                reply_markup=await create_decision_keyboard(
                    await get_available_decisions(case_id)
                ),
            )
            return States.FINAL_DECISION

        else:
            await query.message.edit_text("❌ Неизвестное действие")
            return ConversationHandler.END

    except Exception as e:
        logger.error(f"Ошибка в главном меню: {e}")
        await update.callback_query.message.edit_text("❌ Произошла ошибка")
        return ConversationHandler.END


async def select_case(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выбор расследования"""
    try:
        query = update.callback_query
        await query.answer()

        case_id = query.data.split("_")[1]
        context.user_data["case_id"] = case_id

        case = await case_repository.get_case(case_id)
        if not case:
            await query.message.edit_text("❌ Расследование не найдено")
            return ConversationHandler.END

        await query.message.edit_text(
            f"🔍 *{case.title}*\n\n{case.description}\n\nВыберите действие:",
            parse_mode="Markdown",
            reply_markup=await create_investigation_actions_keyboard([case]),
        )

        return States.MAIN_MENU

    except Exception as e:
        logger.error(f"Ошибка при выборе расследования: {e}")
        await query.message.edit_text("❌ Произошла ошибка при выборе расследования")
        return ConversationHandler.END


async def handle_examination_action(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Обработка действий осмотра"""
    try:
        query = update.callback_query
        await query.answer()  # Убираем часики с кнопки

        case_id = context.user_data.get("case_id")
        if not case_id:
            await query.message.edit_text("❌ Ошибка: расследование не найдено")
            return ConversationHandler.END

        # Получаем результат осмотра
        result = await claude_service.generate_next_step(
            case_id=case_id, action_type="examine", target_id=query.data.split("_")[1]
        )

        # Обновляем сообщение с результатом
        await query.message.edit_text(
            f"🔍 Результат осмотра:\n\n{result}\n\nВыберите следующее действие:",
            reply_markup=await create_investigation_actions_keyboard(
                [await case_repository.get_case(case_id)]
            ),
        )

        return States.MAIN_MENU

    except Exception as e:
        logger.error(f"Ошибка при осмотре: {e}")
        await query.message.edit_text("❌ Произошла ошибка при осмотре")
        return ConversationHandler.END


async def handle_interrogation_action(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Обработка допроса"""
    try:
        query = update.callback_query
        await query.answer()

        case_id = context.user_data.get("case_id")
        if not case_id:
            await query.message.edit_text("❌ Ошибка: расследование не найдено")
            return ConversationHandler.END

        result = await claude_service.generate_next_step(
            case_id=case_id,
            action_type="interrogate",
            target_id=query.data.split("_")[1],
        )

        await query.message.edit_text(
            f"👥 Результат допроса:\n\n{result}\n\nВыберите следующее действие:",
            reply_markup=await create_investigation_actions_keyboard(
                [await case_repository.get_case(case_id)]
            ),
        )

        return States.MAIN_MENU

    except Exception as e:
        logger.error(f"Ошибка при допросе: {e}")
        await query.message.edit_text("❌ Произошла ошибка при допросе")
        return ConversationHandler.END


async def handle_analysis_action(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Обработка анализа улик"""
    try:
        query = update.callback_query
        await query.answer()

        case_id = context.user_data.get("case_id")
        if not case_id:
            await query.message.edit_text("❌ Ошибка: расследование не найдено")
            return ConversationHandler.END

        result = await claude_service.generate_next_step(
            case_id=case_id, action_type="analyze", target_id=query.data.split("_")[1]
        )

        await query.message.edit_text(
            f"🔬 Результат анализа:\n\n{result}\n\nВыберите следующее действие:",
            reply_markup=await create_investigation_actions_keyboard(
                [await case_repository.get_case(case_id)]
            ),
        )

        return States.MAIN_MENU

    except Exception as e:
        logger.error(f"Ошибка при анализе: {e}")
        await query.message.edit_text("❌ Произошла ошибка при анализе")
        return ConversationHandler.END


async def handle_deduction_action(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Обработка выдвижения версии"""
    try:
        query = update.callback_query
        await query.answer()

        case_id = context.user_data.get("case_id")
        if not case_id:
            await query.message.edit_text("❌ Ошибка: расследование не найдено")
            return ConversationHandler.END

        result = await claude_service.generate_next_step(
            case_id=case_id, action_type="deduction", target_id=query.data.split("_")[1]
        )

        await query.message.edit_text(
            f"🧠 Результат рассуждения:\n\n{result}\n\nВыберите следующее действие:",
            reply_markup=await create_investigation_actions_keyboard(
                [await case_repository.get_case(case_id)]
            ),
        )

        return States.MAIN_MENU

    except Exception as e:
        logger.error(f"Ошибка при выдвижении версии: {e}")
        await query.message.edit_text("❌ Произошла ошибка при выдвижении версии")
        return ConversationHandler.END


async def handle_skill_action(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Обработка использования навыка"""
    try:
        query = update.callback_query
        await query.answer()

        case_id = context.user_data.get("case_id")
        if not case_id:
            await query.message.edit_text("❌ Ошибка: расследование не найдено")
            return ConversationHandler.END

        skill_id = query.data.split("_")[1]
        result = await claude_service.generate_next_step(
            case_id=case_id, action_type="skill", target_id=skill_id
        )

        await query.message.edit_text(
            f"🎯 Результат использования навыка:\n\n{result}\n\nВыберите следующее действие:",
            reply_markup=await create_investigation_actions_keyboard(
                [await case_repository.get_case(case_id)]
            ),
        )

        return States.MAIN_MENU

    except Exception as e:
        logger.error(f"Ошибка при использовании навыка: {e}")
        await query.message.edit_text("❌ Произошла ошибка при использовании навыка")
        return ConversationHandler.END


async def handle_final_decision(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Обработка финального решения по делу"""
    try:
        query = update.callback_query
        await query.answer()

        case_id = context.user_data.get("case_id")
        if not case_id:
            await query.message.edit_text("❌ Ошибка: расследование не найдено")
            return ConversationHandler.END

        decision_id = query.data.split("_")[1]
        result = await claude_service.generate_next_step(
            case_id=case_id, action_type="decision", target_id=decision_id
        )

        # Завершаем расследование
        await case_repository.close_case(case_id, decision_id)

        await query.message.edit_text(
            f"🎭 Финальное решение:\n\n{result}\n\nРасследование завершено.",
            reply_markup=None,
        )

        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Ошибка при принятии финального решения: {e}")
        await query.message.edit_text(
            "❌ Произошла ошибка при принятии финального решения"
        )
        return ConversationHandler.END


async def cancel_investigation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Отмена расследования"""
    try:
        query = update.callback_query
        if query:
            await query.answer()
            await query.message.edit_text("❌ Расследование отменено")
        else:
            await update.message.reply_text("❌ Расследование отменено")

        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Ошибка при отмене расследования: {e}")
        return ConversationHandler.END


# Создаем ConversationHandler
investigation_handler = ConversationHandler(
    entry_points=[CommandHandler("investigate", start_investigation)],
    states={
        States.MAIN_MENU: [
            CallbackQueryHandler(handle_main_action, pattern="^action_"),
            CallbackQueryHandler(select_case, pattern="^case_"),
        ],
        States.EXAMINING_SCENE: [
            CallbackQueryHandler(handle_examination_action, pattern="^action_")
        ],
        States.INTERVIEWING_WITNESS: [
            CallbackQueryHandler(handle_interrogation_action, pattern="^action_")
        ],
        States.ANALYZING_EVIDENCE: [
            CallbackQueryHandler(handle_analysis_action, pattern="^action_")
        ],
        States.MAKING_DEDUCTION: [
            CallbackQueryHandler(handle_deduction_action, pattern="^action_")
        ],
        States.ANALYZING: [
            CallbackQueryHandler(handle_skill_action, pattern="^skill_")
        ],
        States.FINAL_DECISION: [
            CallbackQueryHandler(handle_final_decision, pattern="^decision_")
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_investigation)],
    per_message=False,
)


def register_investigation_handlers(application: Application) -> None:
    """
    Регистрирует обработчики расследований в приложении.

    Args:
        application: Экземпляр Application для регистрации обработчиков
    """
    # Инициализируем репозитории при запуске
    application.job_queue.run_once(init_repositories, 0)

    # Регистрируем обработчик расследований
    application.add_handler(investigation_handler)

    logger.info("Investigation handlers registered successfully")


async def handle_examination(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_repository: UserRepository
):
    """Обработка осмотра места"""
    try:
        state_data = context.user_data
        user = await user_repository.get_user(update.effective_user.id)

        # Получаем доступные объекты для осмотра
        examineable_objects = await get_examineable_objects(state_data["case_id"])

        # Создаем клавиатуру
        keyboard = create_investigation_actions_keyboard(examineable_objects)

        # Обновляем сообщение
        await update.callback_query.message.edit_text(
            "🔍 Выберите объект для осмотра:", reply_markup=keyboard
        )

        # Обновляем состояние
        await context.bot.set_state(
            update.effective_user.id, state=States.EXAMINING_SCENE
        )

    except Exception as e:
        logger.error(f"Error handling examination: {e}")
        await update.callback_query.answer("❌ Произошла ошибка при осмотре")


async def create_investigation_actions_keyboard(
    items: List[Dict[str, Any]],
) -> InlineKeyboardMarkup:
    """Создает клавиатуру действий для расследования"""
    return investigation_keyboards.create_action_keyboard(items)


async def get_examineable_objects(case_id: int) -> List[Dict[str, Any]]:
    """Получает список объектов для осмотра"""
    if case_repository is None:
        await init_repositories()
    return await case_repository.get_examineable_objects(case_id)


async def get_available_witnesses(case_id: int) -> List[Dict[str, Any]]:
    """Получает список доступных свидетелей"""
    if case_repository is None:
        await init_repositories()
    return await case_repository.get_available_witnesses(case_id)


async def get_available_evidence(case_id: int) -> List[Dict[str, Any]]:
    """Получает список доступных улик"""
    if case_repository is None:
        await init_repositories()
    return await case_repository.get_available_evidence(case_id)


async def get_available_theories(case_id: int) -> List[Dict[str, Any]]:
    """Получает список доступных теорий"""
    if case_repository is None:
        await init_repositories()
    return await case_repository.get_available_theories(case_id)


async def get_available_skills(user_id: int) -> List[Dict[str, Any]]:
    """Получает список доступных навыков"""
    if user_repository is None:
        await init_repositories()
    user = await user_repository.get_user_by_telegram_id(user_id)
    return user.get_available_skills() if user else []


async def create_decision_keyboard(
    decisions: List[Dict[str, Any]],
) -> InlineKeyboardMarkup:
    """Создает клавиатуру для принятия решения"""
    return investigation_keyboards.create_decision_keyboard(decisions)


async def get_available_decisions(case_id: int) -> List[Dict[str, Any]]:
    """Получает список доступных решений"""
    if case_repository is None:
        await init_repositories()
    return await case_repository.get_available_decisions(case_id)
