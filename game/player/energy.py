"""Система управления энергией игрока."""

from datetime import datetime, timedelta, timezone
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

from bot.database.models.user import User
from game.player.skills import SkillType


class ActionType(Enum):
    """Типы действий, требующих энергии."""

    START_INVESTIGATION = auto()
    CHANGE_LOCATION = auto()
    INTERROGATE_SUSPECT = auto()
    ANALYZE_EVIDENCE = auto()
    SEARCH_LOCATION = auto()


class EnergyManager:
    """Менеджер энергии игрока."""

    # Базовые затраты энергии на действия
    ACTION_COSTS: Dict[ActionType, int] = {
        ActionType.START_INVESTIGATION: 20,
        ActionType.CHANGE_LOCATION: 5,
        ActionType.INTERROGATE_SUSPECT: 10,
        ActionType.ANALYZE_EVIDENCE: 8,
        ActionType.SEARCH_LOCATION: 7,
    }

    # Базовый коэффициент восстановления энергии (в единицах в час)
    BASE_RESTORE_RATE: float = 10.0

    # Максимальная энергия по умолчанию
    BASE_MAX_ENERGY: int = 100

    # Действия, не требующие энергии
    FREE_ACTIONS: List[ActionType] = [
        ActionType.CHANGE_LOCATION,  # Перемещение между локациями бесплатно
    ]

    def __init__(self):
        """Инициализация менеджера энергии."""
        self._energy_planner = EnergyPlanner()

    async def calculate_current_energy(self, user: User) -> int:
        """
        Рассчитывает текущую энергию пользователя с учетом восстановления.

        Args:
            user: Пользователь

        Returns:
            int: Текущая энергия
        """
        if user.energy >= user.max_energy:
            return user.max_energy

        # Рассчитываем время с последнего обновления
        time_passed = datetime.now(timezone.utc) - user.last_energy_update
        hours_passed = time_passed.total_seconds() / 3600

        # Рассчитываем восстановленную энергию
        restore_rate = self._calculate_restore_rate(user)
        restored_energy = int(hours_passed * restore_rate)

        # Обновляем энергию
        new_energy = min(user.energy + restored_energy, user.max_energy)
        user.energy = new_energy
        user.last_energy_update = datetime.now(timezone.utc)

        return new_energy

    async def can_perform_action(
        self, user: User, action_type: ActionType
    ) -> Tuple[bool, Optional[str]]:
        """
        Проверяет, может ли пользователь выполнить действие.

        Args:
            user: Пользователь
            action_type: Тип действия

        Returns:
            Tuple[bool, Optional[str]]: (Можно ли выполнить действие, Сообщение об ошибке)
        """
        if action_type in self.FREE_ACTIONS:
            return True, None

        current_energy = await self.calculate_current_energy(user)
        cost = self._calculate_action_cost(user, action_type)

        if current_energy < cost:
            return (
                False,
                f"Недостаточно энергии. Требуется: {cost}, Доступно: {current_energy}",
            )

        return True, None

    async def consume_energy(self, user: User, action_type: ActionType) -> bool:
        """
        Потребляет энергию для выполнения действия.

        Args:
            user: Пользователь
            action_type: Тип действия

        Returns:
            bool: Успешно ли потреблена энергия
        """
        if action_type in self.FREE_ACTIONS:
            return True

        can_perform, _ = await self.can_perform_action(user, action_type)
        if not can_perform:
            return False

        cost = self._calculate_action_cost(user, action_type)
        user.energy -= cost
        user.last_energy_update = datetime.now(timezone.utc)

        return True

    async def restore_energy(self, user: User, amount: int) -> int:
        """
        Восстанавливает энергию пользователя.

        Args:
            user: Пользователь
            amount: Количество энергии для восстановления

        Returns:
            int: Фактически восстановленная энергия
        """
        current_energy = await self.calculate_current_energy(user)
        max_restore = user.max_energy - current_energy
        actual_restore = min(amount, max_restore)

        user.energy += actual_restore
        user.last_energy_update = datetime.now(timezone.utc)

        return actual_restore

    def get_next_full_energy_time(self, user: User) -> datetime:
        """
        Рассчитывает время полного восстановления энергии.

        Args:
            user: Пользователь

        Returns:
            datetime: Время полного восстановления
        """
        current_energy = user.energy
        if current_energy >= user.max_energy:
            return datetime.now(timezone.utc)

        restore_rate = self._calculate_restore_rate(user)
        energy_needed = user.max_energy - current_energy
        hours_needed = energy_needed / restore_rate

        return user.last_energy_update + timedelta(hours=hours_needed)

    def _calculate_action_cost(self, user: User, action_type: ActionType) -> int:
        """
        Рассчитывает стоимость действия с учетом навыков.

        Args:
            user: Пользователь
            action_type: Тип действия

        Returns:
            int: Стоимость действия
        """
        base_cost = self.ACTION_COSTS[action_type]

        # Применяем скидки за навыки
        skill_discount = self._calculate_skill_discount(user, action_type)

        # Применяем бонусы за достижения
        achievement_bonus = self._calculate_achievement_bonus(user, action_type)

        final_cost = int(base_cost * (1 - skill_discount) * (1 - achievement_bonus))
        return max(1, final_cost)  # Минимальная стоимость - 1

    def _calculate_restore_rate(self, user: User) -> float:
        """
        Рассчитывает скорость восстановления энергии.

        Args:
            user: Пользователь

        Returns:
            float: Скорость восстановления (в единицах в час)
        """
        rate = self.BASE_RESTORE_RATE

        # Бонусы за достижения
        achievement_bonus = self._calculate_achievement_bonus(user, None)
        rate *= 1 + achievement_bonus

        # Бонусы за уровень
        level_bonus = (user.level - 1) * 0.1  # +10% за каждый уровень
        rate *= 1 + level_bonus

        return rate

    def _calculate_skill_discount(self, user: User, action_type: ActionType) -> float:
        """
        Рассчитывает скидку на стоимость действия за навыки.

        Args:
            user: Пользователь
            action_type: Тип действия

        Returns:
            float: Скидка (от 0 до 1)
        """
        skill_mapping = {
            ActionType.ANALYZE_EVIDENCE: SkillType.FORENSIC,
            ActionType.INTERROGATE_SUSPECT: SkillType.PSYCHOLOGY,
            ActionType.SEARCH_LOCATION: SkillType.DETECTIVE,
        }

        if action_type not in skill_mapping:
            return 0.0

        skill_type = skill_mapping[action_type]
        skill_level = getattr(user, f"{skill_type.value}_skill")

        # Максимальная скидка 50% при уровне навыка 100
        return min(0.5, skill_level / 200)

    def _calculate_achievement_bonus(
        self, user: User, action_type: Optional[ActionType] = None
    ) -> float:
        """
        Рассчитывает бонусы за достижения.

        Args:
            user: Пользователь
            action_type: Тип действия (опционально)

        Returns:
            float: Бонус (от 0 до 1)
        """
        bonus = 0.0

        # Проверяем достижения в статистике пользователя
        if "achievements" in user.stats:
            achievements = user.stats["achievements"]

            # Бонусы за общие достижения
            if "energy_master" in achievements:
                bonus += 0.2  # +20% к восстановлению

            # Бонусы за специфические достижения
            if action_type:
                if f"{action_type.name.lower()}_expert" in achievements:
                    bonus += 0.15  # +15% скидка на конкретное действие

        return bonus


