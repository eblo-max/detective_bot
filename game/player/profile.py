from datetime import datetime, timezone
from typing import Dict, List

from bot.database.models.user import User


class PlayerProfile:
    def __init__(self, user: User):
        self.user = user
        self.created_at = datetime.now(timezone.utc)
        self.level = 1
        self.experience = 0
        self.skills: Dict[str, int] = {
            "observation": 1,
            "analysis": 1,
            "deduction": 1,
            "interrogation": 1,
        }
        self.achievements: List[str] = []
        self.completed_cases: List[int] = []

    def add_experience(self, amount: int):
        self.experience += amount
        self._check_level_up()

    def _check_level_up(self):
        experience_needed = self.level * 1000
        if self.experience >= experience_needed:
            self.level += 1
            self.experience -= experience_needed

    def improve_skill(self, skill_name: str, amount: int = 1):
        if skill_name in self.skills:
            self.skills[skill_name] += amount
