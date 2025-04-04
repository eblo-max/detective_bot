import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Union

from bot.database.models.investigation import Investigation, InvestigationStage
from game.player.skills import SkillType
from game.player.energy import ActionType

# Константы для типов улик
EVIDENCE_PHOTOS = "фотографии"
EVIDENCE_DOCUMENTS = "документы"


class CrimeType(Enum):
    """Типы преступлений"""

    MURDER = "murder"
    KIDNAPPING = "kidnapping"
    ROBBERY = "robbery"
    FRAUD = "fraud"
    BLACKMAIL = "blackmail"
    ARSON = "arson"
    THEFT = "theft"
    ASSAULT = "assault"


class Difficulty(Enum):
    """Уровни сложности расследования"""

    EASY = 1
    MEDIUM = 2
    HARD = 3
    EXPERT = 4


@dataclass
class Location:
    """Шаблон локации"""

    name: str
    description: str
    available_actions: List[str]
    clues: List[str]
    suspects: List[str]


@dataclass
class Evidence:
    """Шаблон улики"""

    name: str
    description: str
    type: str
    importance: int  # 1-5
    analysis_time: int  # в минутах
    possible_conclusions: List[str]
    required_skills: List[str]


@dataclass
class Suspect:
    """Шаблон подозреваемого"""

    name: str
    description: str
    alibi: str
    motives: List[str]
    evidence: List[str]
    is_guilty: bool


@dataclass
class CaseTemplate:
    """Шаблон расследования"""

    id: str
    title: str
    description: str
    difficulty: Difficulty
    locations: List[Location]
    suspects: List[Suspect]
    key_evidence: List[str]
    red_herrings: List[str]
    correct_sequence: List[str]
    hints: Dict[int, List[str]]  # Уровень навыка -> список подсказок


# Шаблоны локаций
LOCATION_TEMPLATES = {
    "crime_scene": Location(
        name="Место преступления",
        description="Основная локация, где произошло преступление",
        available_actions=["Осмотреть место преступления", "Опросить свидетелей"],
        clues=[
            "отпечатки пальцев",
            "следы крови",
            "сломанные предметы",
            "потерянные вещи",
            "записки",
            EVIDENCE_PHOTOS,
        ],
        suspects=["свидетели", "первый нашедший", "очевидцы", "случайные прохожие"],
    ),
    "police_station": Location(
        name="Полицейский участок",
        description="Место для работы с документами и допросов",
        available_actions=[
            "Осмотреть документы",
            "Опросить задержанных",
            "Опросить информаторов",
        ],
        clues=["протоколы", EVIDENCE_PHOTOS, "записи допросов", "досье", "отчеты"],
        suspects=["задержанные", "свидетели", "информаторы", "коллеги"],
    ),
}

# Шаблоны улик
EVIDENCE_TEMPLATES = {
    "physical": Evidence(
        name="Физическая улика",
        description="Материальный объект, связанный с преступлением",
        type="physical",
        importance=3,
        analysis_time=30,
        possible_conclusions=[
            "принадлежит подозреваемому",
            "содержит следы ДНК",
            "имеет отпечатки",
            "был поврежден",
            "был перемещен",
        ],
        required_skills=["forensic", "detective"],
    ),
    "documentary": Evidence(
        name="Документальная улика",
        description="Бумаги, записи, электронные данные",
        type="documentary",
        importance=2,
        analysis_time=20,
        possible_conclusions=[
            "подлинность",
            "время создания",
            "авторство",
            "содержание",
            "история изменений",
        ],
        required_skills=["detective", "forensic"],
    ),
    "testimonial": Evidence(
        name="Показания",
        description="Устные или письменные свидетельства",
        type="testimonial",
        importance=2,
        analysis_time=15,
        possible_conclusions=[
            "достоверность",
            "противоречия",
            "мотивы",
            "отношения",
            "временная линия",
        ],
        required_skills=["psychology", "detective"],
    ),
}

