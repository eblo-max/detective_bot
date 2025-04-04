from typing import Dict

from services.claude_service.claude_service import ClaudeService


class ProfileService:
    def __init__(self):
        self.claude_service = ClaudeService()

    async def generate_suspect_profile(
        self, case_context: str, suspect_info: Dict
    ) -> Dict:
        """Генерация психологического профиля подозреваемого"""
        prompt = f"""
        На основе следующей информации создай психологический профиль подозреваемого:
        
        Контекст дела: {case_context}
        Информация о подозреваемом: {suspect_info}
        
        Включи следующие аспекты:
        1. Личностные характеристики
        2. Мотивация
        3. Поведенческие паттерны
        4. Возможные слабости
        """

        response = await self.claude_service.client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        return {
            "suspect_name": suspect_info.get("name"),
            "profile": response.content[0].text,
        }

    async def analyze_behavior(self, case_context: str, behavior_data: Dict) -> Dict:
        """Анализ поведения подозреваемого"""
        prompt = f"""
        Проанализируй поведение подозреваемого на основе следующих данных:
        
        Контекст дела: {case_context}
        Данные о поведении: {behavior_data}
        
        Включи:
        1. Анализ паттернов поведения
        2. Оценка правдивости показаний
        3. Выявление возможных противоречий
        """

        response = await self.claude_service.client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )

        return {"analysis": response.content[0].text}
