import asyncio
import logging
import sys

from bot.core.bot import DetectiveBot
from bot.core.config import BotConfig as Config
from bot.database.db import init_db

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def main():
    try:
        # Инициализация базы данных
        await init_db()

        # Инициализация бота
        config = Config()
        bot = DetectiveBot(config=config)
        await bot.start()

        # Держим бота работающим
        logger.info("Бот запущен. Нажмите Ctrl+C для остановки.")

        # Ожидаем сигнала остановки
        try:
            stop_signal = asyncio.Event()
            await stop_signal.wait()
        except asyncio.CancelledError:
            logger.info("Получен сигнал остановки")

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return 1
    finally:
        # Корректное завершение работы бота
        if "bot" in locals():
            logger.info("Остановка бота...")
            try:
                await bot.stop()
            except Exception as e:
                logger.error(f"Ошибка при остановке бота: {e}")

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
