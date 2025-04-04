"""
Основной модуль бота-детектива
"""

from .claude_service.claude_service import ClaudeService
from .news_service import NewsService
from .profile_service import ProfileService

__all__ = ["ClaudeService", "NewsService", "ProfileService"]