# Шаблоны подозреваемых
SUSPECT_TEMPLATES = {
    "primary": Suspect(
        name="Основной подозреваемый",
        description="Главный подозреваемый в расследовании",
        alibi="был дома",
        motives=["месть", "деньги", "власть", "любовь", "зависть", "самозащита"],
        evidence=["отпечатки", "ДНК", EVIDENCE_DOCUMENTS, EVIDENCE_PHOTOS, "записи"],
        is_guilty=False,
    )
}

# Шаблоны расследований
CASE_TEMPLATES = {
    "murder_basic": CaseTemplate(
        id="murder_001",
        title="Убийство в старом особняке",
        description=(
            "В роскошном особняке на окраине города обнаружено тело известного коллекционера "
            "антиквариата. Смерть наступила в результате отравления. В доме находились только "
            "близкие родственники и слуги. Кто же совершил это преступление?"
        ),
        difficulty=Difficulty.MEDIUM,
        locations=[
            LOCATION_TEMPLATES["crime_scene"],
            LOCATION_TEMPLATES["police_station"],
        ],
        suspects=[SUSPECT_TEMPLATES["primary"]],
        key_evidence=[
            "Остатки яда в бокале вина",
            "Следы грязи от садовых ботинок",
            "Записи в дневнике о подозрительных встречах",
            "Странные покупки племянника",
            "Подозрительные звонки в ночь убийства",
        ],
        red_herrings=[
            "Сломанная ручка чайника",
            "Странные пятна на фартуке горничной",
            "Открытый сейф",
            "Следы сажи на руках дворецкого",
            "Пустая бутылка из-под вина",
        ],
        correct_sequence=[
            "Осмотреть место преступления",
            "Собрать улики",
            "Опросить свидетелей",
            "Проверить алиби",
            "Проанализировать мотивы",
            "Сопоставить доказательства",
            "Выявить виновного",
        ],
        hints={
            1: [
                "Обратите внимание на следы на полу",
                "Проверьте содержимое бокалов",
                "Расспросите всех свидетелей",
            ],
            2: [
                "Сравните алиби подозреваемых",
                "Изучите записи в дневнике",
                "Проверьте покупки подозреваемых",
            ],
            3: [
                "Проанализируйте мотивы каждого подозреваемого",
                "Сопоставьте улики с алиби",
                "Обратите внимание на странные совпадения",
            ],
            4: [
                "Изучите связи между подозреваемыми",
                "Проверьте финансовые операции",
                "Проанализируйте поведение в ночь убийства",
            ],
        },
    )
}

# Шаблоны промптов для Claude API
CLAUDE_PROMPTS = {
    "generate_story": """
    Создай детективную историю со следующими параметрами:
    - Тип преступления: {crime_type}
    - Сложность: {difficulty}
    - Локация: {location}
    - Подозреваемые: {suspects}
    
    История должна включать:
    1. Описание места преступления
    2. Характеристики подозреваемых
    3. Найденные улики
    4. Возможные сюжетные повороты
    5. Ключевые подсказки
    """,
    "analyze_evidence": """
    Проанализируй следующую улику:
    - Тип: {evidence_type}
    - Описание: {evidence_description}
    - Контекст: {context}
    
    Предоставь:
    1. Возможные выводы
    2. Необходимые навыки для анализа
    3. Время на анализ
    4. Связи с другими уликами
    """,
    "create_profile": """
    Создай психологический профиль подозреваемого:
    - Имя: {name}
    - Описание: {description}
    - Мотивы: {motives}
    - Алиби: {alibi}
    
    Включи:
    1. Характерные черты
    2. Возможные мотивы
    3. Вероятность причастности
    4. Рекомендации по допросу
    """,
}

