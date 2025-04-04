from telegram import InlineKeyboardButton, InlineKeyboardMarkup


async def create_news_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для новостей."""
    keyboard = [
        [
            InlineKeyboardButton("🗺 Карта города", callback_data="news_map"),
            InlineKeyboardButton("📰 Все новости", callback_data="news_list"),
        ],
        [InlineKeyboardButton("« Назад", callback_data="news_back")],
    ]
    return InlineKeyboardMarkup(keyboard)
