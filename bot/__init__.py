"""
Основной пакет бота
"""

from bot.core.bot import DetectiveBot
from bot.core.config import load_config, BotConfig

__all__ = ["DetectiveBot", "load_config", "BotConfig"]
