from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.relationship import Relationship, RelationshipStatus
from bot.database.repositories.base_repository import BaseRepository


class RelationshipRepository(BaseRepository[Relationship]):
    """Репозиторий для работы с отношениями между пользователями."""

    def __init__(self, session: AsyncSession):
        """Инициализация репозитория."""
        super().__init__(session, Relationship)

    async def get_relationship(
        self, user_id: int, target_id: int
    ) -> Optional[Relationship]:
        """Получить отношение между пользователями."""
        query = select(Relationship).where(
            and_(
                or_(
                    and_(
                        Relationship.user_id == user_id,
                        Relationship.target_id == target_id,
                    ),
                    and_(
                        Relationship.user_id == target_id,
                        Relationship.target_id == user_id,
                    ),
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_relationship(
        self,
        user_id: int,
        target_id: int,
        status: RelationshipStatus = RelationshipStatus.NEUTRAL,
        trust_level: int = 0,
    ) -> Relationship:
        """Создать отношение между пользователями."""
        relationship = Relationship(
            user_id=user_id,
            target_id=target_id,
            status=status,
            trust_level=trust_level,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(relationship)
        await self.session.commit()
        await self.session.refresh(relationship)
        return relationship

    async def update_trust(
        self, user_id: int, target_id: int, trust_change: int
    ) -> Optional[Relationship]:
        """Обновить уровень доверия в отношениях."""
        relationship = await self.get_relationship(user_id, target_id)
        if not relationship:
            return None

        relationship.update_trust(trust_change)
        relationship.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(relationship)
        return relationship

    async def get_user_relationships(
        self, user_id: int, status: Optional[RelationshipStatus] = None
    ) -> List[Relationship]:
        """Получить отношения пользователя."""
        conditions = [
            or_(Relationship.user_id == user_id, Relationship.target_id == user_id)
        ]
        if status is not None:
            conditions.append(Relationship.status == status)

        query = select(Relationship).where(and_(*conditions))
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_user_friends(self, user_id: int) -> List[Relationship]:
        """Получить друзей пользователя."""
        return await self.get_user_relationships(user_id, RelationshipStatus.FRIENDLY)

    async def get_user_rivals(self, user_id: int) -> List[Relationship]:
        """Получить соперников пользователя."""
        return await self.get_user_relationships(user_id, RelationshipStatus.RIVAL)

    async def get_top_relationships(
        self, user_id: int, limit: int = 10
    ) -> List[Relationship]:
        """Получить топ отношений пользователя по уровню доверия."""
        query = (
            select(Relationship)
            .where(
                or_(Relationship.user_id == user_id, Relationship.target_id == user_id)
            )
            .order_by(desc(Relationship.trust_level))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def search_relationships(
        self,
        user_id: int,
        query: str,
        status: Optional[RelationshipStatus] = None,
        limit: int = 10,
    ) -> List[Relationship]:
        """Поиск отношений пользователя."""
        conditions = [
            or_(Relationship.user_id == user_id, Relationship.target_id == user_id)
        ]

        if status is not None:
            conditions.append(Relationship.status == status)

        # Здесь нужно добавить поиск по имени пользователя
        # Для этого нужно сделать JOIN с таблицей пользователей
        # TODO: Реализовать поиск по имени пользователя

        query = select(Relationship).where(and_(*conditions)).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_relationship_stats(self, user_id: int) -> Dict[str, Any]:
        """Получить статистику отношений пользователя."""
        relationships = await self.get_user_relationships(user_id)

        stats = {
            "total_relationships": len(relationships),
            "friends": len(
                [r for r in relationships if r.status == RelationshipStatus.FRIENDLY]
            ),
            "rivals": len(
                [r for r in relationships if r.status == RelationshipStatus.RIVAL]
            ),
            "neutral": len(
                [r for r in relationships if r.status == RelationshipStatus.NEUTRAL]
            ),
            "average_trust": (
                sum(r.trust_level for r in relationships) / len(relationships)
                if relationships
                else 0
            ),
            "top_relationships": [
                {
                    "user_id": r.target_id if r.user_id == user_id else r.user_id,
                    "status": r.status.value,
                    "trust_level": r.trust_level,
                    "created_at": r.created_at.isoformat(),
                    "updated_at": r.updated_at.isoformat(),
                }
                for r in sorted(
                    relationships, key=lambda x: x.trust_level, reverse=True
                )[:5]
            ],
        }

        return stats

    async def get_relationship_history(
        self, user_id: int, target_id: int
    ) -> Optional[Dict[str, Any]]:
        """Получить историю отношений между пользователями."""
        relationship = await self.get_relationship(user_id, target_id)
        if not relationship:
            return None

        return {
            "user_id": user_id,
            "target_id": target_id,
            "status": relationship.status.value,
            "trust_level": relationship.trust_level,
            "created_at": relationship.created_at.isoformat(),
            "updated_at": relationship.updated_at.isoformat(),
            "is_mutual": relationship.is_mutual,
        }
