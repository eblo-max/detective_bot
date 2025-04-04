from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from bot.database.models.user import User
from game.player.skills import SkillType


class AchievementCategory(Enum):
    """Категории достижений"""

    SKILLS = "skills"  # Достижения за развитие навыков
    CASES = "cases"  # Достижения за расследования
    SPECIAL = "special"  # Специальные достижения
    SECRET = "secret"  # Секретные достижения
    COLLECTION = "collection"  # Коллекционные достижения


class AchievementRarity(Enum):
    """Редкость достижений"""

    COMMON = "common"  # Обычные
    UNCOMMON = "uncommon"  # Необычные
    RARE = "rare"  # Редкие
    EPIC = "epic"  # Эпические
    LEGENDARY = "legendary"  # Легендарные


@dataclass
class AchievementReward:
    """Награда за достижение"""

    experience: int = 0
    skill_bonuses: Dict[str, float] = None  # Бонусы к навыкам
    special_abilities: List[str] = None  # Специальные способности
    items: List[str] = None  # Предметы
    money: int = 0  # Деньги
    reputation: int = 0  # Репутация


@dataclass
class AchievementProgress:
    """Прогресс достижения"""

    current: int = 0
    required: int = 0
    stages: List[int] = None
    completed_stages: List[int] = None


@dataclass
class Achievement:
    """Достижение"""

    id: str
    title: str
    description: str
    icon: str
    reward: Dict[str, int]  # тип награды -> количество
    hidden: bool = False
    category: str = "general"
    requirements: Dict[str, Any] = None
    unlocked_at: Optional[datetime] = None


class AchievementSystem:
    """Система управления достижениями"""

    def __init__(self):
        self.achievements: Dict[str, Achievement] = {}
        self.player_achievements: Dict[str, Dict] = {}
        self._init_achievements()

    def _init_achievements(self):
        """Инициализация всех достижений"""
        # Достижения за навыки
        self.achievements["skill_master"] = Achievement(
            id="skill_master",
            title="Мастер детектив",
            description="Достигните максимального уровня в любом навыке",
            icon="💫",
            reward={
                "experience": 1000,
                "skill_bonuses": {"detective": 0.2},
                "special_abilities": ["expert_analysis"],
            },
            category="skills",
            requirements={"skill_level": 100},
        )

        # Достижения за расследования
        self.achievements["case_solver"] = Achievement(
            id="case_solver",
            title="Опытный следователь",
            description="Успешно завершите 10 расследований",
            icon="🏆",
            reward={"experience": 500, "money": 1000, "reputation": 50},
            category="cases",
            requirements={"completed_cases": 10},
        )

        # Специальные достижения
        self.achievements["perfect_solve"] = Achievement(
            id="perfect_solve",
            title="Идеальное расследование",
            description="Завершите расследование без ошибок",
            icon="✨",
            reward={
                "experience": 2000,
                "money": 5000,
                "reputation": 100,
                "special_abilities": ["perfect_analysis"],
            },
            category="special",
            requirements={"perfect_case": True},
        )

        # Секретные достижения
        self.achievements["hidden_master"] = Achievement(
            id="hidden_master",
            title="Мастер тайн",
            description="???",  # Секретное описание
            icon="🌟✨",
            reward={
                "experience": 5000,
                "money": 10000,
                "reputation": 200,
                "special_abilities": ["hidden_insight"],
            },
            category="secret",
            requirements={"hidden_conditions": True},
        )

    def check_achievement(self, achievement_id: str, player_data: Dict) -> bool:
        """Проверка условий достижения"""
        achievement = self.achievements.get(achievement_id)
        if not achievement:
            return False

        # Проверка базовых условий
        if achievement.requirements:
            for key, value in achievement.requirements.items():
                if key == "skill_level":
                    if player_data.get("skills", {}).get("detective", 0) < value:
                        return False
                elif key == "completed_cases":
                    if player_data.get("completed_cases", 0) < value:
                        return False
                elif key == "perfect_case":
                    if not player_data.get("perfect_case", False):
                        return False
                # Добавьте другие проверки условий

        return True

    def update_progress(self, achievement_id: str, progress_data: Dict) -> bool:
        """Обновление прогресса достижения"""
        achievement = self.achievements.get(achievement_id)
        if not achievement:
            return False

        player_achievement = self.player_achievements.get(achievement_id, {})
        current_progress = player_achievement.get("progress", 0)

        # Обновление прогресса
        if achievement.stages:
            for stage in achievement.stages:
                if current_progress < stage <= achievement.current:
                    self._unlock_stage(achievement_id, stage)
        else:
            achievement.current += 1

        # Проверка завершения
        if achievement.current >= achievement.required:
            return self.complete_achievement(achievement_id)

        return False

    def complete_achievement(self, achievement_id: str) -> bool:
        """Завершение достижения"""
        achievement = self.achievements.get(achievement_id)
        if not achievement:
            return False

        if achievement_id in self.player_achievements:
            return False

        # Отметка достижения как завершенного
        self.player_achievements[achievement_id] = {
            "completed": True,
            "completion_date": datetime.now(),
            "progress": achievement.current,
        }

        return True

    def _unlock_stage(self, achievement_id: str, stage: int):
        """Разблокировка этапа достижения"""
        achievement = self.achievements.get(achievement_id)
        if not achievement:
            return

        if not achievement.completed_stages:
            achievement.completed_stages = []

        if stage not in achievement.completed_stages:
            achievement.completed_stages.append(stage)

    def get_achievement_message(self, achievement_id: str) -> str:
        """Форматирование сообщения о достижении"""
        achievement = self.achievements.get(achievement_id)
        if not achievement:
            return ""

        rewards_text = []
        for reward_type, amount in achievement.reward.items():
            if reward_type == "experience":
                rewards_text.append(f"⭐ {amount} опыта")
            elif reward_type == "energy":
                rewards_text.append(f"💪 {amount} энергии")
            elif reward_type == "money":
                rewards_text.append(f"💰 {amount} монет")
            elif reward_type == "skill_points":
                rewards_text.append(f"🎯 {amount} очков навыков")

        message = (
            f"🏆 *Новое достижение!*\n\n"
            f"{achievement.icon} *{achievement.title}*\n"
            f"{achievement.description}\n\n"
            f"*Награды:*\n"
            f"{' | '.join(rewards_text)}"
        )
        return message

    def get_player_achievements(self, player_id: str) -> Dict:
        """Получение достижений игрока"""
        return {
            "completed": [
                achievement_id
                for achievement_id, data in self.player_achievements.items()
                if data.get("completed")
            ],
            "in_progress": [
                achievement_id
                for achievement_id, data in self.player_achievements.items()
                if not data.get("completed")
            ],
            "available": [
                achievement_id
                for achievement_id, achievement in self.achievements.items()
                if achievement_id not in self.player_achievements
            ],
        }

    def get_achievement_progress(self, achievement_id: str) -> Dict:
        """Получение прогресса достижения"""
        achievement = self.achievements.get(achievement_id)
        if not achievement:
            return {}

        player_achievement = self.player_achievements.get(achievement_id, {})
        return {
            "current": achievement.current,
            "required": achievement.required,
            "stages": achievement.stages,
            "completed_stages": achievement.completed_stages,
            "is_completed": player_achievement.get("completed", False),
        }


