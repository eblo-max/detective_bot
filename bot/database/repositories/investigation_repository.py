"""Репозиторий для работы с расследованиями."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import and_, select, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.config import config
from bot.database.models.investigation import (
    Investigation,
    InvestigationStage,
    InvestigationStatus,
    Evidence,
    Suspect,
)
from bot.database.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class InvestigationRepository(BaseRepository[Investigation]):
    """Репозиторий для работы с расследованиями."""

    def __init__(self, session: AsyncSession):
        """Инициализация репозитория."""
        super().__init__(session, Investigation)

    async def get_active_investigations(self) -> List[Investigation]:
        """Получить все активные расследования."""
        query = select(Investigation).where(
            Investigation.status == InvestigationStatus.IN_PROGRESS
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_investigation_by_id(
        self, investigation_id: int
    ) -> Optional[Investigation]:
        """Получить расследование по ID."""
        query = select(Investigation).where(Investigation.id == investigation_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_investigation(
        self,
        title: str,
        description: str,
        difficulty: int,
        user_id: int,
        evidence: Optional[List[Dict[str, Any]]] = None,
        suspects: Optional[List[Dict[str, Any]]] = None,
    ) -> Investigation:
        """Создать новое расследование."""
        investigation = Investigation(
            title=title,
            description=description,
            difficulty=difficulty,
            user_id=user_id,
            status=InvestigationStatus.NOT_STARTED,
            current_state={
                "stage": InvestigationStage.INITIAL,
                "location": "",
                "discovered_clues": [],
                "interrogated_suspects": [],
                "player_actions": [],
                "current_options": [],
            },
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.session.add(investigation)
        await self.session.commit()
        await self.session.refresh(investigation)
        return investigation

    async def update_investigation_status(
        self, investigation_id: int, status: InvestigationStatus
    ) -> Optional[Investigation]:
        """Обновить статус расследования."""
        investigation = await self.get_investigation_by_id(investigation_id)
        if not investigation:
            return None

        investigation.status = status
        investigation.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(investigation)
        return investigation

    async def add_evidence(
        self, investigation_id: int, evidence_type: str, description: str
    ) -> Optional[Evidence]:
        """Добавить улику в расследование."""
        investigation = await self.get_investigation_by_id(investigation_id)
        if not investigation:
            return None

        evidence = Evidence(
            investigation_id=investigation_id,
            type=evidence_type,
            description=description,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(evidence)
        await self.session.commit()
        await self.session.refresh(evidence)
        return evidence

    async def add_suspect(
        self,
        investigation_id: int,
        name: str,
        description: str,
        alibi: Optional[str] = None,
    ) -> Optional[Suspect]:
        """Добавить подозреваемого в расследование."""
        investigation = await self.get_investigation_by_id(investigation_id)
        if not investigation:
            return None

        suspect = Suspect(
            investigation_id=investigation_id,
            name=name,
            description=description,
            alibi=alibi,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(suspect)
        await self.session.commit()
        await self.session.refresh(suspect)
        return suspect

    async def get_user_investigations(
        self, user_id: int, status: Optional[InvestigationStatus] = None
    ) -> List[Investigation]:
        """Получить расследования пользователя."""
        conditions = [Investigation.user_id == user_id]
        if status is not None:
            conditions.append(Investigation.status == status)

        query = select(Investigation).where(and_(*conditions))
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_user_investigation(
        self, user_id: int, investigation_id: int
    ) -> Optional[Investigation]:
        """Получить расследование пользователя по ID."""
        query = select(Investigation).where(
            and_(
                Investigation.user_id == user_id,
                Investigation.id == investigation_id,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_top_investigations(self, limit: int = 10) -> List[Investigation]:
        """Получить топ расследований по сложности."""
        query = (
            select(Investigation).order_by(desc(Investigation.difficulty)).limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def search_investigations(
        self,
        query: str,
        difficulty: Optional[int] = None,
        status: Optional[InvestigationStatus] = None,
        limit: int = 10,
    ) -> List[Investigation]:
        """Поиск расследований."""
        conditions = [
            or_(
                Investigation.title.ilike(f"%{query}%"),
                Investigation.description.ilike(f"%{query}%"),
            )
        ]

        if difficulty is not None:
            conditions.append(Investigation.difficulty == difficulty)
        if status is not None:
            conditions.append(Investigation.status == status)

        query = select(Investigation).where(and_(*conditions)).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_investigation_progress(
        self, investigation_id: int
    ) -> Optional[Dict[str, Any]]:
        """Получить прогресс расследования."""
        investigation = await self.get_investigation_by_id(investigation_id)
        if not investigation:
            return None

        return {
            "id": investigation.id,
            "title": investigation.title,
            "status": investigation.status.value,
            "difficulty": investigation.difficulty,
            "progress": investigation.calculate_progress(),
            "current_state": investigation.current_state,
            "evidence_count": investigation.get_evidence_count(),
            "suspects_count": investigation.get_suspects_count(),
            "remaining_time": investigation.get_remaining_time(),
        }

    async def get_investigation_statistics(
        self, investigation_id: int
    ) -> Optional[Dict[str, Any]]:
        """Получить статистику расследования."""
        investigation = await self.get_investigation_by_id(investigation_id)
        if not investigation:
            return None

        return {
            "id": investigation.id,
            "title": investigation.title,
            "status": investigation.status.value,
            "difficulty": investigation.difficulty,
            "created_at": investigation.created_at.isoformat(),
            "updated_at": investigation.updated_at.isoformat(),
            "clues_found": investigation.clues_found,
            "suspects_interrogated": investigation.suspects_interrogated,
            "evidence_analyzed": investigation.evidence_analyzed,
            "correct_deductions": investigation.correct_deductions,
            "wrong_deductions": investigation.wrong_deductions,
            "player_actions": investigation.player_actions,
        }
