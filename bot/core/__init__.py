"""
Основной пакет бота
"""

from bot.core.bot import DetectiveBot
from bot.core.config import load_config, BotConfig
from bot.keyboards.common_keyboard import create_main_menu_keyboard

__all__ = ["DetectiveBot", "load_config", "BotConfig", "create_main_menu_keyboard"]
