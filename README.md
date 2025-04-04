# Detective Bot

Телеграм-бот для детективной игры с элементами RPG.

## Требования

- Python 3.9+
- PostgreSQL 13+
- Telegram Bot Token
- Claude API Key

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/detective_bot.git
cd detective_bot
```

2. Создайте виртуальное окружение и активируйте его:
```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
venv\Scripts\activate     # для Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `.env` на основе `.env.example` и заполните необходимые переменные:
```bash
cp .env.example .env
```

5. Создайте базу данных PostgreSQL:
```bash
createdb detective_bot
```

6. Примените миграции:
```bash
alembic upgrade head
```

## Запуск

1. Активируйте виртуальное окружение (если еще не активировано):
```bash
source venv/bin/activate  # для Linux/Mac
venv\Scripts\activate     # для Windows
```

2. Запустите бота:
```bash
python main.py
```

## Разработка

### Структура проекта

```
detective_bot/
├── alembic/              # Миграции базы данных
├── bot/                  # Код бота
│   ├── core/            # Основные компоненты
│   ├── handlers/        # Обработчики команд
│   └── keyboards/       # Клавиатуры
├── database/            # Работа с базой данных
├── game/                # Игровая логика
├── logs/                # Логи
├── tests/               # Тесты
├── .env                 # Переменные окружения
├── .env.example         # Пример переменных окружения
├── alembic.ini         # Конфигурация Alembic
├── main.py             # Точка входа
└── requirements.txt    # Зависимости
```

### Тестирование

```bash
pytest
```

### Линтинг

```bash
black .
isort .
flake8
mypy .
```

## Лицензия

MIT 