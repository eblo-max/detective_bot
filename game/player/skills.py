import math
import random
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from bot.core.config import config


class SkillType(Enum):
    """Типы навыков в игре"""

    DETECTIVE = "detective"  # Поиск улик, анализ места преступления
    FORENSIC = "forensic"  # Работа с уликами, криминалистика
    PSYCHOLOGY = "psychology"  # Работа с подозреваемыми и свидетелями


@dataclass
class SkillBonus:
    """Бонусы, предоставляемые навыком"""

    success_chance: float = 0.0  # Увеличение шанса успеха
    quality_bonus: float = 0.0  # Улучшение качества результата
    time_reduction: float = 0.0  # Уменьшение времени на действия
    special_ability: Optional[str] = None  # Особая способность


@dataclass
class SpecialAbility:
    """Особая способность, доступная при высоком уровне навыка"""

    name: str
    description: str
    required_level: int
    cooldown: int  # в минутах
    effect: Dict[str, float]


class Skill:
    """Базовый класс для навыка"""

    def __init__(
        self,
        skill_type: SkillType,
        level: int = 1,
        experience: int = 0,
        specialization: bool = False,
    ):
        self.skill_type = skill_type
        self.level = level
        self.experience = experience
        self.specialization = specialization
        self.last_used: Optional[float] = None

        # Загружаем особые способности для навыка
        self.abilities = self._init_abilities()

    def _init_abilities(self) -> Dict[int, SpecialAbility]:
        """Инициализация особых способностей навыка"""
        if self.skill_type == SkillType.DETECTIVE:
            return {
                5: SpecialAbility(
                    name="Орлиный глаз",
                    description="Повышенный шанс найти скрытые улики",
                    required_level=5,
                    cooldown=30,
                    effect={"evidence_find_chance": 0.25},
                ),
                10: SpecialAbility(
                    name="Дедукция Шерлока",
                    description="Получение дополнительных подсказок при анализе",
                    required_level=10,
                    cooldown=60,
                    effect={"hint_quality": 0.5},
                ),
            }
        elif self.skill_type == SkillType.FORENSIC:
            return {
                5: SpecialAbility(
                    name="Эксперт-криминалист",
                    description="Улучшенный анализ улик",
                    required_level=5,
                    cooldown=30,
                    effect={"analysis_quality": 0.3},
                ),
                10: SpecialAbility(
                    name="Научный метод",
                    description="Возможность проведения сложных тестов",
                    required_level=10,
                    cooldown=60,
                    effect={"test_accuracy": 0.5},
                ),
            }
        elif self.skill_type == SkillType.PSYCHOLOGY:
            return {
                5: SpecialAbility(
                    name="Эмпатия",
                    description="Лучшее понимание мотивов",
                    required_level=5,
                    cooldown=30,
                    effect={"motive_insight": 0.3},
                ),
                10: SpecialAbility(
                    name="Профайлер",
                    description="Создание точных психологических профилей",
                    required_level=10,
                    cooldown=60,
                    effect={"profile_accuracy": 0.5},
                ),
            }
        return {}

    def add_experience(self, amount: int) -> Tuple[bool, Optional[SpecialAbility]]:
        """
        Добавляет опыт навыку и возвращает tuple:
        (произошло ли повышение уровня, новая разблокированная способность)
        """
        old_level = self.level
        self.experience += amount * (1.2 if self.specialization else 1.0)

        while self.can_level_up():
            self.level_up()

        if self.level > old_level:
            new_ability = self.abilities.get(self.level)
            return True, new_ability

        return False, None

    def can_level_up(self) -> bool:
        """Проверяет, достаточно ли опыта для повышения уровня"""
        return (
            self.level < config.MAX_SKILL_LEVEL
            and self.experience >= self.get_required_exp()
        )

    def level_up(self) -> None:
        """Повышает уровень навыка"""
        self.experience -= self.get_required_exp()
        self.level += 1

    def get_required_exp(self) -> int:
        """Возвращает количество опыта, необходимое для следующего уровня"""
        return int(config.BASE_SKILL_EXP * (self.level**config.SKILL_EXP_SCALING))

    def get_success_chance(self, difficulty: int) -> float:
        """Рассчитывает шанс успеха действия"""
        base_chance = config.BASE_SUCCESS_CHANCE
        skill_bonus = (
            self.level / config.MAX_SKILL_LEVEL
        ) * config.SKILL_BONUS_MULTIPLIER
        difficulty_penalty = (difficulty / 5) * config.DIFFICULTY_PENALTY_MULTIPLIER

        return min(0.95, max(0.05, base_chance + skill_bonus - difficulty_penalty))

    def get_bonus(self) -> SkillBonus:
        """Возвращает текущие бонусы навыка"""
        level_ratio = self.level / config.MAX_SKILL_LEVEL

        return SkillBonus(
            success_chance=level_ratio * 0.3,
            quality_bonus=level_ratio * 0.2,
            time_reduction=level_ratio * 0.25,
        )

    def can_use_ability(self, ability_level: int) -> bool:
        """Проверяет, доступна ли особая способность"""
        ability = self.abilities.get(ability_level)
        if not ability or self.level < ability.required_level:
            return False
        return True


