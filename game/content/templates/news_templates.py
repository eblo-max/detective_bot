from datetime import datetime
from typing import Dict, List

from bot.database.models.news import News, NewsCategory


class NewsTemplates:
    @staticmethod
    def get_news_item(news: Dict) -> str:
        """Шаблон новостной заметки"""
        date = datetime.fromisoformat(news["created_at"]).strftime("%d.%m.%Y")
        return f"📰 {news['title']}\n\n{news['description']}\n\nДата: {date}"

    @staticmethod
    def get_news_list(news_items: list) -> str:
        """Шаблон списка новостей"""
        result = "📰 Последние новости:\n\n"
        for item in news_items:
            result += NewsTemplates.get_news_item(item) + "\n\n"
        return result

    @staticmethod
    def get_breaking_news(news: Dict) -> str:
        """Шаблон срочной новости"""
        return f"🚨 СРОЧНО!\n\n{news['title']}\n\n{news['description']}"
