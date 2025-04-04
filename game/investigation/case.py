import logging
import random
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from bot.database.models.investigation import (
    Investigation,
    InvestigationStage,
    InvestigationStatus,
    PlayerAction,
)
from bot.database.repositories.investigation_repository import InvestigationRepository
from bot.core.config import config
from bot.database.models.user import User
from services.claude_service.claude_service import ClaudeService
from game.player.skills import SkillType
from game.player.energy import ActionType

logger = logging.getLogger(__name__)


class CaseStatus:
    """Статусы расследования."""

    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class CaseStage:
    """Этапы расследования."""

    INITIAL = "initial"
    EXAMINING_SCENE = "examining_scene"
    COLLECTING_EVIDENCE = "collecting_evidence"
    INTERVIEWING_WITNESSES = "interviewing_witnesses"
    ANALYZING_EVIDENCE = "analyzing_evidence"
    INTERROGATING_SUSPECTS = "interrogating_suspects"
    MAKING_DEDUCTION = "making_deduction"
    COMPLETED = "completed"
    FAILED = "failed"


class CaseOutcome:
    """Результаты расследования."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"


class Case:
    """Класс для управления расследованием."""

    def __init__(
        self,
        investigation: Investigation,
        repository: InvestigationRepository,
        claude_service: ClaudeService,
    ):
        """Инициализация расследования."""
        self.investigation = investigation
        self.repository = repository
        self.claude_service = claude_service
        self.logger = logging.getLogger(f"{__name__}.{investigation.id}")

        # Инициализация списков
        self.evidence: List[Dict[str, Any]] = []
        self.suspects: List[Dict[str, Any]] = []
        self.witnesses: List[Dict[str, Any]] = []

        # Основные параметры
        self.id = investigation.id
        self.title = investigation.title
        self.description = investigation.description
        self.difficulty = investigation.difficulty
        self.user = investigation.user

        # Временные метки
        self.created_at = datetime.utcnow()
        self.last_action_at = self.created_at
        self.completed_at: Optional[datetime] = None

        # Локации
        self.current_location: str = "start"
        self.available_locations: List[Dict[str, Any]] = []
        self.visited_locations: List[str] = ["start"]

        # Игровой прогресс
        self.current_stage = CaseStage.INITIAL
        self.player_decisions: List[Dict[str, Any]] = []
        self.story_branches: Dict[str, List[str]] = {}
        self.current_branch = "main"

        # Статистика
        self.correct_deductions = 0
        self.wrong_deductions = 0
        self.evidence_analyzed = 0
        self.witnesses_interviewed = 0
        self.suspects_interrogated = 0

        # Состояние
        self.is_active = True
        self.outcome: Optional[str] = None

    async def initialize(self) -> None:
        """Асинхронная инициализация расследования"""
        await self._initialize_story()

    async def _initialize_story(self) -> None:
        """Инициализирует начальное состояние расследования"""
        try:
            initial_prompt = (
                f"Создай детективную историю сложности {self.difficulty}/5 "
                f"с названием '{self.title}'. История должна включать: "
                "место преступления, улики, свидетелей и подозреваемых."
            )
            story_data = await self.claude_service.generate_story(initial_prompt)

            if not story_data or not isinstance(story_data, dict):
                raise ValueError("Неверный формат данных истории")

            self.story_branches["main"] = story_data.get("story_points", [])
            self.evidence.extend(story_data.get("evidence", []))
            self.suspects.extend(story_data.get("suspects", []))
            self.witnesses.extend(story_data.get("witnesses", []))

        except Exception as e:
            logger.error(f"Ошибка при инициализации истории: {e}")
            raise RuntimeError("Не удалось инициализировать расследование")

    async def process_action(self, action: str) -> Tuple[str, List[str]]:
        """
        Обрабатывает действие игрока.

        Args:
            action: Действие игрока

        Returns:
            Tuple[str, List[str]]: (описание результата, доступные действия)
        """
        # Проверяем, доступно ли действие
        if action not in self.investigation.current_state["current_options"]:
            return "Это действие недоступно в текущей ситуации.", []

        # Генерируем результат действия
        context = self._prepare_context()
        result = await self.claude_service.generate_investigation_step(context, action)

        # Обновляем состояние
        await self._update_state(action, result)

        # Получаем новые доступные действия
        new_options = await self._get_available_actions()

        return result["description"], new_options

    def _prepare_context(self) -> Dict[str, Any]:
        """Подготавливает контекст для генерации."""
        return {
            "title": self.investigation.title,
            "difficulty": self.investigation.difficulty,
            "current_state": self.investigation.current_state,
            "story_nodes": self.investigation.story_nodes,
            "progress": self.investigation.progress,
        }

    async def _update_state(self, action: str, result: Dict[str, Any]) -> None:
        """Обновляет состояние расследования."""
        # Создаем действие игрока
        player_action = PlayerAction(
            action=action,
            timestamp=datetime.utcnow(),
            result=result.get("description"),
            evidence_found=result.get("new_evidence", []),
            clues_discovered=result.get("new_clues", []),
        )

        # Обновляем состояние
        state_update = {
            "discovered_clues": list(
                set(
                    self.investigation.current_state["discovered_clues"]
                    + result.get("new_clues", [])
                )
            ),
            "player_actions": self.investigation.current_state["player_actions"]
            + [player_action],
            "current_options": result.get("next_actions", []),
        }

        # Обновляем в репозитории
        await self.repository.update_investigation_state(
            self.investigation.id, state_update
        )

        # Проверяем завершение
        if result.get("consequences", []):
            await self._check_completion(result["consequences"])

    async def _get_available_actions(self) -> List[str]:
        """Получает доступные действия."""
        # Получаем текущий узел истории
        current_node = self._get_current_node()

        # Базовые действия
        actions = current_node.get("options", [])

        # Добавляем специальные действия на основе состояния
        if (
            self.investigation.current_state["stage"]
            == InvestigationStage.INVESTIGATION
        ):
            actions.extend(["analyze_evidence", "review_notes"])
        elif (
            self.investigation.current_state["stage"]
            == InvestigationStage.INTERROGATION
        ):
            actions.extend(["prepare_questions", "review_testimony"])

        return list(set(actions))  # Убираем дубликаты

    def _get_current_node(self) -> Dict[str, Any]:
        """Получает текущий узел истории."""
        # Определяем текущий узел на основе последнего действия
        last_action = (
            self.investigation.current_state["player_actions"][-1]
            if self.investigation.current_state["player_actions"]
            else None
        )

        if last_action:
            # Ищем узел, соответствующий последнему действию
            for node_id, node in self.investigation.story_nodes.items():
                if last_action.action in node.get("options", []):
                    return node

        # Если узел не найден, возвращаем начальный
        return self.investigation.story_nodes.get("start", {})

    async def _check_completion(self, consequences: List[str]) -> None:
        """Проверяет условия завершения расследования."""
        # Проверяем наличие ключевых улик
        required_evidence = self.investigation.story_nodes.get("conclusion", {}).get(
            "evidence", []
        )
        has_required_evidence = all(
            evidence in self.investigation.current_state["discovered_clues"]
            for evidence in required_evidence
        )

        # Проверяем допрос всех подозреваемых
        required_suspects = self.investigation.story_nodes.get("conclusion", {}).get(
            "suspects", []
        )
        has_interrogated_all = all(
            suspect in self.investigation.current_state["interrogated_suspects"]
            for suspect in required_suspects
        )

        # Если все условия выполнены, завершаем расследование
        if has_required_evidence and has_interrogated_all:
            await self.repository.update_investigation_status(
                self.investigation.id, InvestigationStatus.COMPLETED
            )
            self.logger.info("Расследование завершено успешно")

    async def get_current_state(self) -> Dict[str, Any]:
        """Возвращает текущее состояние расследования."""
        return {
            "title": self.investigation.title,
            "status": self.investigation.status,
            "difficulty": self.investigation.difficulty,
            "current_state": self.investigation.current_state,
            "available_actions": await self._get_available_actions(),
            "progress": self._calculate_progress(),
        }

    def _calculate_progress(self) -> float:
        """Рассчитывает прогресс расследования."""
        total_evidence = len(
            self.investigation.story_nodes.get("conclusion", {}).get("evidence", [])
        )
        total_suspects = len(
            self.investigation.story_nodes.get("conclusion", {}).get("suspects", [])
        )

        if total_evidence + total_suspects == 0:
            return 0.0

        evidence_progress = (
            len(self.investigation.current_state["discovered_clues"]) / total_evidence
        )
        suspects_progress = (
            len(self.investigation.current_state["interrogated_suspects"])
            / total_suspects
        )

        return (evidence_progress + suspects_progress) / 2

    async def start_investigation(self) -> Dict[str, Any]:
        """Начинает новое расследование"""
        if not self.is_active:
            raise ValueError("Расследование уже завершено")

        self.current_stage = CaseStage.EXAMINING_SCENE

        scene_description = await self.claude_service.generate_scene_description(
            self.title, self.description
        )

        return {
            "message": scene_description,
            "available_actions": self._get_available_actions(),
        }

    async def examine_scene(self, focus_area: str) -> Dict[str, Any]:
        """Осмотр места преступления"""
        if self.current_stage != CaseStage.EXAMINING_SCENE:
            raise ValueError("Недоступно на текущем этапе")

        scene_details = (
            await self.claude_service.generate_scene_examination(self.title, focus_area)
            or {}
        )  # Инициализируем пустым словарем, если None

        # Шанс найти новую улику (30% по умолчанию)
        if random.random() < 0.3:
            new_evidence = await self._generate_new_evidence(focus_area)
            self.evidence.append(new_evidence)
            scene_details["found_evidence"] = new_evidence

        return scene_details

    async def collect_evidence(self, evidence_id: int) -> Dict[str, Any]:
        """Сбор улик"""
        evidence = self._find_evidence(evidence_id)
        if not evidence:
            raise ValueError("Улика не найдена")

        evidence["collected"] = True
        self.evidence_analyzed += 1

        # Используем описание улики или генерируем новое
        evidence_description = evidence.get("description", "Неизвестная улика")
        analysis_result = await self.claude_service.analyze_evidence(
            self.title, evidence_description
        )

        self._update_story_branch(analysis_result.get("significance", {}))
        return analysis_result

    async def interview_witness(
        self, witness_id: int, questions: List[str]
    ) -> Dict[str, Any]:
        """Опрос свидетеля"""
        witness = self._find_witness(witness_id)
        if not witness:
            raise ValueError("Свидетель не найден")

        self.witnesses_interviewed += 1

        interview_result = (
            await self.claude_service.generate_witness_response(
                self.title, witness.get("name", "Неизвестный свидетель"), questions
            )
            or {}
        )

        self._update_story_branch(interview_result.get("implications", {}))
        return interview_result

    async def interrogate_suspect(
        self, suspect_id: int, approach: str
    ) -> Dict[str, Any]:
        """Допрос подозреваемого"""
        suspect = self._find_suspect(suspect_id)
        if not suspect:
            raise ValueError("Подозреваемый не найден")

        self.suspects_interrogated += 1

        interrogation_result = (
            await self.claude_service.generate_suspect_response(
                self.title, suspect.get("name", "Неизвестный подозреваемый"), approach
            )
            or {}
        )

        self._update_story_branch(interrogation_result.get("reaction", {}))
        return interrogation_result

    async def make_deduction(
        self, deduction: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Проверяет правильность выводов игрока"""
        if self.current_stage != CaseStage.MAKING_DEDUCTION:
            raise ValueError("Сейчас нельзя делать выводы")

        evaluation = (
            await self.claude_service.evaluate_deduction(
                self.title, deduction, self.story_branches.get(self.current_branch, [])
            )
            or {}
        )

        is_correct = evaluation.get("accuracy", 0) > config.DEDUCTION_THRESHOLD
        if is_correct:
            self.correct_deductions += 1
        else:
            self.wrong_deductions += 1

        return is_correct, evaluation

    async def complete_investigation(self) -> Dict[str, Any]:
        """Завершает расследование и подсчитывает награды"""
        if not self.is_active:
            raise ValueError("Расследование уже завершено")

        self.is_active = False
        self.completed_at = datetime.utcnow()

        # Определяем исход
        success_rate = self.correct_deductions / (
            self.correct_deductions + self.wrong_deductions
        )
        if success_rate >= config.PERFECT_CASE_THRESHOLD:
            self.outcome = CaseOutcome.SUCCESS
        elif success_rate >= config.PARTIAL_SUCCESS_THRESHOLD:
            self.outcome = CaseOutcome.PARTIAL_SUCCESS
        else:
            self.outcome = CaseOutcome.FAILURE

        # Рассчитываем награды
        rewards = self._calculate_rewards()

        # Обновляем статистику пользователя
        await self._update_user_stats(rewards)

        return {
            "outcome": self.outcome,
            "rewards": rewards,
            "statistics": self.get_statistics(),
        }

    def _calculate_rewards(self) -> Dict[str, int]:
        """Рассчитывает награды за расследование"""
        base_exp = config.BASE_EXPERIENCE * self.difficulty

        # Модификаторы наград
        time_bonus = self._calculate_time_bonus()
        accuracy_bonus = self.correct_deductions / max(
            1, self.correct_deductions + self.wrong_deductions
        )
        completion_bonus = len(
            [e for e in self.evidence if e.get("collected", False)]
        ) / len(self.evidence)

        total_exp = int(base_exp * (1 + time_bonus + accuracy_bonus + completion_bonus))

        return {
            "experience": total_exp,
            "detective_skill": self.difficulty * accuracy_bonus,
            "forensic_skill": self.difficulty * completion_bonus,
            "psychology_skill": self.difficulty
            * (self.witnesses_interviewed / len(self.witnesses)),
        }

    async def _update_user_stats(self, rewards: Dict[str, int]) -> None:
        """Обновляет статистику пользователя"""
        self.user.add_experience(rewards["experience"])
        self.user.improve_skill("detective", rewards["detective_skill"])
        self.user.improve_skill("forensic", rewards["forensic_skill"])
        self.user.improve_skill("psychology", rewards["psychology_skill"])

        self.user.update_statistics(
            case_solved=self.outcome == CaseOutcome.SUCCESS,
            correct=self.correct_deductions > self.wrong_deductions,
            perfect=self.outcome == CaseOutcome.SUCCESS and self.wrong_deductions == 0,
        )

    def _update_story_branch(self, implications: Dict[str, Any]) -> None:
        """Обновляет текущую ветку сюжета на основе действий игрока"""
        if implications.get("new_branch"):
            new_branch = f"{self.current_branch}_{len(self.story_branches)}"
            self.story_branches[new_branch] = implications["story_points"]
            self.current_branch = new_branch

    def _find_evidence(self, evidence_id: int) -> Optional[Dict[str, Any]]:
        """Находит улику по ID"""
        return next((e for e in self.evidence if e["id"] == evidence_id), None)

    def _find_witness(self, witness_id: int) -> Optional[Dict[str, Any]]:
        """Находит свидетеля по ID"""
        return next((w for w in self.witnesses if w["id"] == witness_id), None)

    def _find_suspect(self, suspect_id: int) -> Optional[Dict[str, Any]]:
        """Находит подозреваемого по ID"""
        return next((s for s in self.suspects if s["id"] == suspect_id), None)

    async def _generate_new_evidence(self, context: str) -> Dict[str, Any]:
        """Генерирует новую улику на основе контекста"""
        evidence_data = await self.claude_service.generate_evidence(
            self.title, context, len(self.evidence)
        )
        return {
            "id": len(self.evidence) + 1,
            **evidence_data,
            "collected": False,
            "analyzed": False,
        }

    def _calculate_time_bonus(self) -> float:
        """Рассчитывает бонус за скорость расследования"""
        if not self.completed_at:
            return 0.0

        investigation_time = (self.completed_at - self.created_at).total_seconds()
        par_time = config.BASE_INVESTIGATION_TIME * self.difficulty

        if investigation_time <= par_time:
            return 0.5  # Максимальный бонус за скорость
        else:
            return max(0.0, 0.5 - (investigation_time - par_time) / par_time)

    def get_statistics(self) -> Dict[str, Any]:
        """Возвращает статистику расследования"""
        return {
            "duration": (
                (self.completed_at - self.created_at).total_seconds()
                if self.completed_at
                else None
            ),
            "evidence_collected": len(
                [e for e in self.evidence if e.get("collected", False)]
            ),
            "total_evidence": len(self.evidence),
            "witnesses_interviewed": self.witnesses_interviewed,
            "suspects_interrogated": self.suspects_interrogated,
            "correct_deductions": self.correct_deductions,
            "wrong_deductions": self.wrong_deductions,
            "current_stage": self.current_stage,
            "outcome": self.outcome,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Сериализует расследование в словарь"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "difficulty": self.difficulty,
            "current_stage": self.current_stage,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "evidence": self.evidence,
            "suspects": self.suspects,
            "witnesses": self.witnesses,
            "statistics": self.get_statistics(),
        }

    async def change_location(self, location_id: str) -> Dict[str, Any]:
        """
        Смена текущей локации в расследовании.

        Args:
            location_id: Идентификатор новой локации

        Returns:
            Dict[str, Any]: Информация о новой локации и доступных действиях

        Raises:
            ValueError: Если локация недоступна или не существует
        """
        if not self.is_active:
            raise ValueError("Расследование завершено")

        # Проверяем доступность локации
        if location_id not in [loc["id"] for loc in self.available_locations]:
            raise ValueError("Локация недоступна")

        # Обновляем текущую локацию
        self.current_location = location_id
        if location_id not in self.visited_locations:
            self.visited_locations.append(location_id)

        location_description = (
            await self.claude_service.generate_location_description(
                self.title, location_id
            )
            or {}
        )

        # Проверяем наличие новых улик (30% шанс)
        if random.random() < 0.3:
            new_evidence = await self._generate_new_evidence(location_id)
            self.evidence.append(new_evidence)
            location_description["found_evidence"] = new_evidence

        return {
            "location": location_description,
            "available_actions": self._get_available_actions(),
        }

    def is_solved(self) -> bool:
        """
        Проверяет, решено ли дело.

        Returns:
            bool: True если дело решено, False в противном случае
        """
        return (
            self.outcome == CaseOutcome.SUCCESS
            or self.outcome == CaseOutcome.PARTIAL_SUCCESS
        )

    def is_failed(self) -> bool:
        """
        Проверяет, провалено ли дело.

        Returns:
            bool: True если дело провалено, False в противном случае
        """
        return self.outcome == CaseOutcome.FAILURE

    def is_completed(self) -> bool:
        """
        Проверяет, завершено ли дело (решено или провалено).

        Returns:
            bool: True если дело завершено, False в противном случае
        """
        return self.is_solved() or self.is_failed()