class SkillSystem:
    """Система управления навыками игрока"""

    def __init__(self):
        self.skills = {skill_type: Skill(skill_type) for skill_type in SkillType}
        self.specialization: Optional[SkillType] = None

    def improve_skill(
        self, skill_type: SkillType, amount: int
    ) -> Tuple[bool, Optional[SpecialAbility]]:
        """Улучшает навык и возвращает информацию о повышении уровня"""
        skill = self.skills[skill_type]
        return skill.add_experience(amount)

    def check_action_success(
        self, skill_type: SkillType, difficulty: int, context: Optional[Dict] = None
    ) -> Tuple[bool, Dict[str, float]]:
        """
        Проверяет успешность действия с учетом навыка и сложности.
        Возвращает (успех/неудача, детали проверки)
        """
        skill = self.skills[skill_type]
        success_chance = skill.get_success_chance(difficulty)

        # Применяем бонусы от контекста
        if context:
            if (
                context.get("is_specialized", False)
                and self.specialization == skill_type
            ):
                success_chance *= 1.2
            if context.get("has_tools", False):
                success_chance *= 1.1

        success = random.random() < success_chance

        return success, {
            "base_chance": skill.get_success_chance(difficulty),
            "final_chance": success_chance,
            "skill_level": skill.level,
            "difficulty": difficulty,
        }

    def set_specialization(self, skill_type: SkillType) -> None:
        """Устанавливает специализацию игрока"""
        if self.skills[skill_type].level >= config.MIN_SPECIALIZATION_LEVEL:
            self.specialization = skill_type
            self.skills[skill_type].specialization = True
        else:
            raise ValueError(
                f"Необходим {config.MIN_SPECIALIZATION_LEVEL} уровень "
                f"навыка для специализации"
            )

    def get_skill_info(self, skill_type: SkillType) -> Dict:
        """Возвращает информацию о навыке"""
        skill = self.skills[skill_type]
        return {
            "type": skill_type.value,
            "level": skill.level,
            "experience": skill.experience,
            "next_level": skill.get_required_exp(),
            "bonuses": vars(skill.get_bonus()),
            "abilities": [
                {
                    "name": ability.name,
                    "description": ability.description,
                    "unlocked": skill.level >= ability.required_level,
                }
                for level, ability in skill.abilities.items()
            ],
            "is_specialized": skill.specialization,
        }

    def get_available_abilities(self, skill_type: SkillType) -> List[SpecialAbility]:
        """Возвращает список доступных особых способностей"""
        skill = self.skills[skill_type]
        return [
            ability
            for level, ability in skill.abilities.items()
            if skill.level >= ability.required_level
        ]

    def apply_skill_to_action(
        self, skill_type: SkillType, action_type: str, difficulty: int
    ) -> Dict[str, Any]:
        """
        Применяет навык к действию и возвращает результат.

        Args:
            skill_type: Тип навыка
            action_type: Тип действия
            difficulty: Сложность действия

        Returns:
            Dict[str, Any]: Результат применения навыка
        """
        skill = self.skills[skill_type]
        success, details = self.check_action_success(skill_type, difficulty)

        # Получаем бонусы от навыка
        bonus = skill.get_bonus()

        # Проверяем, можно ли использовать специальную способность
        available_abilities = self.get_available_abilities(skill_type)
        used_ability = None

        if (
            available_abilities and random.random() < 0.3
        ):  # 30% шанс использования способности
            used_ability = random.choice(available_abilities)
            # Применяем эффекты способности
            for effect, value in used_ability.effect.items():
                if effect in details:
                    details[effect] *= 1 + value

        return {
            "success": success,
            "details": details,
            "bonus": vars(bonus),
            "used_ability": vars(used_ability) if used_ability else None,
            "skill_level": skill.level,
            "experience_gained": int(difficulty * (1 + bonus.success_chance)),
        }

    def combine_skills(
        self,
        primary_skill: SkillType,
        secondary_skill: SkillType,
        action_type: str,
        difficulty: int,
    ) -> Dict[str, Any]:
        """
        Комбинирует два навыка для выполнения сложного действия.

        Args:
            primary_skill: Основной навык
            secondary_skill: Вспомогательный навык
            action_type: Тип действия
            difficulty: Сложность действия

        Returns:
            Dict[str, Any]: Результат комбинирования навыков
        """
        primary_result = self.apply_skill_to_action(
            primary_skill, action_type, difficulty
        )
        secondary_result = self.apply_skill_to_action(
            secondary_skill, action_type, difficulty
        )

        # Рассчитываем комбинированный успех
        combined_success = (
            (primary_result["success"] and secondary_result["success"])
            or (primary_result["success"] and random.random() < 0.3)
            or (secondary_result["success"] and random.random() < 0.3)
        )

        # Комбинируем бонусы
        combined_bonus = {
            "success_chance": max(
                primary_result["bonus"]["success_chance"],
                secondary_result["bonus"]["success_chance"],
            ),
            "quality_bonus": (
                primary_result["bonus"]["quality_bonus"]
                + secondary_result["bonus"]["quality_bonus"]
            )
            / 2,
            "time_reduction": max(
                primary_result["bonus"]["time_reduction"],
                secondary_result["bonus"]["time_reduction"],
            ),
        }

        return {
            "success": combined_success,
            "primary_skill": primary_result,
            "secondary_skill": secondary_result,
            "combined_bonus": combined_bonus,
            "experience_gained": int(
                difficulty * (1 + combined_bonus["success_chance"]) * 1.5
            ),
        }

    def to_dict(self) -> Dict:
        """Сериализует систему навыков в словарь"""
        return {
            "skills": {
                skill_type.value: self.get_skill_info(skill_type)
                for skill_type in SkillType
            },
            "specialization": (
                self.specialization.value if self.specialization else None
            ),
        }
