"""Обработчики callback-запросов."""

import logging
from typing import Any, Dict, Optional

from telegram import Update
from telegram.ext import ContextTypes

from bot.database.repositories.case_repository import CaseRepository
from bot.database.repositories.investigation_repository import InvestigationRepository
from bot.database.repositories.user_repository import UserRepository
from bot.keyboards.investigation import InvestigationKeyboards
from bot.keyboards.profile_keyboard import create_profile_keyboard
from bot.utils.formatters import format_case_description, format_investigation_response

logger = logging.getLogger(__name__)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик callback-запросов от инлайн-кнопок"""
    try:
        query = update.callback_query
        await query.answer()

        # Разбираем данные кнопки
        data = query.data.split("_")
        action = data[0]
        target_id = data[1] if len(data) > 1 else None

        # Обрабатываем различные типы действий
        if action == "case":
            await handle_case_callback(query, target_id)
        elif action == "evidence":
            await handle_evidence_callback(query, target_id)
        elif action == "suspect":
            await handle_suspect_callback(query, target_id)
        elif action == "location":
            await handle_location_callback(query, target_id)
        elif action == "skill":
            await handle_skill_callback(query, target_id)
        elif action == "achievement":
            await handle_achievement_callback(query, target_id)
        else:
            await query.message.edit_text("❌ Неизвестное действие")

    except Exception as e:
        logger.error(f"Ошибка в обработке callback: {e}")
        await update.callback_query.message.edit_text(
            "❌ Произошла ошибка. Попробуйте позже."
        )


async def handle_case_callback(query: Any, case_id: str) -> None:
    """Обработка callback для выбора дела"""
    try:
        case = await CaseRepository.get_case(case_id)
        if not case:
            await query.message.edit_text("❌ Дело не найдено")
            return

        case_text = format_case_description(case)
        await query.message.edit_text(
            case_text,
            reply_markup=await InvestigationKeyboards.create_location_keyboard(
                case.locations
            ),
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке выбора дела: {e}")
        await query.message.edit_text("❌ Не удалось загрузить дело")


async def handle_evidence_callback(query: Any, evidence_id: str) -> None:
    """Обработка callback для выбора улики"""
    try:
        evidence = await InvestigationRepository.get_evidence(evidence_id)
        if not evidence:
            await query.message.edit_text("❌ Улика не найдена")
            return

        evidence_text = (
            f"🔍 *Улика:* {evidence.name}\n\n"
            f"Описание: {evidence.description}\n"
            f"Тип: {evidence.type}\n"
            f"Важность: {'⭐' * evidence.importance}\n\n"
            "Выберите действие:"
        )

        await query.message.edit_text(
            evidence_text,
            reply_markup=await InvestigationKeyboards.create_evidence_keyboard(
                evidence
            ),
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке выбора улики: {e}")
        await query.message.edit_text("❌ Не удалось загрузить улику")


async def handle_suspect_callback(query: Any, suspect_id: str) -> None:
    """Обработка callback для выбора подозреваемого"""
    try:
        suspect = await InvestigationRepository.get_suspect(suspect_id)
        if not suspect:
            await query.message.edit_text("❌ Подозреваемый не найден")
            return

        suspect_text = (
            f"👤 *Подозреваемый:* {suspect.name}\n\n"
            f"Описание: {suspect.description}\n"
            f"Алиби: {suspect.alibi}\n"
            f"Мотивы: {', '.join(suspect.motives)}\n\n"
            "Выберите действие:"
        )

        await query.message.edit_text(
            suspect_text,
            reply_markup=await InvestigationKeyboards.create_interrogation_keyboard(
                suspect
            ),
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке выбора подозреваемого: {e}")
        await query.message.edit_text("❌ Не удалось загрузить подозреваемого")


async def handle_location_callback(query: Any, location_id: str) -> None:
    """Обработка callback для выбора локации"""
    try:
        location = await InvestigationRepository.get_location(location_id)
        if not location:
            await query.message.edit_text("❌ Локация не найдена")
            return

        location_text = (
            f"📍 *Локация:* {location.name}\n\n"
            f"Описание: {location.description}\n"
            f"Доступные действия: {', '.join(location.available_actions)}\n\n"
            "Выберите действие:"
        )

        await query.message.edit_text(
            location_text,
            reply_markup=await InvestigationKeyboards.create_location_keyboard(
                [location]
            ),
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке выбора локации: {e}")
        await query.message.edit_text("❌ Не удалось загрузить локацию")


async def handle_skill_callback(query: Any, skill_id: str) -> None:
    """Обработка callback для использования навыка"""
    try:
        user_id = query.from_user.id
        user = await UserRepository.get_user(user_id)
        if not user:
            await query.message.edit_text("❌ Пользователь не найден")
            return

        skill = user.get_skill(skill_id)
        if not skill:
            await query.message.edit_text("❌ Навык не найден")
            return

        skill_text = (
            f"✨ *Навык:* {skill.name}\n\n"
            f"Уровень: {skill.level}\n"
            f"Опыт: {skill.experience}/{skill.next_level_exp}\n"
            f"Описание: {skill.description}\n\n"
            "Выберите действие:"
        )

        await query.message.edit_text(
            skill_text,
            reply_markup=await create_profile_keyboard(),
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке выбора навыка: {e}")
        await query.message.edit_text("❌ Не удалось загрузить навык")


async def handle_achievement_callback(query: Any, achievement_id: str) -> None:
    """Обработка callback для просмотра достижения"""
    try:
        user_id = query.from_user.id
        user = await UserRepository.get_user(user_id)
        if not user:
            await query.message.edit_text("❌ Пользователь не найден")
            return

        achievement = user.get_achievement(achievement_id)
        if not achievement:
            await query.message.edit_text("❌ Достижение не найдено")
            return

        achievement_text = (
            f"🏆 *Достижение:* {achievement.title}\n\n"
            f"Описание: {achievement.description}\n"
            f"Прогресс: {achievement.progress}/{achievement.required}\n"
            f"Награда: {achievement.reward}\n\n"
            "Выберите действие:"
        )

        await query.message.edit_text(
            achievement_text,
            reply_markup=await create_profile_keyboard(),
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке выбора достижения: {e}")
        await query.message.edit_text("❌ Не удалось загрузить достижение")
