from telegram import InlineKeyboardButton, InlineKeyboardMarkup


async def create_case_actions_keyboard(case) -> InlineKeyboardMarkup:
    """Создает клавиатуру действий для дела."""
    keyboard = [
        [
            InlineKeyboardButton(
                "🔍 Начать расследование",
                callback_data=f"investigation_start_{case.id}",
            ),
            InlineKeyboardButton(
                "📝 Детали дела", callback_data=f"case_details_{case.id}"
            ),
        ],
        [InlineKeyboardButton("« Назад", callback_data="cases_list")],
    ]
    return InlineKeyboardMarkup(keyboard)
