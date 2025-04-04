"""Модель расследования."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional, TYPE_CHECKING

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.models.base import Base
from bot.core.config import config

if TYPE_CHECKING:
    from bot.database.models.user import User


class InvestigationStatus(str, Enum):
    """Статусы расследования."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class InvestigationStage(str, Enum):
    """Этапы расследования."""

    INITIAL = "initial"
    INVESTIGATION = "investigation"
    INTERROGATION = "interrogation"
    EVIDENCE_ANALYSIS = "evidence_analysis"
    CONCLUSION = "conclusion"


@dataclass
class GameAction:
    """Действие игрока."""

    def __init__(
        self,
        action: str,
        timestamp: datetime,
        result: Optional[str] = None,
        evidence_found: Optional[List[str]] = None,
        clues_discovered: Optional[List[str]] = None,
    ):
        """
        Действие игрока.

        Args:
            action: str
            timestamp: datetime
            result: Optional[str]
            evidence_found: Optional[List[str]]
            clues_discovered: Optional[List[str]]
        """
        self.action = action
        self.timestamp = timestamp
        self.result = result
        self.evidence_found = evidence_found or []
        self.clues_discovered = clues_discovered or []


@dataclass
class StoryNode:
    """Узел истории."""

    text: str
    options: List[str]
    requirements: Optional[Dict[str, Any]] = None
    consequences: Optional[List[str]] = None
    evidence: Optional[List[str]] = None
    suspects: Optional[List[str]] = None


@dataclass
class InvestigationState:
    """Текущее состояние расследования."""

    stage: InvestigationStage
    location: str
    discovered_clues: List[str]
    interrogated_suspects: List[str]
    player_actions: List[GameAction]
    current_options: List[str]
    evidence_collected: Optional[List[str]] = None
    active_suspects: Optional[List[str]] = None
    time_of_day: str = "day"
    weather: str = "clear"
    special_conditions: Optional[List[str]] = None


@dataclass
class InvestigationData:
    """Расследование."""

    id: str
    title: str
    status: InvestigationStatus
    difficulty: int
    current_state: InvestigationState
    story_nodes: Dict[str, StoryNode]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    player_id: Optional[str] = None
    template_id: Optional[str] = None
    progress: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует расследование в словарь."""
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "difficulty": self.difficulty,
            "current_state": {
                "stage": self.current_state.stage,
                "location": self.current_state.location,
                "discovered_clues": self.current_state.discovered_clues,
                "interrogated_suspects": self.current_state.interrogated_suspects,
                "player_actions": [
                    {
                        "action": action.action,
                        "timestamp": action.timestamp.isoformat(),
                        "result": action.result,
                        "evidence_found": action.evidence_found,
                        "clues_discovered": action.clues_discovered,
                    }
                    for action in self.current_state.player_actions
                ],
                "current_options": self.current_state.current_options,
                "evidence_collected": self.current_state.evidence_collected,
                "active_suspects": self.current_state.active_suspects,
                "time_of_day": self.current_state.time_of_day,
                "weather": self.current_state.weather,
                "special_conditions": self.current_state.special_conditions,
            },
            "story_nodes": {
                node_id: {
                    "text": node.text,
                    "options": node.options,
                    "requirements": node.requirements,
                    "consequences": node.consequences,
                    "evidence": node.evidence,
                    "suspects": node.suspects,
                }
                for node_id, node in self.story_nodes.items()
            },
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "player_id": self.player_id,
            "template_id": self.template_id,
            "progress": self.progress,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InvestigationData":
        """Создает расследование из словаря."""
        # Преобразуем строки дат в объекты datetime
        for date_field in ["created_at", "updated_at", "completed_at"]:
            if date_field in data and data[date_field]:
                data[date_field] = datetime.fromisoformat(data[date_field])

        # Преобразуем действия игрока
        if "current_state" in data and "player_actions" in data["current_state"]:
            data["current_state"]["player_actions"] = [
                GameAction(
                    action=action["action"],
                    timestamp=datetime.fromisoformat(action["timestamp"]),
                    result=action.get("result"),
                    evidence_found=action.get("evidence_found", []),
                    clues_discovered=action.get("clues_discovered", []),
                )
                for action in data["current_state"]["player_actions"]
            ]

        # Преобразуем узлы истории
        if "story_nodes" in data:
            data["story_nodes"] = {
                node_id: StoryNode(**node_data)
                for node_id, node_data in data["story_nodes"].items()
            }

        # Преобразуем текущее состояние
        if "current_state" in data:
            data["current_state"] = InvestigationState(**data["current_state"])

        return cls(**data)


class Evidence(Base):
    """Модель улики"""

    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    investigation_id: Mapped[int] = mapped_column(ForeignKey("investigations.id"))
    type: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc)
    )

    investigation: Mapped["Investigation"] = relationship(
        "Investigation", back_populates="evidence"
    )

    def to_dict(self) -> dict:
        """Преобразует объект в словарь"""
        return {
            "id": self.id,
            "type": self.type,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
        }


class Suspect(Base):
    """Модель подозреваемого"""

    __tablename__ = "suspect"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    investigation_id: Mapped[int] = mapped_column(ForeignKey("investigations.id"))
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    alibi: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc)
    )

    investigation: Mapped["Investigation"] = relationship(
        "Investigation", back_populates="suspects"
    )

    def to_dict(self) -> dict:
        """Преобразует объект в словарь"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "alibi": self.alibi,
            "created_at": self.created_at.isoformat(),
        }


