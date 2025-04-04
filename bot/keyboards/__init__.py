"""Инициализация клавиатур."""

from bot.keyboards.common_keyboard import (
    create_main_menu_keyboard,
    get_main_menu_keyboard,
)
from bot.keyboards.investigation import (
    ActionType,
    ButtonData,
    InvestigationKeyboards,
)
from bot.keyboards.profile_keyboard import (
    create_profile_keyboard,
    create_back_to_profile_keyboard,
)

__all__ = [
    # Общие клавиатуры
    "create_main_menu_keyboard",
    "get_main_menu_keyboard",
    # Клавиатуры профиля
    "create_profile_keyboard",
    "create_back_to_profile_keyboard",
    # Клавиатуры расследования
    "ActionType",
    "ButtonData",
    "InvestigationKeyboards",
]
