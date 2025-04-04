"""Конфигурация бота."""

import os
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Загрузка переменных окружения
load_dotenv()


class BotConfig:
    """Конфигурация бота"""

    def __init__(self):
        self.TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
        if not self.TELEGRAM_TOKEN:
            raise ValueError("TELEGRAM_TOKEN не найден в переменных окружения")

        self.CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
        if not self.CLAUDE_API_KEY:
            raise ValueError("CLAUDE_API_KEY не найден в переменных окружения")

        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///detective_bot.db")

        # Дополнительные настройки
        self.investigation_timeout = 72
        self.debug = True


def load_config() -> BotConfig:
    """Загрузка конфигурации бота."""
    return BotConfig()


# Настройки окружения
ENV = os.getenv("ENV", "development")

# API токены
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# Настройки базы данных
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:Tspunxak1290!@localhost:5432/detective_bot7",
)
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))

# Настройки логирования
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = "detective_bot.log"

# Настройки Claude API
CLAUDE_MODEL = "claude-3-sonnet-20240229"
CLAUDE_MAX_TOKENS = 4096
CLAUDE_TEMPERATURE = 0.7
CLAUDE_CACHE_TTL = 3600  # 1 час в секундах

# Debug
DEBUG = True


class Settings(BaseSettings):
    """Настройки бота."""

    # Режим работы
    ENV: str = ENV

    # API токены
    TELEGRAM_TOKEN: str = TELEGRAM_TOKEN
    CLAUDE_API_KEY: str = CLAUDE_API_KEY

    # Настройки базы данных
    DATABASE_URL: str = DATABASE_URL
    DB_POOL_SIZE: int = DB_POOL_SIZE
    DB_MAX_OVERFLOW: int = DB_MAX_OVERFLOW
    DB_POOL_TIMEOUT: int = DB_POOL_TIMEOUT
    DB_POOL_RECYCLE: int = DB_POOL_RECYCLE

    # Игровые константы
    MAX_ENERGY: int = 100
    ENERGY_RESTORE_RATE: int = 10
    MAX_CASES_ACTIVE: int = 3
    INVESTIGATION_TIMEOUT: int = 72

    # Настройки логирования
    LOG_LEVEL: str = LOG_LEVEL
    LOG_FORMAT: str = LOG_FORMAT
    LOG_FILE: str = LOG_FILE

    # Настройки Claude API
    CLAUDE_MODEL: str = CLAUDE_MODEL
    CLAUDE_MAX_TOKENS: int = CLAUDE_MAX_TOKENS
    CLAUDE_TEMPERATURE: float = CLAUDE_TEMPERATURE
    CLAUDE_CACHE_TTL: int = CLAUDE_CACHE_TTL

    # Debug
    DEBUG: bool = DEBUG

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


class Config:
    """Конфигурация бота."""

    def __init__(self, settings: Settings):
        self.ENV = settings.ENV
        self.TELEGRAM_TOKEN = settings.TELEGRAM_TOKEN
        self.CLAUDE_API_KEY = settings.CLAUDE_API_KEY
        self.DATABASE_URL = settings.DATABASE_URL
        self.DB_POOL_SIZE = settings.DB_POOL_SIZE
        self.DB_MAX_OVERFLOW = settings.DB_MAX_OVERFLOW
        self.DB_POOL_TIMEOUT = settings.DB_POOL_TIMEOUT
        self.DB_POOL_RECYCLE = settings.DB_POOL_RECYCLE
        self.MAX_ENERGY = settings.MAX_ENERGY
        self.ENERGY_RESTORE_RATE = settings.ENERGY_RESTORE_RATE
        self.MAX_CASES_ACTIVE = settings.MAX_CASES_ACTIVE
        self.INVESTIGATION_TIMEOUT = settings.INVESTIGATION_TIMEOUT
        self.LOG_LEVEL = settings.LOG_LEVEL
        self.LOG_FORMAT = settings.LOG_FORMAT
        self.LOG_FILE = settings.LOG_FILE
        self.CLAUDE_MODEL = settings.CLAUDE_MODEL
        self.CLAUDE_MAX_TOKENS = settings.CLAUDE_MAX_TOKENS
        self.CLAUDE_TEMPERATURE = settings.CLAUDE_TEMPERATURE
        self.CLAUDE_CACHE_TTL = settings.CLAUDE_CACHE_TTL
        self.DEBUG = settings.DEBUG


def load_config() -> Config:
    """
    Загружает конфигурацию из переменных окружения.

    Returns:
        Config: Объект конфигурации
    """
    settings = Settings()
    return Config(settings)


config = load_config()
