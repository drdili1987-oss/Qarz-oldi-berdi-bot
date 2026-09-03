import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import admin, debts, finance, start
from services.scheduler import setup_scheduler
from services.userbot import userbot_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # Handler'lar ro'yxati tartibi muhim: start FSM state'lari eng birinchi
    # tekshiriladi, keyin debts/finance/admin.
    dp.include_router(start.router)
    dp.include_router(debts.router)
    dp.include_router(finance.router)
    dp.include_router(admin.router)

    scheduler = setup_scheduler(bot)
    scheduler.start()

    await userbot_service.start()

    try:
        logger.info("Bot ishga tushmoqda (long polling)...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await userbot_service.stop()
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
