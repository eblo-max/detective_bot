"""Клавиатуры для профиля"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def create_profile_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру профиля"""
    keyboard = [
        [
            InlineKeyboardButton("📊 Статистика", callback_data="profile_stats"),
            InlineKeyboardButton("🎯 Навыки", callback_data="profile_skills"),
        ],
        [
            InlineKeyboardButton("🏆 Достижения", callback_data="profile_achievements"),
            InlineKeyboardButton("📜 История", callback_data="profile_history"),
        ],
        [InlineKeyboardButton("« Назад в меню", callback_data="back_to_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def create_back_to_profile_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для возврата в профиль"""
    keyboard = [
        [InlineKeyboardButton("🔙 Назад в профиль", callback_data="back_to_profile")]
    ]
    return InlineKeyboardMarkup(keyboard)
