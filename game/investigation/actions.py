from typing import Dict, List, Optional

from game.investigation.case import Case
from game.player.skills import SkillType
from game.player.energy import ActionType


class InvestigationActions:
    @staticmethod
    async def search_evidence(case: Case) -> Dict:
        """Поиск улик"""
        return {
            "action": "search_evidence",
            "success": True,
            "message": "Вы нашли новую улику!",
            "evidence": {"description": "Описание найденной улики"},
        }

    @staticmethod
    async def interrogate_suspect(case: Case, suspect_id: int) -> Dict:
        """Допрос подозреваемого"""
        return {
            "action": "interrogate_suspect",
            "success": True,
            "message": "Подозреваемый дал показания",
            "testimony": "Текст показаний",
        }

    @staticmethod
    async def analyze_evidence(case: Case, evidence_id: int) -> Dict:
        """Анализ улики"""
        return {
            "action": "analyze_evidence",
            "success": True,
            "message": "Анализ улики завершен",
            "analysis": "Результаты анализа",
        }

    @staticmethod
    async def propose_solution(case: Case, solution: str) -> Dict:
        """Выдвижение версии"""
        return {
            "action": "propose_solution",
            "success": True,
            "message": "Версия выдвинута",
            "solution": solution,
        }
