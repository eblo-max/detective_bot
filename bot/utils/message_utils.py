def format_case_description(description: str) -> str:
    """Форматирует описание дела"""
    return f"🔍 Дело:\n\n{description}"


def format_evidence(evidence: dict) -> str:
    """Форматирует описание улики"""
    return f"📝 Улика:\n\n{evidence['description']}"


def format_suspect(suspect: dict) -> str:
    """Форматирует описание подозреваемого"""
    return f"👤 Подозреваемый:\n\nИмя: {suspect['name']}\nОписание: {suspect['description']}"


def format_achievement(achievement: str) -> str:
    """Форматирует описание достижения"""
    return f"🏆 Достижение разблокировано:\n\n{achievement}"