class Investigation(Base):
    __tablename__ = "investigations"

    # Основные поля
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    status: Mapped[InvestigationStatus] = mapped_column(
        SQLAlchemyEnum(InvestigationStatus),
        default=InvestigationStatus.NOT_STARTED,
        nullable=False,
    )

    # Временные поля
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
    )
    solved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Связь с пользователем
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    user: Mapped["User"] = relationship(
        "User", back_populates="investigations", foreign_keys=[user_id]
    )

    # JSON поля для хранения состояния и действий
    current_state: Mapped[Dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    player_actions: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )

    # Игровая механика
    clues_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    suspects_interrogated: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    evidence_analyzed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_deductions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wrong_deductions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Связи с другими таблицами
    evidence: Mapped[List["Evidence"]] = relationship(
        "Evidence", back_populates="investigation", cascade="all, delete-orphan"
    )
    suspects: Mapped[List["Suspect"]] = relationship(
        "Suspect", back_populates="investigation", cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_state = {
            "stage": InvestigationStage.INITIAL,
            "location": "",
            "discovered_clues": [],
            "interrogated_suspects": [],
            "player_actions": [],
            "current_options": [],
        }
        self.player_actions = []

    def add_player_action(
        self, action_type: str, description: str, result: Optional[str] = None
    ) -> None:
        """Добавляет действие игрока в историю"""
        action = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": action_type,
            "description": description,
            "result": result,
        }
        self.player_actions.append(action)
        self.updated_at = datetime.now(timezone.utc)

    def add_clue(self, clue_description: str) -> None:
        """Добавляет новую улику"""
        self.clues_found += 1
        self.current_state["discovered_clues"].append(clue_description)
        self.add_player_action("clue_found", f"Найдена улика: {clue_description}")

    def interrogate_suspect(self, suspect_id: int, result: str) -> None:
        """Регистрирует допрос подозреваемого"""
        self.suspects_interrogated += 1
        if suspect_id not in self.current_state["interrogated_suspects"]:
            self.current_state["interrogated_suspects"].append(suspect_id)
        self.add_player_action(
            "interrogation", f"Допрошен подозреваемый #{suspect_id}", result
        )

    def analyze_evidence(self, evidence_id: int, analysis_result: str) -> None:
        """Регистрирует анализ улики"""
        self.evidence_analyzed += 1
        self.add_player_action(
            "evidence_analysis",
            f"Проанализирована улика #{evidence_id}",
            analysis_result,
        )

    def make_deduction(self, deduction: str, is_correct: bool) -> None:
        """Регистрирует вывод игрока"""
        if is_correct:
            self.correct_deductions += 1
        else:
            self.wrong_deductions += 1
        self.add_player_action(
            "deduction", deduction, "Верно" if is_correct else "Неверно"
        )

    def update_status(self, new_status: InvestigationStatus) -> None:
        """Обновляет статус расследования"""
        self.status = new_status
        if new_status == InvestigationStatus.COMPLETED:
            self.solved_at = datetime.now(timezone.utc)
        self.add_player_action("status_change", f"Статус изменен на {new_status}")

    def get_progress(self) -> float:
        """Возвращает прогресс расследования в процентах"""
        total_tasks = config.TASKS_PER_INVESTIGATION
        completed_tasks = (
            len(self.current_state["discovered_clues"])
            + len(self.current_state["interrogated_suspects"])
            + self.evidence_analyzed
        )
        return min(100.0, (completed_tasks / total_tasks) * 100)

    def to_dict(self) -> Dict[str, Any]:
        """Сериализует модель в словарь"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "difficulty": self.difficulty,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "solved_at": self.solved_at.isoformat() if self.solved_at else None,
            "user_id": self.user_id,
            "current_state": self.current_state,
            "progress": self.get_progress(),
            "statistics": {
                "clues_found": self.clues_found,
                "suspects_interrogated": self.suspects_interrogated,
                "evidence_analyzed": self.evidence_analyzed,
                "correct_deductions": self.correct_deductions,
                "wrong_deductions": self.wrong_deductions,
            },
            "last_action": self.player_actions[-1] if self.player_actions else None,
        }

    def calculate_progress(self) -> float:
        """
        Рассчитывает прогресс расследования в процентах.

        Returns:
            float: Прогресс от 0 до 100
        """
        total_tasks = len(self.evidence) + len(self.suspects)
        completed_tasks = self.evidence_analyzed + self.suspects_interrogated
        return (
            min(100.0, (completed_tasks / total_tasks) * 100)
            if total_tasks > 0
            else 0.0
        )

    def is_completed(self) -> bool:
        """
        Проверяет, завершено ли расследование.

        Returns:
            bool: True если расследование завершено
        """
        return self.status == InvestigationStatus.COMPLETED

    def add_evidence(self, evidence_type: str, description: str) -> Evidence:
        """
        Добавляет новую улику в расследование.

        Args:
            evidence_type: Тип улики
            description: Описание улики

        Returns:
            Evidence: Созданная улика
        """
        evidence = Evidence(
            type=evidence_type, description=description, investigation_id=self.id
        )
        self.evidence.append(evidence)
        return evidence

    def add_suspect(
        self, name: str, description: str, alibi: Optional[str] = None
    ) -> "Suspect":
        """Добавляет подозреваемого к расследованию"""
        suspect = Suspect(
            investigation_id=self.id, name=name, description=description, alibi=alibi
        )
        self.suspects.append(suspect)
        return suspect

    def complete(self) -> None:
        """Завершает расследование"""
        self.status = InvestigationStatus.COMPLETED
        self.updated_at = datetime.now(timezone.utc)

    def fail(self) -> None:
        """Помечает расследование как проваленное"""
        self.status = InvestigationStatus.FAILED
        self.updated_at = datetime.now(timezone.utc)

    def timeout(self) -> None:
        """Помечает расследование как просроченное"""
        self.status = InvestigationStatus.TIMEOUT
        self.updated_at = datetime.now(timezone.utc)

    def is_active(self) -> bool:
        """Проверяет, является ли расследование активным"""
        return self.status == InvestigationStatus.IN_PROGRESS

    def is_failed(self) -> bool:
        """Проверяет, провалено ли расследование"""
        return self.status == InvestigationStatus.FAILED

    def is_timeout(self) -> bool:
        """Проверяет, просрочено ли расследование"""
        return self.status == InvestigationStatus.TIMEOUT

    def get_evidence_by_type(self, evidence_type: str) -> List[Evidence]:
        """Получает все улики определенного типа"""
        return [e for e in self.evidence if e.type == evidence_type]

    def get_suspect_by_name(self, name: str) -> Optional["Suspect"]:
        """Получает подозреваемого по имени"""
        for suspect in self.suspects:
            if suspect.name.lower() == name.lower():
                return suspect
        return None

    def get_suspects_without_alibi(self) -> List["Suspect"]:
        """Получает всех подозреваемых без алиби"""
        return [s for s in self.suspects if not s.alibi]

    def get_suspects_with_alibi(self) -> List["Suspect"]:
        """Получает всех подозреваемых с алиби"""
        return [s for s in self.suspects if s.alibi]

    def get_evidence_count(self) -> int:
        """Получает количество улик"""
        return len(self.evidence)

    def get_suspects_count(self) -> int:
        """Получает количество подозреваемых"""
        return len(self.suspects)

    def get_remaining_time(self) -> int:
        """Получает оставшееся время до дедлайна в часах"""
        if self.is_timeout():
            return 0
        now = datetime.now(timezone.utc)
        if now >= self.updated_at:
            return 0
        return int((self.updated_at - now).total_seconds() / 3600)