# Шаблоны сообщений
MESSAGE_TEMPLATES = {
    "case_start": """
    🕵️ Новое расследование: {title}
    
    {description}
    
    ⏰ Время на расследование: {time_limit} часов
    🎯 Сложность: {difficulty}
    
    Начните с осмотра места преступления.
    """,
    "evidence_found": """
    🔍 Найдена новая улика!
    
    {evidence_description}
    
    Что вы хотите сделать?
    1. Проанализировать улику
    2. Связать с другими уликами
    3. Показать подозреваемым
    """,
    "suspect_interview": """
    👤 Допрос подозреваемого: {suspect_name}
    
    {suspect_description}
    
    Алиби: {alibi}
    
    Задайте вопрос или выберите тактику допроса.
    """,
    "case_success": """
    🎉 Поздравляем! Дело раскрыто!
    
    Преступник: {culprit}
    Мотив: {motive}
    
    Ваши достижения:
    {achievements}
    
    Награда: {reward}
    """,
    "case_failure": """
    ❌ К сожалению, время истекло...
    
    Что пошло не так:
    {failure_reasons}
    
    Попробуйте еще раз или выберите другое дело.
    """,
}

# Библиотека мотивов и характеристик
CHARACTER_TRAITS = {
    "motives": [
        "месть",
        "деньги",
        "власть",
        "любовь",
        "зависть",
        "самозащита",
        "идеология",
        "психологические проблемы",
        "семейные обстоятельства",
        "профессиональные конфликты",
    ],
    "personality_traits": [
        "агрессивный",
        "хитрый",
        "умный",
        "эмоциональный",
        "холодный",
        "импульсивный",
        "расчетливый",
        "трусливый",
        "храбрый",
        "манипулятивный",
    ],
    "occupations": [
        "бизнесмен",
        "политик",
        "врач",
        "юрист",
        "полицейский",
        "преступник",
        "служащий",
        "артист",
        "ученый",
        "военный",
    ],
}

# Система ветвления сюжета
PLOT_BRANCHES = {
    "evidence_analysis": {
        "success": {
            "next_steps": [
                "найти новые улики",
                "допросить подозреваемых",
                "проверить алиби",
                "связать улики",
            ],
            "consequences": [
                "новые подозреваемые",
                "изменение приоритетов",
                "разблокировка новых локаций",
                "получение подсказок",
            ],
        },
        "failure": {
            "next_steps": [
                "повторить анализ",
                "искать другие улики",
                "изменить подход",
                "консультироваться с экспертами",
            ],
            "consequences": [
                "потеря времени",
                "ухудшение отношений",
                "появление новых подозреваемых",
                "изменение сложности",
            ],
        },
    },
    "suspect_interview": {
        "success": {
            "next_steps": [
                "проверить показания",
                "искать подтверждения",
                "допросить других",
                "анализировать связи",
            ],
            "consequences": [
                "новые улики",
                "изменение отношений",
                "разоблачение лжи",
                "получение алиби",
            ],
        },
        "failure": {
            "next_steps": [
                "изменить тактику",
                "допросить снова",
                "искать другие подходы",
                "консультироваться с психологом",
            ],
            "consequences": [
                "ухудшение отношений",
                "потеря доверия",
                "закрытие доступа",
                "появление новых подозреваемых",
            ],
        },
    },
}

# Шаблоны финальных сцен
FINAL_SCENES = {
    "success": {
        "title": "Триумфальное раскрытие",
        "description": """
        После тщательного расследования все улики указывают на {culprit}.
        Мотив: {motive}
        Метод: {method}
        
        {resolution}
        
        Дело закрыто успешно!
        """,
        "rewards": {
            "experience": 100,
            "reputation": 50,
            "money": 1000,
            "items": ["медаль", "благодарность", EVIDENCE_DOCUMENTS],
        },
    },
    "partial_success": {
        "title": "Частичная победа",
        "description": """
        Хотя преступник не был пойман, вы собрали важные улики
        и установили ключевые факты дела.
        
        {partial_results}
        
        Дело остается открытым, но вы сделали важный вклад.
        """,
        "rewards": {
            "experience": 50,
            "reputation": 25,
            "money": 500,
            "items": ["благодарность", EVIDENCE_DOCUMENTS],
        },
    },
    "failure": {
        "title": "Неудача",
        "description": """
        К сожалению, время истекло, и дело осталось нераскрытым.
        
        {failure_reasons}
        
        Но каждый опыт - это урок для будущих расследований.
        """,
        "rewards": {
            "experience": 25,
            "reputation": -10,
            "money": 100,
            "items": [EVIDENCE_DOCUMENTS],
        },
    },
}