def format_achievement_message(achievement: Achievement) -> str:
    """
    Форматирует сообщение о получении достижения.

    Args:
        achievement: Объект достижения

    Returns:
        str: Отформатированное сообщение
    """
    rewards_text = []
    for reward_type, amount in achievement.reward.items():
        if reward_type == "experience":
            rewards_text.append(f"⭐ {amount} опыта")
        elif reward_type == "energy":
            rewards_text.append(f"💪 {amount} энергии")
        elif reward_type == "money":
            rewards_text.append(f"💰 {amount} монет")
        elif reward_type == "skill_points":
            rewards_text.append(f"🎯 {amount} очков навыков")

    message = (
        f"🏆 *Новое достижение!*\n\n"
        f"{achievement.icon} *{achievement.title}*\n"
        f"{achievement.description}\n\n"
        f"*Награды:*\n"
        f"{' | '.join(rewards_text)}"
    )
    return message


# Словарь всех достижений
ACHIEVEMENTS = {
    "case_solving": {
        "first_case": Achievement(
            id="first_case",
            title="Первое дело",
            description="Раскройте свое первое дело",
            icon="🔍",
            reward={"experience": 100, "money": 500},
            category="case_solving",
        ),
        "perfect_solve": Achievement(
            id="perfect_solve",
            title="Идеальное расследование",
            description="Раскройте дело без ошибок",
            icon="✨",
            reward={"experience": 200, "money": 1000, "skill_points": 2},
            category="case_solving",
        ),
        "master_detective": Achievement(
            id="master_detective",
            title="Мастер-детектив",
            description="Раскройте 10 дел",
            icon="👑",
            reward={"experience": 1000, "money": 5000, "skill_points": 5},
            category="case_solving",
        ),
        "speed_demon": Achievement(
            id="speed_demon",
            title="Скоростное расследование",
            description="Раскройте дело менее чем за 30 минут",
            icon="⚡",
            reward={"experience": 300, "money": 1500, "energy": 50},
            category="case_solving",
        ),
    },
    "skills": {
        "forensic_expert": Achievement(
            id="forensic_expert",
            title="Криминалист-эксперт",
            description="Достигните 10 уровня в навыке криминалистики",
            icon="🔬",
            reward={"experience": 500, "money": 2000, "skill_points": 3},
            category="skills",
        ),
        "psychology_master": Achievement(
            id="psychology_master",
            title="Мастер психологии",
            description="Достигните 10 уровня в навыке психологии",
            icon="🧠",
            reward={"experience": 500, "money": 2000, "skill_points": 3},
            category="skills",
        ),
        "detective_pro": Achievement(
            id="detective_pro",
            title="Профессиональный детектив",
            description="Достигните 10 уровня в навыке детектива",
            icon="🕵️",
            reward={"experience": 500, "money": 2000, "skill_points": 3},
            category="skills",
        ),
    },
    "exploration": {
        "location_master": Achievement(
            id="location_master",
            title="Исследователь",
            description="Исследуйте все локации в деле",
            icon="🗺️",
            reward={"experience": 200, "money": 1000},
            category="exploration",
        ),
        "evidence_collector": Achievement(
            id="evidence_collector",
            title="Собиратель улик",
            description="Соберите все улики в деле",
            icon="📦",
            reward={"experience": 200, "money": 1000},
            category="exploration",
        ),
        "interrogation_pro": Achievement(
            id="interrogation_pro",
            title="Мастер допроса",
            description="Допросите всех подозреваемых",
            icon="💬",
            reward={"experience": 200, "money": 1000},
            category="exploration",
        ),
    },
    "special": {
        "night_owl": Achievement(
            id="night_owl",
            title="Ночная сова",
            description="Раскройте дело в ночное время",
            icon="🦉",
            reward={"experience": 300, "money": 1500},
            category="special",
            hidden=True,
        ),
        "lucky_detective": Achievement(
            id="lucky_detective",
            title="Счастливчик",
            description="Найдите улику с первого раза",
            icon="🍀",
            reward={"experience": 200, "money": 1000},
            category="special",
            hidden=True,
        ),
        "social_butterfly": Achievement(
            id="social_butterfly",
            title="Социальная бабочка",
            description="Установите хорошие отношения со всеми подозреваемыми",
            icon="🦋",
            reward={"experience": 300, "money": 1500},
            category="special",
            hidden=True,
        ),
    },
}


