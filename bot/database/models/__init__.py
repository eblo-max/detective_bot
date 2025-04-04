"""
Основной модуль бота-детектива
"""

from bot.database.models.achievement import Achievement, UserAchievement
from bot.database.models.case import Case, CaseStatus, UserCase
from bot.database.models.investigation import (
    Investigation,
    InvestigationStatus,
    InvestigationStage,
    Evidence,
    Suspect,
)
from bot.database.models.relationship import Relationship, RelationshipStatus
from bot.database.models.resources import Energy, Inventory, Reputation
from bot.database.models.skill import Skill, UserSkill, SkillType
from bot.database.models.user import User, UserStats, UserStatus

__all__ = [
    "Achievement",
    "UserAchievement",
    "Case",
    "CaseStatus",
    "UserCase",
    "Investigation",
    "InvestigationStatus",
    "InvestigationStage",
    "Evidence",
    "Suspect",
    "Relationship",
    "RelationshipStatus",
    "Energy",
    "Inventory",
    "Reputation",
    "Skill",
    "UserSkill",
    "SkillType",
    "User",
    "UserStats",
    "UserStatus",
]