# Список всех шаблонов
TEMPLATES = {
    Difficulty.EASY: [
        CASE_TEMPLATES["murder_basic"],  # Пока только один шаблон
        # Здесь будут добавлены другие шаблоны
    ],
    Difficulty.MEDIUM: [
        CASE_TEMPLATES["murder_basic"],
        # Здесь будут добавлены другие шаблоны
    ],
    Difficulty.HARD: [
        CASE_TEMPLATES["murder_basic"],
        # Здесь будут добавлены другие шаблоны
    ],
    Difficulty.EXPERT: [
        CASE_TEMPLATES["murder_basic"],
        # Здесь будут добавлены другие шаблоны
    ],
}


def get_template_by_difficulty(difficulty: int) -> Optional[CaseTemplate]:
    """
    Возвращает подходящий шаблон расследования по уровню сложности.

    Args:
        difficulty: Уровень сложности (1-4)

    Returns:
        Optional[CaseTemplate]: Шаблон расследования или None
    """
    try:
        diff_level = Difficulty(difficulty)
        available_templates = TEMPLATES.get(diff_level, [])
        if not available_templates:
            return None
        return random.choice(available_templates)
    except ValueError:
        return None


def customize_template(template: CaseTemplate, user_data: Dict) -> CaseTemplate:
    """
    Адаптирует шаблон расследования под игрока.

    Args:
        template: Исходный шаблон расследования
        user_data: Данные игрока (уровень, навыки и т.д.)

    Returns:
        CaseTemplate: Адаптированный шаблон
    """
    # Создаем копию шаблона
    customized = CaseTemplate(
        id=template.id,
        title=template.title,
        description=template.description,
        difficulty=template.difficulty,
        locations=template.locations.copy(),
        suspects=template.suspects.copy(),
        key_evidence=template.key_evidence.copy(),
        red_herrings=template.red_herrings.copy(),
        correct_sequence=template.correct_sequence.copy(),
        hints=template.hints.copy(),
    )

    # Адаптируем сложность под уровень игрока
    detective_skill = user_data.get("detective_skill", 1)
    if detective_skill < 3:
        # Упрощаем для начинающих
        customized.key_evidence = customized.key_evidence[:3]
        customized.red_herrings = customized.red_herrings[:2]
        customized.correct_sequence = customized.correct_sequence[:5]
    elif detective_skill > 7:
        # Усложняем для опытных
        customized.key_evidence.extend(customized.red_herrings[:2])
        customized.red_herrings.extend(customized.key_evidence[:2])
        random.shuffle(customized.key_evidence)
        random.shuffle(customized.red_herrings)

    # Добавляем подсказки в зависимости от навыков
    forensic_skill = user_data.get("forensic_skill", 1)
    if forensic_skill > 5:
        # Добавляем подсказки по анализу улик
        customized.hints[1].extend(
            [
                "Обратите внимание на химический состав пятен",
                "Изучите микроскопические следы",
                "Проверьте отпечатки пальцев",
            ]
        )

    psychology_skill = user_data.get("psychology_skill", 1)
    if psychology_skill > 5:
        # Добавляем подсказки по психологическому анализу
        customized.hints[1].extend(
            [
                "Проанализируйте поведение подозреваемых",
                "Обратите внимание на невербальные сигналы",
                "Изучите эмоциональные реакции",
            ]
        )

    return customized