def check_achievements(
    user: Any, action: str, context: Dict[str, Any]
) -> List[Achievement]:
    """
    Проверяет условия и выдает достижения.

    Args:
        user: Объект пользователя
        action: Тип действия
        context: Контекст действия

    Returns:
        List[Achievement]: Список полученных достижений
    """
    unlocked_achievements = []

    # Проверяем достижения за решение дел
    if action == "case_completed":
        cases_solved = user.stats.cases_solved
        if cases_solved == 1:
            unlocked_achievements.append(ACHIEVEMENTS["case_solving"]["first_case"])

        if cases_solved >= 10:
            unlocked_achievements.append(
                ACHIEVEMENTS["case_solving"]["master_detective"]
            )

        if context.get("perfect_solve", False):
            unlocked_achievements.append(ACHIEVEMENTS["case_solving"]["perfect_solve"])

        if context.get("completion_time", 0) < 30:  # в минутах
            unlocked_achievements.append(ACHIEVEMENTS["case_solving"]["speed_demon"])

    # Проверяем достижения за навыки
    elif action == "skill_level_up":
        skill_name = context.get("skill_name")
        new_level = context.get("new_level")

        if new_level >= 10:
            if skill_name == "forensic":
                unlocked_achievements.append(ACHIEVEMENTS["skills"]["forensic_expert"])
            elif skill_name == "psychology":
                unlocked_achievements.append(
                    ACHIEVEMENTS["skills"]["psychology_master"]
                )
            elif skill_name == "detective":
                unlocked_achievements.append(ACHIEVEMENTS["skills"]["detective_pro"])

    # Проверяем достижения за исследование
    elif action == "location_explored":
        if context.get("all_locations_explored", False):
            unlocked_achievements.append(ACHIEVEMENTS["exploration"]["location_master"])

    elif action == "evidence_found":
        if context.get("all_evidence_collected", False):
            unlocked_achievements.append(
                ACHIEVEMENTS["exploration"]["evidence_collector"]
            )

    elif action == "suspect_interviewed":
        if context.get("all_suspects_interviewed", False):
            unlocked_achievements.append(
                ACHIEVEMENTS["exploration"]["interrogation_pro"]
            )

    # Проверяем специальные достижения
    elif action == "case_started":
        if context.get("time_of_day", "").lower() == "night":
            unlocked_achievements.append(ACHIEVEMENTS["special"]["night_owl"])

    elif action == "evidence_found":
        if context.get("found_on_first_try", False):
            unlocked_achievements.append(ACHIEVEMENTS["special"]["lucky_detective"])

    elif action == "case_completed":
        if context.get("good_relationships_with_all", False):
            unlocked_achievements.append(ACHIEVEMENTS["special"]["social_butterfly"])

    # Устанавливаем время получения для новых достижений
    for achievement in unlocked_achievements:
        if not achievement.unlocked_at:
            achievement.unlocked_at = datetime.utcnow()

    return unlocked_achievements
