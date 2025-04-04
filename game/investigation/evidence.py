from datetime import datetime
from typing import Dict, List, Optional

from bot.database.models.investigation import Evidence as DBEvidence
from game.player.skills import SkillType


class Evidence:
    def __init__(self, evidence_id: int, description: str, type: str):
        self.id = evidence_id
        self.description = description
        self.type = type
        self.found_at = datetime.utcnow()
        self.analyzed = False
        self.analysis_result = None

    def analyze(self, analysis: str):
        """Анализ улики"""
        self.analyzed = True
        self.analysis_result = analysis
        self.analyzed_at = datetime.utcnow()


class EvidenceSystem:
    @staticmethod
    def generate_evidence(case_context: str) -> Evidence:
        """Генерация новой улики на основе контекста дела"""
        # Здесь будет логика генерации улики
        return Evidence(evidence_id=1, description="Описание улики", type="physical")

    @staticmethod
    def analyze_evidence(evidence: Evidence, context: str) -> str:
        """Анализ улики"""
        # Здесь будет логика анализа улики
        return "Результаты анализа улики"
