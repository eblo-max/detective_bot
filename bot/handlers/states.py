"""Состояния для ConversationHandler"""

from enum import Enum, auto


class States(Enum):
    """Состояния диалога с ботом"""

    # Основные состояния
    MAIN_MENU = "main_menu"
    PROFILE = "profile"
    VIEWING_PROFILE = "viewing_profile"
    CASES = "cases"
    NEWS = "news"
    VIEWING_NEWS = "viewing_news"

    # Состояния расследования
    EXAMINING_SCENE = auto()
    INTERVIEWING_WITNESS = auto()
    ANALYZING_EVIDENCE = auto()
    MAKING_DEDUCTION = auto()
    FINAL_DECISION = "final_decision"

    # Состояния анализа
    ANALYZING = "analyzing"
    CONFIRMING = "confirming"

    # Состояния выбора
    CHOOSING_CASE = "choosing_case"
    ANALYZING_TEXT = "analyzing_text"
