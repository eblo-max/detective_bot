"""Функции форматирования сообщений"""

from datetime import datetime
from typing import Any, Dict, List


def format_message(text: str, **kwargs) -> str:
    """Форматирует сообщение с эмодзи и разметкой Markdown"""
    return text.format(**kwargs)


def format_profile(user: Dict[str, Any]) -> str:
    """Форматирует профиль пользователя"""
    return (
        f"👤 *Профиль детектива*\n\n"
        f"🆔 ID: `{user['telegram_id']}`\n"
        f"👤 Имя: {user.get('username', 'Не указано')}\n"
        f"📊 Уровень: {user['stats']['level']}\n"
        f"⭐ Опыт: {user['stats']['experience']}\n"
        f"💪 Энергия: {user['stats']['energy']}/{user['stats']['max_energy']}\n"
        f"🔍 Решенных дел: {user['stats']['cases_solved']}\n"
        f"✨ Идеальных дел: {user['stats'].get('perfect_cases', 0)}\n\n"
        f"🎯 Навыки:\n"
        + "\n".join(
            [f"• {name}: {data['level']}" for name, data in user["skills"].items()]
        )
    )


def format_case_description(case: Dict[str, Any]) -> str:
    """Форматирует описание дела"""
    return (
        f"📁 *{case['title']}*\n"
        f"📝 {case['description']}\n"
        f"🏆 Сложность: {'⭐' * case['difficulty']}\n"
        f"📅 Начато: {case['start_date'].strftime('%d.%m.%Y')}\n"
        f"📊 Прогресс: {case['progress']}%\n\n"
    )


def format_evidence_analysis(evidence: Dict[str, Any]) -> str:
    """Форматирует анализ улики"""
    return (
        f"🔍 *Анализ улики:* {evidence['name']}\n\n"
        f"📝 Описание: {evidence['description']}\n"
        f"🔬 Результаты анализа:\n{evidence['analysis']}\n"
        f"📊 Значимость: {evidence['importance']}/10\n\n"
    )


def format_news(news: Dict[str, Any]) -> str:
    """Форматирует новость"""
    return (
        f"📰 *{news['title']}*\n\n"
        f"{news['content']}\n\n"
        f"📅 {news['date'].strftime('%d.%m.%Y %H:%M')}\n"
    )


def format_investigation_response(response: Dict[str, Any]) -> str:
    """
    Форматирует ответ расследования.

    Args:
        response: Словарь с данными ответа

    Returns:
        str: Отформатированное сообщение
    """
    message = []

    # Основное описание
    if "description" in response:
        message.append(f"🔍 {response['description']}\n")

    # Найденные улики
    if "evidence" in response and response["evidence"]:
        message.append("\n📦 *Найденные улики:*")
        for evidence in response["evidence"]:
            message.append(f"• {evidence['name']}: {evidence['description']}")

    # Показания свидетелей
    if "witnesses" in response and response["witnesses"]:
        message.append("\n👥 *Показания свидетелей:*")
        for witness in response["witnesses"]:
            message.append(f"• {witness['name']}: {witness['statement']}")

    # Подозреваемые
    if "suspects" in response and response["suspects"]:
        message.append("\n🎭 *Подозреваемые:*")
        for suspect in response["suspects"]:
            message.append(f"• {suspect['name']}: {suspect['description']}")

    # Подсказки
    if "hints" in response and response["hints"]:
        message.append("\n💡 *Подсказки:*")
        for hint in response["hints"]:
            message.append(f"• {hint}")

    # Доступные действия
    if "available_actions" in response and response["available_actions"]:
        message.append("\n🎯 *Доступные действия:*")
        for action in response["available_actions"]:
            message.append(f"• {action}")

    return "\n".join(message)
