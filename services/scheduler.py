import logging
from datetime import datetime, timezone

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

import database as db
from config import REMINDER_CHECK_INTERVAL_HOURS, REMINDER_INTERVAL_DAYS
from locales.texts import TEXTS

logger = logging.getLogger(__name__)


async def _check_and_notify(bot: Bot) -> None:
    debts = db.get_all_debts()
    now = datetime.now(timezone.utc)

    for debt_id, debt in debts.items():
        if debt.get("status") != "active":
            continue

        debtor_id = debt.get("debtor_id")
        creditor_id = debt.get("creditor_id")
        if not debtor_id or not creditor_id:
            continue

        last_notified = debt.get("last_notified_at")
        last_dt = None
        if isinstance(last_notified, (int, float)):
            if last_notified == 0:
                created_at = debt.get("created_at")
                if isinstance(created_at, (int, float)):
                    last_dt = datetime.fromtimestamp(created_at, tz=timezone.utc)
                elif isinstance(created_at, str):
                    try:
                        last_dt = datetime.fromisoformat(created_at)
                    except ValueError:
                        last_dt = now
                else:
                    last_dt = now
            else:
                last_dt = datetime.fromtimestamp(last_notified, tz=timezone.utc)
        elif isinstance(last_notified, str):
            try:
                last_dt = datetime.fromisoformat(last_notified)
            except ValueError:
                logger.warning("Noto'g'ri sana formati (debt_id=%s): %s", debt_id, last_notified)
                continue

        if not last_dt:
            continue

        days_passed = (now - last_dt).days
        if days_passed < REMINDER_INTERVAL_DAYS:
            continue

        creditor = db.get_user(creditor_id)
        if not creditor:
            continue

        lang = db.get_user_language(debtor_id)
        text = TEXTS[lang]["debt_reminder"].format(
            name=creditor["full_name"], amount=db.format_amount(debt["amount"]), currency=debt["currency"]
        )

        try:
            await bot.send_message(int(debtor_id), text)
            db.update_debt_notified(debt_id)
        except Exception as exc:
            logger.warning("Eslatma yuborilmadi (debt_id=%s): %s", debt_id, exc)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        _check_and_notify,
        trigger=IntervalTrigger(hours=REMINDER_CHECK_INTERVAL_HOURS),
        args=(bot,),
        id="debt_reminder_job",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),
    )
    return scheduler
