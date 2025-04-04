"""Модуль для управления сюжетом расследования."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

from game.investigation.case import Case
from services.claude_service.claude_service import ClaudeService
from game.player.skills import SkillType
from game.player.energy import ActionType
from bot.database.models.investigation import Investigation, InvestigationStage


class InvestigationNodeType(Enum):
    """Типы узлов расследования."""

    LOCATION = auto()
    INTERROGATION = auto()
    EVIDENCE_ANALYSIS = auto()
    DECISION = auto()
    CONCLUSION = auto()


class InvestigationOutcome(Enum):
    """Возможные исходы расследования."""

    SUCCESS = auto()
    PARTIAL_SUCCESS = auto()
    FAILURE = auto()
    CRITICAL_FAILURE = auto()


@dataclass
class InvestigationNode:
    """Узел расследования."""

    id: str
    type: InvestigationNodeType
    title: str
    description: str
    available_actions: List[str]
    required_skills: Dict[SkillType, int]
    evidence_required: List[str]
    suspects_required: List[str]
    next_nodes: List[str]
    consequences: Dict[str, str]
    success_threshold: float
    time_limit: Optional[int] = None


class Storyteller:
    """Класс для управления сюжетом расследования."""

    def __init__(self, case: Case, claude_service: ClaudeService):
        """
        Инициализация рассказчика.

        Args:
            case: Текущее расследование
            claude_service: Сервис для работы с Claude API
        """
        self._case = case
        self._claude_service = claude_service
        self._logger = logging.getLogger(__name__)
        self._current_node: Optional[InvestigationNode] = None
        self._visited_nodes: List[str] = []
        self._collected_evidence: List[str] = []
        self._interrogated_suspects: List[str] = []
        self._player_choices: List[Dict[str, Any]] = []
        self._start_time = datetime.now(timezone.utc)

    async def initialize_story(self) -> None:
        """Инициализация сюжета расследования."""
        # Получаем начальный узел из шаблона расследования
        self._current_node = await self._get_node_by_id(
            self._case.template.initial_node_id
        )
        self._visited_nodes.append(self._current_node.id)

    async def get_available_actions(self) -> List[str]:
        """
        Получает список доступных действий в текущем узле.

        Returns:
            List[str]: Список доступных действий
        """
        if not self._current_node:
            return []

        # Проверяем требования к навыкам
        if not self._check_skill_requirements():
            return []

        # Проверяем требования к уликам
        if not self._check_evidence_requirements():
            return []

        # Проверяем требования к допросам
        if not self._check_suspect_requirements():
            return []

        return self._current_node.available_actions

    async def process_action(
        self, action: str, context: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[InvestigationNode]]:
        """
        Обрабатывает действие игрока.

        Args:
            action: Выбранное действие
            context: Контекст действия

        Returns:
            Tuple[bool, str, Optional[InvestigationNode]]:
                (успешность действия, сообщение, следующий узел)
        """
        if not self._current_node:
            return False, "Нет активного узла расследования", None

        if action not in self._current_node.available_actions:
            return False, "Это действие недоступно", None

        # Оцениваем действие
        success, message = await self._evaluate_action(action, context)

        # Обновляем прогресс
        self._update_progress(action, success, context)

        # Определяем следующий узел
        next_node = await self._determine_next_node(action, success)

        return success, message, next_node

    async def _evaluate_action(
        self, action: str, context: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Оценивает успешность действия игрока.

        Args:
            action: Выбранное действие
            context: Контекст действия

        Returns:
            Tuple[bool, str]: (успешность, сообщение)
        """
        # Создаем контекст для оценки
        evaluation_context = {
            "action": action,
            "node_type": self._current_node.type,
            "player_skills": self._case.user.skills,
            "collected_evidence": self._collected_evidence,
            "interrogated_suspects": self._interrogated_suspects,
            "context": context,
        }

        # Получаем оценку от Claude
        response = await self._claude_service.generate_investigation_step(
            evaluation_context, "evaluate_action"
        )

        evaluation = response.get("evaluation", {})
        success = evaluation.get("success", False)
        message = evaluation.get("message", "")

        return success, message

    async def _determine_next_node(
        self, action: str, success: bool
    ) -> Optional[InvestigationNode]:
        """
        Определяет следующий узел на основе действия и его результата.

        Args:
            action: Выбранное действие
            success: Успешность действия

        Returns:
            Optional[InvestigationNode]: Следующий узел
        """
        # Получаем ID следующего узла из последствий
        next_node_id = self._current_node.consequences.get(
            f"{action}_{'success' if success else 'failure'}"
        )

        if not next_node_id:
            return None

        # Получаем следующий узел
        next_node = await self._get_node_by_id(next_node_id)
        if next_node:
            self._current_node = next_node
            self._visited_nodes.append(next_node.id)

        return next_node

    def _update_progress(
        self, action: str, success: bool, context: Dict[str, Any]
    ) -> None:
        """
        Обновляем прогресс расследования.

        Args:
            action: Выбранное действие
            success: Успешность действия
            context: Контекст действия
        """
        # Обновляем собранные улики
        if "evidence" in context:
            self._collected_evidence.extend(context["evidence"])

        # Обновляем допрошенных подозреваемых
        if "suspects" in context:
            self._interrogated_suspects.extend(context["suspects"])

        # Сохраняем выбор игрока
        self._player_choices.append(
            {
                "action": action,
                "success": success,
                "timestamp": datetime.now(timezone.utc),
                "context": context,
            }
        )

    def _check_skill_requirements(self) -> bool:
        """
        Проверяет соответствие навыков игрока требованиям узла.

        Returns:
            bool: Соответствие требованиям
        """
        for skill, required_level in self._current_node.required_skills.items():
            if self._case.user.get_skill_level(skill) < required_level:
                return False
        return True

    def _check_evidence_requirements(self) -> bool:
        """
        Проверяет наличие необходимых улик.

        Returns:
            bool: Соответствие требованиям
        """
        return all(
            evidence in self._collected_evidence
            for evidence in self._current_node.evidence_required
        )

    def _check_suspect_requirements(self) -> bool:
        """
        Проверяет наличие необходимых допросов.

        Returns:
            bool: Соответствие требованиям
        """
        return all(
            suspect in self._interrogated_suspects
            for suspect in self._current_node.suspects_required
        )

    async def _get_node_by_id(self, node_id: str) -> Optional[InvestigationNode]:
        """
        Получает узел по его ID.

        Args:
            node_id: ID узла

        Returns:
            Optional[InvestigationNode]: Узел расследования
        """
        # Получаем узел из шаблона расследования
        node_data = self._case.template.nodes.get(node_id)
        if not node_data:
            return None

        return InvestigationNode(**node_data)

    async def check_investigation_completion(self) -> Optional[InvestigationOutcome]:
        """
        Проверяет условия завершения расследования.

        Returns:
            Optional[InvestigationOutcome]: Исход расследования
        """
        if not self._current_node:
            return None

        # Проверяем, является ли текущий узел заключительным
        if self._current_node.type != InvestigationNodeType.CONCLUSION:
            return None

        # Рассчитываем эффективность игрока
        effectiveness = self._calculate_player_effectiveness()

        # Определяем исход
        if effectiveness >= self._current_node.success_threshold:
            return InvestigationOutcome.SUCCESS
        elif effectiveness >= self._current_node.success_threshold * 0.7:
            return InvestigationOutcome.PARTIAL_SUCCESS
        elif effectiveness >= self._current_node.success_threshold * 0.4:
            return InvestigationOutcome.FAILURE
        else:
            return InvestigationOutcome.CRITICAL_FAILURE

    def _calculate_player_effectiveness(self) -> float:
        """
        Рассчитывает эффективность игрока.

        Returns:
            float: Эффективность (0.0 - 1.0)
        """
        effectiveness = 0.0
        total_weight = 0

        # Оцениваем успешность действий
        for choice in self._player_choices:
            weight = self._get_action_weight(choice["action"])
            effectiveness += weight * (1.0 if choice["success"] else 0.0)
            total_weight += weight

        # Учитываем собранные улики
        evidence_ratio = len(self._collected_evidence) / len(
            self._case.template.required_evidence
        )
        effectiveness += evidence_ratio * 0.3

        # Учитываем допрошенных подозреваемых
        suspect_ratio = len(self._interrogated_suspects) / len(
            self._case.template.required_suspects
        )
        effectiveness += suspect_ratio * 0.3

        # Нормализуем результат
        return min(1.0, effectiveness / (total_weight + 0.6))

    def _get_action_weight(self, action: str) -> float:
        """
        Определяет вес действия для расчета эффективности.

        Args:
            action: Действие

        Returns:
            float: Вес действия
        """
        weights = {
            "search": 0.2,
            "interrogate": 0.3,
            "analyze": 0.3,
            "decide": 0.4,
            "conclude": 0.5,
        }
        return weights.get(action, 0.1)

    def get_investigation_summary(self) -> Dict[str, Any]:
        """
        Получаем сводку по расследованию.

        Returns:
            Dict[str, Any]: Сводка расследования
        """
        return {
            "current_node": self._current_node.id if self._current_node else None,
            "visited_nodes": self._visited_nodes,
            "collected_evidence": self._collected_evidence,
            "interrogated_suspects": self._interrogated_suspects,
            "player_choices": self._player_choices,
            "duration": (datetime.now(timezone.utc) - self._start_time).total_seconds(),
        }
