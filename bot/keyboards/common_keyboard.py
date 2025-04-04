"""Общие клавиатуры бота"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


async def create_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Создает inline клавиатуру главного меню"""
    keyboard = [
        [
            InlineKeyboardButton(
                "🔍 Расследования", callback_data="menu_investigations"
            ),
            InlineKeyboardButton("👤 Профиль", callback_data="menu_profile"),
        ],
        [
            InlineKeyboardButton("📊 Статистика", callback_data="menu_stats"),
            InlineKeyboardButton("🏆 Достижения", callback_data="menu_achievements"),
        ],
        [
            InlineKeyboardButton("📰 Новости", callback_data="menu_news"),
            InlineKeyboardButton("❓ Помощь", callback_data="menu_help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Создает reply клавиатуру главного меню"""
    keyboard = [
        ["🔍 Новое расследование", "📰 Новости"],
        ["👤 Профиль", "🏆 Достижения"],
        ["❓ Помощь"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