class EnergyPlanner:
    """Планировщик оптимального использования энергии."""

    def __init__(self):
        """Инициализация планировщика."""
        self._action_priorities = {
            ActionType.START_INVESTIGATION: 1,
            ActionType.ANALYZE_EVIDENCE: 2,
            ActionType.INTERROGATE_SUSPECT: 3,
            ActionType.SEARCH_LOCATION: 4,
            ActionType.CHANGE_LOCATION: 5,
        }

    async def get_optimal_action_sequence(
        self, user: User, available_actions: List[ActionType]
    ) -> List[ActionType]:
        """
        Возвращает оптимальную последовательность действий.

        Args:
            user: Пользователь
            available_actions: Доступные действия

        Returns:
            List[ActionType]: Оптимальная последовательность действий
        """
        # Сортируем действия по приоритету
        sorted_actions = sorted(
            available_actions,
            key=lambda x: self._action_priorities.get(x, float("inf")),
        )

        # Фильтруем действия, которые можно выполнить
        energy_manager = EnergyManager()
        optimal_sequence = []

        for action in sorted_actions:
            can_perform, _ = await energy_manager.can_perform_action(user, action)
            if can_perform:
                optimal_sequence.append(action)

        return optimal_sequence

    def estimate_energy_recovery_time(
        self, user: User, target_energy: int
    ) -> timedelta:
        """
        Оценивает время восстановления до целевого уровня энергии.

        Args:
            user: Пользователь
            target_energy: Целевой уровень энергии

        Returns:
            timedelta: Ожидаемое время восстановления
        """
        energy_manager = EnergyManager()
        current_energy = user.energy
        restore_rate = energy_manager._calculate_restore_rate(user)

        energy_needed = target_energy - current_energy
        if energy_needed <= 0:
            return timedelta(0)

        hours_needed = energy_needed / restore_rate
        return timedelta(hours=hours_needed)
