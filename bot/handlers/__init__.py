"""Инициализация обработчиков бота."""

from bot.handlers.commands import (
    help_command,
    start,
    news,
    profile,
    cases,
    analyze,
    handle_message,
)
from bot.handlers.investigation import (
    investigation_handler,
    register_investigation_handlers,
)
from bot.handlers.news import news_handler, register_news_handlers
from bot.handlers.profile import (
    profile_handler,
    register_profile_handlers,
    handle_profile_callback,
)
from bot.handlers.callbacks import button_callback

__all__ = [
    "commands",
    "help_command",
    "start",
    "news",
    "profile",
    "cases",
    "analyze",
    "handle_message",
    "investigation",
    "investigation_handler",
    "register_investigation_handlers",
    "news_handler",
    "register_news_handlers",
    "profile_handler",
    "register_profile_handlers",
    "button_callback",
    "handle_profile_callback",
]

# Создаем пространства имен
from . import investigation
from . import commands
