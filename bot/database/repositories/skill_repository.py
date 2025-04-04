from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.skill import Skill, UserSkill, SkillType
from bot.database.repositories.base_repository import BaseRepository


class SkillRepository(BaseRepository[Skill]):
    """Репозиторий для работы с навыками."""

    def __init__(self, session: AsyncSession):
        """Инициализация репозитория."""
        super().__init__(session, Skill)

    async def get_skill_by_id(self, skill_id: int) -> Optional[Skill]:
        """Получить навык по ID."""
        query = select(Skill).where(Skill.id == skill_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_skill_by_type(self, skill_type: SkillType) -> Optional[Skill]:
        """Получить навык по типу."""
        query = select(Skill).where(Skill.type == skill_type)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_skill(
        self,
        name: str,
        description: str,
        skill_type: SkillType,
        max_level: int = 100,
        base_experience: int = 100,
        experience_multiplier: float = 1.5,
    ) -> Skill:
        """Создать новый навык."""
        skill = Skill(
            name=name,
            description=description,
            type=skill_type,
            max_level=max_level,
            base_experience=base_experience,
            experience_multiplier=experience_multiplier,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(skill)
        await self.session.commit()
        await self.session.refresh(skill)
        return skill

    async def get_user_skills(self, user_id: int) -> List[UserSkill]:
        """Получить навыки пользователя."""
        query = select(UserSkill).where(UserSkill.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_user_skill(self, user_id: int, skill_id: int) -> Optional[UserSkill]:
        """Получить навык пользователя по ID."""
        query = select(UserSkill).where(
            and_(
                UserSkill.user_id == user_id,
                UserSkill.skill_id == skill_id,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_user_skill(
        self, user_id: int, skill_id: int, level: int = 1, experience: int = 0
    ) -> UserSkill:
        """Создать навык для пользователя."""
        user_skill = UserSkill(
            user_id=user_id,
            skill_id=skill_id,
            level=level,
            experience=experience,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(user_skill)
        await self.session.commit()
        await self.session.refresh(user_skill)
        return user_skill

    async def add_experience(
        self, user_id: int, skill_id: int, experience_amount: int
    ) -> Optional[UserSkill]:
        """Добавить опыт к навыку пользователя."""
        user_skill = await self.get_user_skill(user_id, skill_id)
        if not user_skill:
            return None

        user_skill.add_experience(experience_amount)
        user_skill.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(user_skill)
        return user_skill

    async def get_skills_by_type(self, skill_type: SkillType) -> List[Skill]:
        """Получить навыки по типу."""
        query = select(Skill).where(Skill.type == skill_type)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_top_skills(
        self, skill_type: Optional[SkillType] = None, limit: int = 10
    ) -> List[UserSkill]:
        """Получить топ навыков по уровню."""
        conditions = []
        if skill_type is not None:
            conditions.append(Skill.type == skill_type)

        query = (
            select(UserSkill)
            .join(Skill)
            .where(and_(*conditions))
            .order_by(desc(UserSkill.level), desc(UserSkill.experience))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def search_skills(
        self,
        query: str,
        skill_type: Optional[SkillType] = None,
        limit: int = 10,
    ) -> List[Skill]:
        """Поиск навыков."""
        conditions = [
            or_(
                Skill.name.ilike(f"%{query}%"),
                Skill.description.ilike(f"%{query}%"),
            )
        ]

        if skill_type is not None:
            conditions.append(Skill.type == skill_type)

        query = select(Skill).where(and_(*conditions)).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_skill_progress(
        self, user_id: int, skill_id: int
    ) -> Optional[Dict[str, Any]]:
        """Получить прогресс навыка пользователя."""
        user_skill = await self.get_user_skill(user_id, skill_id)
        if not user_skill:
            return None

        skill = await self.get_skill_by_id(skill_id)
        if not skill:
            return None

        return {
            "skill_id": skill_id,
            "name": skill.name,
            "type": skill.type.value,
            "level": user_skill.level,
            "experience": user_skill.experience,
            "next_level_experience": skill.get_experience_for_level(
                user_skill.level + 1
            ),
            "progress_percentage": user_skill.calculate_progress_percentage(),
            "created_at": user_skill.created_at.isoformat(),
            "updated_at": user_skill.updated_at.isoformat(),
        }

    async def get_user_skill_tree(self, user_id: int) -> Dict[str, Any]:
        """Получить дерево навыков пользователя."""
        user_skills = await self.get_user_skills(user_id)

        skill_tree = {
            "observation": None,
            "deduction": None,
            "interrogation": None,
            "forensics": None,
            "psychology": None,
        }

        for user_skill in user_skills:
            skill = await self.get_skill_by_id(user_skill.skill_id)
            if skill:
                skill_tree[skill.type.value] = {
                    "level": user_skill.level,
                    "experience": user_skill.experience,
                    "next_level_experience": skill.get_experience_for_level(
                        user_skill.level + 1
                    ),
                    "progress_percentage": user_skill.calculate_progress_percentage(),
                }

        return skill_tree
