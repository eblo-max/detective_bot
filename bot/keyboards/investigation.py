import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Union

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from game.player.skills import SkillType

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Типы действий в расследовании"""

    EXAMINE = "examine"  # Осмотр места
    INTERROGATE = "interrogate"  # Допрос
    ANALYZE = "analyze"  # Анализ улик
    MOVE = "move"  # Перемещение
    USE_SKILL = "use_skill"  # Использование навыка
    MAKE_DEDUCTION = "make_deduction"  # Выдвижение версии
    FINAL_DECISION = "final_decision"  # Финальное решение


@dataclass
class ButtonData:
    """Данные для кнопки"""

    action: ActionType
    target_id: str
    additional_data: Optional[Dict] = None


class InvestigationKeyboards:
    """Клавиатуры для расследований"""

    @staticmethod
    def create_main_menu() -> InlineKeyboardMarkup:
        """Создание главного меню расследования"""
        keyboard = [
            [
                InlineKeyboardButton(
                    "🔍 Осмотреть место",
                    callback_data=str(
                        ButtonData(
                            action=ActionType.EXAMINE, target_id="location"
                        ).__dict__
                    ),
                ),
                InlineKeyboardButton(
                    "👥 Допросить свидетеля",
                    callback_data=str(
                        ButtonData(
                            action=ActionType.INTERROGATE, target_id="witnesses"
                        ).__dict__
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    "🔬 Анализировать улики",
                    callback_data=str(
                        ButtonData(
                            action=ActionType.ANALYZE, target_id="evidence"
                        ).__dict__
                    ),
                ),
                InlineKeyboardButton(
                    "🧠 Выдвинуть версию",
                    callback_data=str(
                        ButtonData(
                            action=ActionType.MAKE_DEDUCTION, target_id="deduction"
                        ).__dict__
                    ),
                ),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_location_keyboard(
        locations: List[Dict], current_location: str
    ) -> InlineKeyboardMarkup:
        """Создание клавиатуры для перемещения по локациям"""
        keyboard = []
        row = []

        for location in locations:
            if location["id"] != current_location:
                row.append(
                    InlineKeyboardButton(
                        text=f"📍 {location['name']}",
                        callback_data=str(
                            ButtonData(
                                action=ActionType.MOVE, target_id=location["id"]
                            ).__dict__
                        ),
                    )
                )
                if len(row) == 2:
                    keyboard.append(row)
                    row = []

        if row:
            keyboard.append(row)

        keyboard.append(
            [
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=str(
                        ButtonData(action=ActionType.MOVE, target_id="back").__dict__
                    ),
                )
            ]
        )

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_examination_keyboard(
        examineable_objects: List[Dict], player_skills: Dict[SkillType, int]
    ) -> InlineKeyboardMarkup:
        """Создание клавиатуры для осмотра объектов"""
        keyboard = []
        row = []

        for obj in examineable_objects:
            # Проверяем, доступен ли объект для осмотра
            if obj.get("required_skill"):
                skill_type = SkillType(obj["required_skill"])
                if player_skills.get(skill_type, 0) < obj.get("required_level", 1):
                    continue

            row.append(
                InlineKeyboardButton(
                    text=f"🔍 {obj['name']}",
                    callback_data=str(
                        ButtonData(
                            action=ActionType.EXAMINE,
                            target_id=obj["id"],
                            additional_data={"object_type": obj["type"]},
                        ).__dict__
                    ),
                )
            )
            if len(row) == 2:
                keyboard.append(row)
                row = []

        if row:
            keyboard.append(row)

        keyboard.append(
            [
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=str(
                        ButtonData(action=ActionType.EXAMINE, target_id="back").__dict__
                    ),
                )
            ]
        )

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_interrogation_keyboard(
        witnesses: List[Dict], player_skills: Dict[SkillType, int]
    ) -> InlineKeyboardMarkup:
        """Создание клавиатуры для допроса свидетелей"""
        keyboard = []
        row = []

        for witness in witnesses:
            # Проверяем, доступен ли свидетель для допроса
            if witness.get("required_skill"):
                skill_type = SkillType(witness["required_skill"])
                if player_skills.get(skill_type, 0) < witness.get("required_level", 1):
                    continue

            row.append(
                InlineKeyboardButton(
                    text=f"👤 {witness['name']}",
                    callback_data=str(
                        ButtonData(
                            action=ActionType.INTERROGATE,
                            target_id=witness["id"],
                            additional_data={"witness_type": witness["type"]},
                        ).__dict__
                    ),
                )
            )
            if len(row) == 2:
                keyboard.append(row)
                row = []

        if row:
            keyboard.append(row)

        keyboard.append(
            [
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=str(
                        ButtonData(
                            action=ActionType.INTERROGATE, target_id="back"
                        ).__dict__
                    ),
                )
            ]
        )

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_evidence_analysis_keyboard(
        evidence: List[Dict], player_skills: Dict[SkillType, int]
    ) -> InlineKeyboardMarkup:
        """Создание клавиатуры для анализа улик"""
        keyboard = []
        row = []

        for item in evidence:
            # Проверяем, доступен ли предмет для анализа
            if item.get("required_skill"):
                skill_type = SkillType(item["required_skill"])
                if player_skills.get(skill_type, 0) < item.get("required_level", 1):
                    continue

            row.append(
                InlineKeyboardButton(
                    text=f"🔬 {item['name']}",
                    callback_data=str(
                        ButtonData(
                            action=ActionType.ANALYZE,
                            target_id=item["id"],
                            additional_data={"evidence_type": item["type"]},
                        ).__dict__
                    ),
                )
            )
            if len(row) == 2:
                keyboard.append(row)
                row = []

        if row:
            keyboard.append(row)

        keyboard.append(
            [
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=str(
                        ButtonData(action=ActionType.ANALYZE, target_id="back").__dict__
                    ),
                )
            ]
        )

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_skill_usage_keyboard(
        available_skills: Dict[SkillType, int], target_id: str, target_type: str
    ) -> InlineKeyboardMarkup:
        """Создание клавиатуры для использования навыков"""
        keyboard = []
        row = []

        for skill_type, level in available_skills.items():
            row.append(
                InlineKeyboardButton(
                    text=f"💡 {skill_type.name} (Ур. {level})",
                    callback_data=str(
                        ButtonData(
                            action=ActionType.USE_SKILL,
                            target_id=target_id,
                            additional_data={
                                "skill_type": skill_type.value,
                                "target_type": target_type,
                            },
                        ).__dict__
                    ),
                )
            )
            if len(row) == 2:
                keyboard.append(row)
                row = []

        if row:
            keyboard.append(row)

        keyboard.append(
            [
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=str(
                        ButtonData(
                            action=ActionType.USE_SKILL, target_id="back"
                        ).__dict__
                    ),
                )
            ]
        )

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_deduction_keyboard(
        available_theories: List[Dict], player_skills: Dict[SkillType, int]
    ) -> InlineKeyboardMarkup:
        """Создание клавиатуры для выдвижения версий"""
        keyboard = []
        row = []

        for theory in available_theories:
            # Проверяем, доступна ли версия для выдвижения
            if theory.get("required_skill"):
                skill_type = SkillType(theory["required_skill"])
                if player_skills.get(skill_type, 0) < theory.get("required_level", 1):
                    continue

            row.append(
                InlineKeyboardButton(
                    text=f"🧠 {theory['name']}",
                    callback_data=str(
                        ButtonData(
                            action=ActionType.MAKE_DEDUCTION,
                            target_id=theory["id"],
                            additional_data={"theory_type": theory["type"]},
                        ).__dict__
                    ),
                )
            )
            if len(row) == 2:
                keyboard.append(row)
                row = []

        if row:
            keyboard.append(row)

        keyboard.append(
            [
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=str(
                        ButtonData(
                            action=ActionType.MAKE_DEDUCTION, target_id="back"
                        ).__dict__
                    ),
                )
            ]
        )

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_final_decision_keyboard(
        available_decisions: List[Dict], player_skills: Dict[SkillType, int]
    ) -> InlineKeyboardMarkup:
        """Создание клавиатуры для принятия финального решения"""
        keyboard = []
        row = []

        for decision in available_decisions:
            # Проверяем, доступно ли решение
            if decision.get("required_skill"):
                skill_type = SkillType(decision["required_skill"])
                if player_skills.get(skill_type, 0) < decision.get("required_level", 1):
                    continue

            row.append(
                InlineKeyboardButton(
                    text=f"⚖️ {decision['name']}",
                    callback_data=str(
                        ButtonData(
                            action=ActionType.FINAL_DECISION,
                            target_id=decision["id"],
                            additional_data={"decision_type": decision["type"]},
                        ).__dict__
                    ),
                )
            )
            if len(row) == 2:
                keyboard.append(row)
                row = []

        if row:
            keyboard.append(row)

        keyboard.append(
            [
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=str(
                        ButtonData(
                            action=ActionType.FINAL_DECISION, target_id="back"
                        ).__dict__
                    ),
                )
            ]
        )

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_hints_keyboard(
        available_hints: List[Dict], player_skills: Dict[SkillType, int]
    ) -> InlineKeyboardMarkup:
        """Создание клавиатуры для подсказок"""
        keyboard = []
        row = []

        for hint in available_hints:
            # Проверяем, доступна ли подсказка
            if hint.get("required_skill"):
                skill_type = SkillType(hint["required_skill"])
                if player_skills.get(skill_type, 0) < hint.get("required_level", 1):
                    continue

            row.append(
                InlineKeyboardButton(
                    text=f"💡 {hint['name']}",
                    callback_data=str(
                        ButtonData(
                            action=ActionType.USE_SKILL,
                            target_id=hint["id"],
                            additional_data={"hint_type": hint["type"]},
                        ).__dict__
                    ),
                )
            )
            if len(row) == 2:
                keyboard.append(row)
                row = []

        if row:
            keyboard.append(row)

        keyboard.append(
            [
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=str(
                        ButtonData(
                            action=ActionType.USE_SKILL, target_id="back"
                        ).__dict__
                    ),
                )
            ]
        )

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def parse_callback_data(callback_data: str) -> ButtonData:
        """Парсинг данных из callback_data"""
        try:
            data = eval(callback_data)
            return ButtonData(**data)
        except Exception as e:
            logger.error(f"Ошибка при парсинге callback_data: {e}")
            return ButtonData(action=ActionType.MOVE, target_id="error")
